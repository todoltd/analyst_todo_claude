# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

# Базові типи результату Odoo (fields_get types) + 'formula'. Динамічний selection
# звужується до доступних користувачу полів у валідації/дереві (AC-02); тут — повний словник.
_ODOO_FIELD_TYPES = [
    ('char', 'Текст'),
    ('text', 'Текст (довгий)'),
    ('html', 'HTML'),
    ('integer', 'Ціле'),
    ('float', 'Число'),
    ('monetary', 'Грошове'),
    ('boolean', 'Логічне'),
    ('date', 'Дата'),
    ('datetime', 'Дата/час'),
    ('selection', 'Список'),
    ('many2one', 'Зв\'язок (m2o)'),
    ('one2many', 'Зв\'язок (o2m)'),
    ('many2many', 'Зв\'язок (m2m)'),
    ('binary', 'Файл'),
    ('reference', 'Посилання'),
    ('json', 'JSON'),
]


class BiDatasetField(models.Model):
    _name = 'td.bi.dataset.field'
    _description = 'BI Поле датасету'
    _order = 'sequence, id'

    # === Fields ===
    dataset_id = fields.Many2one(
        'td.bi.dataset', string="Датасет", required=True, ondelete='cascade',
    )
    name = fields.Char(string="Псевдонім", required=True)
    path = fields.Char(string="Шлях поля")
    field_type = fields.Selection(
        selection='_selection_field_type', string="Тип результату",
    )
    role = fields.Selection(
        [
            ('dimension', 'Вимір'),
            ('measure', 'Міра'),
            ('attribute', 'Атрибут'),
        ],
        string="Роль",
    )
    aggregator = fields.Selection(
        [
            ('sum', 'Сума'),
            ('avg', 'Середнє'),
            ('min', 'Мінімум'),
            ('max', 'Максимум'),
            ('count', 'Кількість'),
            ('count_distinct', 'Кількість унікальних'),
            ('bool_and', 'Логічне І'),
            ('bool_or', 'Логічне АБО'),
        ],
        string="Агрегатор",
    )
    is_formula = fields.Boolean(string="DSL-поле")
    formula = fields.Text(string="Формула")
    formula_compiled = fields.Text(
        string="Скомпільована формула",
        compute='_compute_formula_compiled',
        store=True,  # кеш компіляції SQL-виразу DSL (AC-09/AC-10), обчислюється при збереженні
        readonly=True,
    )
    currency_path = fields.Char(string="Шлях валюти")
    geo_role = fields.Selection(
        [
            ('none', 'Немає'),
            ('country', 'Країна'),
            ('state', 'Регіон'),
            ('latlong', 'Координати'),
        ],
        string="Гео-роль",
    )
    format_spec = fields.Json(string="Формат")
    description = fields.Text(string="Опис")
    visible = fields.Boolean(string="Видиме", default=True)
    sequence = fields.Integer(string="Послідовність")

    # === Selection helpers ===
    def _selection_field_type(self):
        """Перелік типів результату поля — типи Odoo (fields_get) + значення `formula`.
        AC-02 — конкретний тип кожного поля проставляється з fields_get() ПОТОЧНОГО
        користувача (поля з groups= недоступні і в дереві не з'являються); тут — повний
        словник можливих значень selection (Odoo вимагає статичний/детермінований перелік).
        """
        return list(_ODOO_FIELD_TYPES) + [('formula', 'Формула')]

    # === Computed ===
    @api.depends('formula', 'is_formula')
    def _compute_formula_compiled(self):
        """Компіляція DSL-формули у SQL-вираз; результат у formula_compiled (store, readonly).
        Сама компіляція/валідація AST делегується td.bi.query.compiler._compile_formula
        (whitelist вузлів AST, колонки через SQL.identifier, значення — bind-параметри).
        AC-09 — змішування агрегованого/неагрегованого операндів виявляє компілятор;
        AC-10 — невідоме поле виявляє компілятор (з підказкою).
        Помилки тут НЕ підіймаємо (інакше блокується обчислення поля) — серверну
        валідацію з ValidationError робить @api.constrains _check_formula при збереженні.
        """
        compiler = self.env['td.bi.query.compiler']
        for record in self:
            if not (record.is_formula and record.formula):
                record.formula_compiled = False
                continue
            try:
                compiled = compiler._compile_formula(record)
                record.formula_compiled = compiled or False
            except (ValidationError, UserError):
                # Невалідну формулу не кешуємо; деталі покаже constrains при збереженні.
                record.formula_compiled = False
            except NotImplementedError:
                # Stage-1: компілятор ще не реалізовано — лишаємо порожнім (не падаємо).
                record.formula_compiled = False

    # === SQL constraints ===
    # Odoo 19: models.Constraint замість _sql_constraints (deprecated)
    _name_uniq_per_dataset = models.Constraint(
        'unique(dataset_id, name)',
        "Псевдонім поля має бути унікальним у межах датасету.",
    )
    # Блокування видалення поля, що використовується віджетами, реалізується
    # методом validate_integrity() на td.bi.dataset (не SQL-constraint).

    # === Constraints (DSL) ===
    @api.constrains('formula', 'is_formula', 'role', 'path')
    def _check_formula(self):
        """Серверна валідація DSL/поля при збереженні; компіляція делегується
        td.bi.query.compiler._compile_formula.

        AC-07 — computed-поле без store і без search не можна використати як вимір/фільтр:
                якщо path вказує на таке поле і роль — dimension, відхиляємо.
        AC-09 — змішування агрегованого/неагрегованого операндів -> ValidationError
                (делеговано компілятору, який підіймає ValidationError).
        AC-10 — невідоме поле у формулі -> ValidationError з підказкою найближчого імені
                (делеговано компілятору).
        AC-13 — dunder/__import__ -> відмова whitelist AST (делеговано компілятору).
        """
        compiler = self.env['td.bi.query.compiler']
        for record in self:
            # AC-07: вимір/фільтр на нефільтрованому computed-полі заборонено.
            if record.path and record.role in ('dimension',) and record.dataset_id.model_name:
                record._check_path_selectable()

            if not record.is_formula:
                continue
            if not record.formula or not record.formula.strip():
                raise ValidationError(_(
                    "Поле «%s» позначене як DSL-поле, але формула порожня.", record.name))
            try:
                # Делегуємо повну валідацію (AST-whitelist, агр./неагр. мікс, невідоме поле,
                # dunder/__import__) компілятору — він підіймає ValidationError з позицією/підказкою.
                compiler._compile_formula(record)
            except NotImplementedError:
                # Stage-1: компілятор-валідатор ще не активний — не блокуємо збереження
                # синтаксично непорожньої формули (повна валідація вмикається зі Stage-2).
                pass

    def _check_path_selectable(self):
        """AC-07 — перевірити, що поле за `path` можна фільтрувати/групувати:
        computed без store і без search неактивне -> ValidationError."""
        self.ensure_one()
        model_name = self.dataset_id.model_name
        if not model_name:
            return
        segments = self.path.split('.')
        model = model_name
        # Пройти relational-цепочку до кінцевого поля (su=False — звірка з правами, AC-02).
        for seg in segments[:-1]:
            meta = self.env[model].fields_get([seg])
            if seg not in meta:
                raise ValidationError(_(
                    "Невідоме/недоступне поле «%(seg)s» у шляху «%(path)s».",
                    seg=seg, path=self.path))
            comodel = meta[seg].get('relation')
            if not comodel:
                raise ValidationError(_(
                    "Поле «%(seg)s» не є зв'язком — шлях «%(path)s» некоректний.",
                    seg=seg, path=self.path))
            model = comodel
        leaf = segments[-1]
        if leaf not in self.env[model].fields_get([leaf]):
            raise ValidationError(_(
                "Невідоме/недоступне поле «%(leaf)s» у моделі «%(model)s».",
                leaf=leaf, model=model))
        field = self.env[model]._fields.get(leaf)
        if field is not None and field.compute and not field.store and not field.search:
            raise ValidationError(_(
                "Поле «%(name)s» (%(path)s) — обчислюване без збереження і пошуку; "
                "його не можна використати як вимір чи фільтр.",
                name=self.name, path=self.path))
