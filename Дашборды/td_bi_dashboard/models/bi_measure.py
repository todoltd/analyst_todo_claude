# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class BiMeasure(models.Model):
    _name = 'td.bi.measure'
    _description = 'BI Іменована міра'
    _order = 'id'

    # === Fields ===
    dataset_id = fields.Many2one(
        'td.bi.dataset', string="Датасет", required=True, ondelete='cascade',
    )
    name = fields.Char(string="Назва", required=True)
    expression = fields.Text(string="Вираз (DSL)")
    field_id = fields.Many2one(
        'td.bi.dataset.field', string="Поле",
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
    extra_domain = fields.Text(string="Додатковий домен")
    show_as = fields.Selection(
        [
            ('value', 'Значення'),
            ('percent_of_total', '% від підсумку'),
            ('percent_of_dimension', '% усередині виміру'),
            ('running_total', 'Накопичувальний підсумок'),
            ('rank', 'Ранг'),
            ('diff_prev', 'Різниця з попереднім'),
            ('diff_prev_pct', '% різниці'),
        ],
        string="Спосіб показу",
    )
    time_intelligence = fields.Selection(
        [
            ('none', 'Немає'),
            ('ytd', 'Year-to-date'),
            ('qtd', 'Quarter-to-date'),
            ('mtd', 'Month-to-date'),
            ('yoy', 'Year-over-year'),
            ('pop', 'Period-over-period'),
            ('rolling', 'Ковзне вікно'),
        ],
        string="Часовий інтелект",
    )
    rolling_n = fields.Integer(string="Вікно ковзання")
    comparison = fields.Selection(
        [
            ('none', 'Немає'),
            ('prev_period', 'Попередній період'),
            ('prev_year', 'Попередній рік'),
            ('custom_shift', 'Власний зсув'),
        ],
        string="Порівняння періодів",
    )
    format_spec = fields.Json(string="Формат")
    description = fields.Text(string="Опис")

    # === SQL constraints ===
    # SPEC: SQL-constraints для td.bi.measure не задано.

    # === Constraints ===
    @api.constrains('expression', 'field_id', 'aggregator', 'show_as')
    def _check_expression(self):
        """Серверна валідація виразу міри при збереженні; компіляція/валідація DSL
        делегується td.bi.query.compiler._compile_formula.

        AC-08 — міра-ratio (DSL над агрегатами) компілюється в один агрегувальний запит
                (SUM+COUNT_DISTINCT в одному formatted_read_group) — компілятор перевіряє
                коректність агрегатної структури виразу;
        AC-09 — змішування агрегованого/неагрегованого операндів -> ValidationError;
        AC-11 — ділення на нуль -> NULLIF(denominator,0)->NULL (генерує компілятор; тут лише
                переконуємось, що вираз компілюється);
        AC-55 — show_as=percent_of_total рахується через GROUPING SETS (рушієм);
                тут перевіряємо, що міра має базу обчислення (expression АБО field_id+aggregator).
        Кожна міра має мати АБО expression, АБО (field_id + aggregator).
        """
        compiler = self.env['td.bi.query.compiler']
        for record in self:
            has_expression = bool(record.expression and record.expression.strip())
            has_simple = bool(record.field_id and record.aggregator)
            if not has_expression and not has_simple:
                raise ValidationError(_(
                    "Міра «%s» має задавати АБО DSL-вираз, АБО поле + агрегатор.",
                    record.name))
            if has_expression and has_simple:
                raise ValidationError(_(
                    "Міра «%s»: вкажіть лише одне — DSL-вираз АБО поле + агрегатор.",
                    record.name))
            if has_expression:
                try:
                    # Делегуємо валідацію виразу (агр./неагр. мікс AC-09, невідоме поле AC-10,
                    # dunder/__import__ AC-13, ділення на нуль AC-11) компілятору.
                    compiler._compile_formula(record)
                except NotImplementedError:
                    # Stage-1: компілятор-валідатор ще не активний — не блокуємо.
                    pass

    @api.constrains('time_intelligence', 'comparison', 'dataset_id')
    def _check_time_intelligence(self):
        """Заборона часового інтелекту/порівняння періодів без виміру-дати у датасеті.

        AC-42 — YoY/PoP рендериться як другий ряд із зсувом домену дат: для цього потрібен
                хоча б один вимір типу date/datetime у датасеті;
        AC-44 — без виміру-дати часовий інтелект недоступний: вмикання -> ValidationError
                (UI ховає/деактивує опції з підказкою «потрібен вимір-дата»).
        """
        for record in self:
            ti = record.time_intelligence
            cmp_ = record.comparison
            needs_date = (ti and ti != 'none') or (cmp_ and cmp_ != 'none')
            if needs_date and not record._dataset_has_date_dimension():
                raise ValidationError(_(
                    "Міра «%s»: часовий інтелект і порівняння періодів потребують "
                    "виміру-дати в датасеті. Додайте поле типу дата/дата-час.",
                    record.name))
            # custom_shift без визначеного rolling_n зробив би зсув періоду невизначеним.
            if cmp_ == 'custom_shift' and not (record.rolling_n and record.rolling_n > 0):
                raise ValidationError(_(
                    "Міра «%s»: для порівняння «Власний зсув» задайте «Вікно ковзання» (> 0).",
                    record.name))

    def _dataset_has_date_dimension(self):
        """AC-42/AC-44 — чи має датасет хоча б одне поле-вимір типу date/datetime.
        Перевіряємо за оголошеними полями датасету (звірка типу з fields_get користувача)."""
        self.ensure_one()
        dataset = self.dataset_id
        if not dataset:
            return False
        model_name = dataset.model_name
        for f in dataset.field_ids:
            # 1) явно проставлений тип результату поля.
            if f.field_type in ('date', 'datetime'):
                return True
            # 2) інакше — звірка кінцевого поля шляху з fields_get (AC-02, без su).
            if f.path and model_name:
                ftype = self._leaf_field_type(model_name, f.path)
                if ftype in ('date', 'datetime'):
                    return True
        return False

    def _leaf_field_type(self, model_name, path):
        """Тип кінцевого поля relational-шляху (fields_get su=False); None якщо недоступне."""
        model = model_name
        segments = path.split('.')
        for seg in segments[:-1]:
            meta = self.env[model].fields_get([seg])
            comodel = meta.get(seg, {}).get('relation')
            if not comodel:
                return None
            model = comodel
        leaf = segments[-1]
        return self.env[model].fields_get([leaf]).get(leaf, {}).get('type')
