# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
import ast
import logging

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Domain  # Odoo 19: первокласний Domain (Domain.AND для кон'юнкції рівнів)

_logger = logging.getLogger(__name__)

# Конфігураційні константи (SPEC §Configuration / ТР §2.4.1, §2.1).
MAX_FIELD_DEPTH = 5          # глибина дерева полів ≤ 5 рівнів (AC-04, ВИМ-02)
PREVIEW_ROW_LIMIT = 80       # ліміт рядків таблиці попереднього перегляду (AC-06)
DEFAULT_STATEMENT_TIMEOUT = 30  # statement_timeout, с (SPEC §Configuration, AC-49)


class BiDataset(models.Model):
    _name = 'td.bi.dataset'
    _description = 'BI Датасет'
    _order = 'name, id'

    # === Fields ===
    name = fields.Char(string="Назва", required=True, translate=True)
    description = fields.Text(string="Опис")
    mode = fields.Selection(
        [
            ('model', 'Модель Odoo'),
            ('blend', 'Обʼєднання таблиць'),
            ('sql', 'SQL-датасет'),
        ],
        string="Режим",
        default='model',
    )
    model_id = fields.Many2one(
        'ir.model',
        string="Коренева модель",
        domain="[('transient', '=', False), ('abstract', '=', False)]",
    )
    model_name = fields.Char(
        string="Технічне імʼя моделі",
        related='model_id.model',
        store=True,
    )
    domain = fields.Text(string="Базовий домен", default='[]')
    field_ids = fields.One2many(
        'td.bi.dataset.field', 'dataset_id', string="Поля датасету",
    )
    join_ids = fields.One2many(
        'td.bi.dataset.join', 'dataset_id', string="Таблиці бленда",
    )
    measure_ids = fields.One2many(
        'td.bi.measure', 'dataset_id', string="Іменовані міри",
    )
    parameter_ids = fields.One2many(
        'td.bi.parameter', 'dataset_id', string="Параметри",
    )
    sql_query = fields.Text(string="SQL-запит")
    sql_field_ids = fields.One2many(
        'td.bi.dataset.field', 'dataset_id', string="Оголошені поля SQL",
    )
    currency_strategy = fields.Selection(
        [
            ('sum_currency', 'За поточним курсом'),
            ('historical', 'Історична'),
            ('group_by_currency', 'Групування за валютою'),
        ],
        string="Стратегія мультивалютності",
        default='sum_currency',
    )
    date_field_default = fields.Char(string="Поле дати за замовчуванням")
    fiscalyear_offset = fields.Integer(string="Зсув фінансового року (міс.)")
    cache_ttl = fields.Integer(string="TTL кешу (с)", default=600)
    row_limit = fields.Integer(string="Ліміт рядків", default=100000)
    visibility = fields.Selection(
        [
            ('private', 'Лише власник'),
            ('groups', 'Команди'),
            ('global', 'Усі'),
        ],
        string="Видимість",
        default='private',
    )
    group_ids = fields.Many2many('res.groups', string="Команди")
    owner_id = fields.Many2one(
        'res.users', string="Власник", default=lambda self: self.env.user,
    )
    company_ids = fields.Many2many('res.company', string="Компанії")
    active = fields.Boolean(string="Активний", default=True)

    # === Computed ===
    version = fields.Integer(
        string="Версія", compute='_compute_version', store=True,
    )

    @api.depends('field_ids', 'measure_ids', 'join_ids', 'parameter_ids',
                 'domain', 'sql_query', 'mode', 'model_id')
    def _compute_version(self):
        """Bump версії датасету при зміні полів/конфігурації; елемент ключа кешу (§2.4).
        AC-23 — version входить у _build_cache_key; bump блокує застарілий кеш:
        будь-яка зміна конфігурації (depends-граф) піднімає version на 1, тож старі
        кеш-ключі більше не накриваються і користувачі бачать свіжі дані.
        """
        for record in self:
            # +1 від поточного збереженого значення (None трактуємо як 0 -> 1).
            record.version = (record.version or 0) + 1

    # === SQL constraints ===
    # SPEC: SQL-constraints для td.bi.dataset не задано.
    # Видимість і мультикомпанія — через record rules (ir.rule), не constraints.

    # === Actions / Key methods ===
    def run_query(self, query_spec):
        """Єдина точка виконання запиту: валідація → права → ключ кешу → компіляція →
        виконання → пост-обробка → кеш (§2.4.1). Приймає `query_spec` (dict).

        Конвеєр (AC-06/AC-19/AC-20/AC-23/AC-49/AC-64):
          1. валідація `query_spec` (структура + кожен path звіряється з fields_get()
             поточного користувача — заборонене/невідоме поле -> AccessError) (AC-02/AC-36);
          2. `has_access('read')` на кореневу модель (AC-01/AC-19);
          3. ефективний домен трьох рівнів виключно через Domain.AND (AC-64);
          4. пошук у td.bi.cache за ключем, що включає uid-маркер прав (AC-23);
          5. кеш-промах -> делегування в td.bi.query.compiler.route_query
             (роутер матеріалізації; інакше formatted_read_group) ВІД ІМЕНІ користувача,
             БЕЗ sudo() (AC-08/AC-53/AC-54/AC-62);
          6. збереження результату в кеш і повернення.

        Попередній перегляд (AC-06): один RPC = один run_query; таблиця -> limit≤80.
        Stage-1 фокус: mode='model'. mode in (blend, sql) — Stage-2/3 заглушка.
        """
        self.ensure_one()
        query_spec = dict(query_spec or {})

        # --- mode='sql': Stage-3 заглушка (структурно коректна) ---
        if self.mode == 'sql':
            # TODO(Stage-3): SQL-датасет (mode=sql, AC-50/51) — контрольована відмова без падіння.
            raise UserError(_(
                "Режим датасету «SQL» буде доступний на наступному етапі."))

        is_blend = (self.mode == 'blend')
        if not is_blend:
            # --- (1) валідація query_spec проти прав користувача (AC-02/AC-36) ---
            # Лише mode='model': шляхи звіряються з полями кореневої моделі. У бленді
            # «поля» — це псевдоніми датасету над джерелами, тож ця перевірка не застосовна.
            self._validate_query_spec(query_spec)
            # --- (2) has_access('read') на кореневу модель (AC-01/AC-19/AC-20) ---
            if not self.model_name:
                raise UserError(_("Для датасету в режимі «Модель Odoo» не задано кореневу модель."))
            root_model = self.env[self.model_name]
            # has_access підіймає/повертає згідно з ACL поточного користувача (без sudo()).
            if not root_model.has_access('read'):
                raise AccessError(_(
                    "Немає доступу на читання моделі «%s».", self.model_name))
        # mode='blend': кореневої моделі немає — доступ забезпечує RLS У КОЖНОМУ CTE-джерелі
        # (_inject_record_rules, AC-39), без sudo. Порожній результат (нуль доступних рядків)
        # деградує як порожній віджет (AC-20), не AccessError.

        # --- (3) ефективний домен трьох рівнів виключно через Domain.AND (AC-64) ---
        base_domain = self._build_base_domain(query_spec)

        # --- (4) ключ кешу + спроба прочитати з кешу (AC-23) ---
        cache = self.env['td.bi.cache']
        use_cache = bool(self.cache_ttl and self.cache_ttl > 0)
        cache_key = False
        if use_cache:
            cache_key = cache._build_cache_key(self, query_spec)
            # _get/_set — допоміжні методи кешу (sibling-трек); guard на час Stage-1.
            if cache_key and hasattr(cache, '_get'):
                cached = cache._get(cache_key)
                if cached is not None:
                    return cached

        # --- (5) делегування в компілятор/роутер ВІД ІМЕНІ користувача (AC-08/62) ---
        # Адаптер route_query інкапсулює 4 API, що звіряються з живою збіркою Odoo 19.0:
        # DEVIATION(Odoo19): підтвердити точну назву публічного методу GROUPING SETS
        #   `formatted_read_grouping_sets` (батч агрегатів кількох віджетів одним викликом,
        #   AC-08/AC-36/AC-55); запасний шлях — кілька викликів `formatted_read_group`.
        # DEVIATION(Odoo19): підтвердити нативний агрегат `sum_currency` у formatted_read_group
        #   (SUM(amount/rate) з JOIN курсу, AC-53/AC-54); запасний шлях — конвертація _convert
        #   на дату документа (патерн sale.report) у пост-обробці.
        # DEVIATION(Odoo19): підтвердити `Model._search(domain) -> Query` як точку запиту з
        #   вбудованими record rules для підзапиту бленда/RLS (AC-39/AC-62); запасний шлях —
        #   `search(domain).ids` (інкапсульовано в compiler._inject_record_rules).
        # DEVIATION(Odoo19): підтвердити життєвий цикл `_auto=False` + `init()` і
        #   `REFRESH MATERIALIZED VIEW CONCURRENTLY` для td.bi.materialization (AC-62/AC-63);
        #   запасний шлях у route_query — fallback на formatted_read_group по сирій моделі.
        compiler = self.env['td.bi.query.compiler']
        result = compiler.route_query(self, query_spec, base_domain)

        # --- (6) пост-обробка (ліміт прев'ю) + запис у кеш (AC-06/AC-23) ---
        result = self._postprocess_result(result, query_spec)
        if use_cache and cache_key and hasattr(cache, '_set'):
            cache._set(cache_key, self, result)
        return result

    def get_fields_tree(self, path=None):
        """Ліниве дерево полів за `path` — лише доступні fields_get(su=False) поля.

        AC-02 — повертаємо лише поля, видимі fields_get() поточного користувача;
                поля з `groups=`, недоступні користувачу, fields_get не повертає -> їх
                у дереві немає і обрати їх не можна.
        AC-04 — глибина шляху ≤ 5 рівнів; на 5-му рівні relational-гілки не розкриваємо
                (повертаємо ознаку `expandable=False` + `depth_limited=True`).
        AC-05 — повтор пари (модель, поле) у шляху -> маркер рекурсії `recursive=True`
                (UI вимагає явного підтвердження перед додаванням).
        AC-07 — computed-поле без store і без search -> `selectable=False`
                (неактивне: не можна фільтрувати/групувати).
        """
        self.ensure_one()
        if self.mode != 'model' or not self.model_name:
            return []

        segments = [s for s in (path or '').split('.') if s]

        # AC-04: понад 5 рівнів не розкриваємо.
        if len(segments) >= MAX_FIELD_DEPTH:
            return {
                'path': path or '',
                'depth_limited': True,
                'message': _("Досягнуто ліміту глибини зв'язків (%s).", MAX_FIELD_DEPTH),
                'fields': [],
            }

        # Пройти шлях до цільової моделі (кожен крок — relational-поле, доступне користувачу).
        target_model, chain = self._resolve_path_model(self.model_name, segments)
        if target_model is None:
            # Недоступний/невідомий проміжний крок -> порожня гілка (без падіння).
            return {'path': path or '', 'fields': []}

        # fields_get(su=False): поля з groups= вже відфільтровано Odoo для цього користувача (AC-02).
        fields_meta = self.env[target_model].fields_get()
        nodes = []
        for fname, meta in fields_meta.items():
            node = self._build_field_node(target_model, fname, meta, chain, segments)
            if node is not None:
                nodes.append(node)
        nodes.sort(key=lambda n: (n['type'] != 'relational', n['label'] or n['name']))
        return {
            'path': path or '',
            'model': target_model,
            'depth': len(segments),
            'fields': nodes,
        }

    def validate_integrity(self):
        """Перевірка цілісності датасету (ВИМ-10).

        AC-01  — лише власник/дизайнер може змінювати датасет (ORM ACL + record rules
                 застосовуються нативно; тут додатково has_access('write')).
        AC-03  — багаторівневий JOIN фіксується автоматично зі шляху поля: пройти кожен
                 path і пересвідчитись, що цепочка зв'язку коректна (повний шлях existує).
        AC-10  — невідоме/некоректне поле відхиляється з підказкою.
        ВИМ-10 — блок видалення поля, що використовують віджети: якщо поле більше не
                 присутнє в датасеті, а на нього посилаються віджети -> UserError з переліком.
        Бамп version після успішної перевірки (елемент ключа кешу, AC-23).
        """
        self.ensure_one()
        # AC-01: зміни лише з правом write (ACL + record rule власника/дизайнера).
        if not self.has_access('write'):
            raise AccessError(_("Немає права змінювати датасет «%s».", self.name or self.id))

        # AC-03/AC-10: кожен path-вимір має валідну цепочку зв'язку до кінцевого поля.
        if self.mode == 'model' and self.model_name:
            for f in self.field_ids:
                if not f.path:
                    continue
                segments = f.path.split('.')
                # Останній сегмент — кінцеве поле; попередні — relational-кроки.
                model, _chain = self._resolve_path_model(self.model_name, segments[:-1])
                if model is None:
                    raise ValidationError(_(
                        "Поле «%(name)s»: цепочку зв'язку шляху «%(path)s» не вдалося "
                        "розгорнути (невідоме/недоступне проміжне поле).",
                        name=f.name, path=f.path))
                leaf = segments[-1]
                meta = self.env[model].fields_get([leaf])
                if leaf not in meta:
                    suggestion = self._suggest_field_name(model, leaf)
                    raise ValidationError(_(
                        "Поле «%(name)s»: невідоме поле «%(leaf)s» у моделі «%(model)s».%(hint)s",
                        name=f.name, leaf=leaf, model=model,
                        hint=(_(" Можливо, ви мали на увазі «%s»?", suggestion) if suggestion else "")))

        # ВИМ-10: блок видалення поля, що використовують віджети.
        used = self._fields_used_by_widgets()
        declared = {f.name for f in self.field_ids} | {m.name for m in self.measure_ids}
        missing = sorted(used - declared)
        if missing:
            raise UserError(_(
                "Неможливо зберегти зміни: поля/міри %(fields)s використовуються "
                "віджетами і не можуть бути видалені.",
                fields=", ".join(missing)))

        # Бамп version (свіжий ключ кешу).
        self.version = (self.version or 0) + 1
        return True

    # === Private helpers ===
    def _build_base_domain(self, query_spec):
        """AC-64 — ефективний домен трьох рівнів ВИКЛЮЧНО через Domain.AND
        (датасет ∧ контроли/аудиторія ∧ домен віджета); без конкатенації списків.
        Текстові домени парсяться через ast.literal_eval (НЕ eval/safe_eval).
        Делегуємо склейку компілятору (_build_effective_domain) із запасним локальним шляхом.
        """
        levels = []
        # Рівень 1: базовий домен датасету.
        levels.append(self._parse_domain_text(self.domain))
        # Рівень 2: домен(и) з query_spec (контроли/аудиторія/cross-filter), вже зібрані клієнтом.
        spec_domain = query_spec.get('domain')
        if spec_domain:
            levels.append(self._coerce_domain(spec_domain))
        # Рівень 3: власний домен віджета.
        widget_domain = query_spec.get('widget_domain')
        if widget_domain:
            levels.append(self._coerce_domain(widget_domain))
        # Рівні контролів/cross-filter/drill (AC-25/AC-15/AC-14) — теж звужують по І.
        for key in ('control_domain', 'cross_filter_domain', 'drill_domain', 'audience_domain'):
            dom = query_spec.get(key)
            if dom:
                levels.append(self._coerce_domain(dom))

        compiler = self.env['td.bi.query.compiler']
        try:
            # Основний шлях: централізована безпечна склейка в адаптері (Domain.AND).
            return compiler._build_effective_domain(levels)
        except NotImplementedError:
            # Запасний локальний шлях (Stage-1): Domain.AND безпосередньо, без конкатенації.
            return Domain.AND([Domain(d) for d in levels if d not in (None, [])])

    def _validate_query_spec(self, query_spec):
        """AC-02/AC-36 — структурна валідація query_spec; кожен path звіряється з
        fields_get() ПОТОЧНОГО користувача. Заборонене (groups=) або невідоме поле -> AccessError.
        """
        if not isinstance(query_spec, dict):
            raise ValidationError(_("query_spec має бути словником."))

        groupby = query_spec.get('groupby') or []
        aggregates = query_spec.get('aggregates') or []
        if not isinstance(groupby, (list, tuple)) or not isinstance(aggregates, (list, tuple)):
            raise ValidationError(_("groupby/aggregates у query_spec мають бути списками."))

        # Зібрати всі path-и, що звертаються до полів моделі.
        paths = set()
        for gb in groupby:
            paths.add(self._path_of_spec_item(gb))
        for ag in aggregates:
            # aggregate-спека виду 'field:agg' або {'field': ..., 'aggregator': ...}
            paths.add(self._path_of_spec_item(ag))
        paths.discard(None)
        paths.discard('')
        paths.discard('__count')  # службовий агрегат не звіряємо

        for path in paths:
            self._assert_path_accessible(path)

    def _assert_path_accessible(self, path):
        """Звірка одного path із fields_get(su=False) користувача вздовж усієї цепочки.
        Невідоме поле -> ValidationError; недоступне (groups=) -> AccessError (AC-02).
        """
        segments = [s for s in path.split('.') if s]
        if not segments:
            return
        # Зрізаємо групувальний суфікс гранулярності (наприклад date_order:month).
        segments[-1] = segments[-1].split(':', 1)[0]
        model = self.model_name
        for idx, seg in enumerate(segments):
            meta = self.env[model].fields_get([seg])
            if seg not in meta:
                # Поле взагалі не існує -> невідоме поле (AC-10/AC-36-валідатор).
                # Відрізняємо від «закрите groups=»: перевіряємо повний fields_get.
                full = self.env[model].fields_get()
                if seg in self.env[model]._fields and seg not in full:
                    # Поле існує в моделі, але приховане для користувача (groups=) -> доступ заборонено.
                    raise AccessError(_(
                        "Поле «%(seg)s» моделі «%(model)s» недоступне за вашими правами.",
                        seg=seg, model=model))
                raise ValidationError(_(
                    "Невідоме поле «%(seg)s» у шляху «%(path)s» (модель «%(model)s»).",
                    seg=seg, path=path, model=model))
            # Перехід углиб relational-полем.
            if idx < len(segments) - 1:
                comodel = meta[seg].get('relation')
                if not comodel:
                    raise ValidationError(_(
                        "Поле «%(seg)s» не є зв'язком — шлях «%(path)s» некоректний.",
                        seg=seg, path=path))
                model = comodel

    def _resolve_path_model(self, model_name, segments):
        """Пройти relational-цепочку `segments` від `model_name`; повертає (цільова_модель, chain)
        або (None, []) якщо крок недоступний/не relational. chain — список (model, field) пар
        для виявлення рекурсії (AC-05)."""
        model = model_name
        chain = []
        for seg in segments:
            meta = self.env[model].fields_get([seg])
            if seg not in meta:
                return None, []
            comodel = meta[seg].get('relation')
            if not comodel:
                return None, []
            chain.append((model, seg))
            model = comodel
        return model, chain

    def _build_field_node(self, model, fname, meta, chain, segments):
        """Сформувати вузол дерева для поля; реалізує AC-05 (рекурсія) і AC-07 (неактивне computed)."""
        ttype = meta.get('type')
        relational = bool(meta.get('relation'))
        node_path = '.'.join(segments + [fname]) if segments else fname

        # AC-07: computed без store і без search -> не можна фільтрувати/групувати.
        field = self.env[model]._fields.get(fname)
        selectable = True
        reason = False
        if field is not None and field.compute and not field.store and not field.search:
            selectable = False
            reason = _("Обчислюване поле без збереження — не можна фільтрувати/групувати.")

        # AC-05: повтор пари (модель, поле) у вже пройденому ланцюзі -> маркер рекурсії.
        recursive = (model, fname) in chain

        return {
            'name': fname,
            'path': node_path,
            'label': meta.get('string') or fname,
            'type': 'relational' if relational else (ttype or 'char'),
            'ttype': ttype,
            'relation': meta.get('relation') or False,
            'expandable': relational and len(segments) + 1 < MAX_FIELD_DEPTH,  # AC-04
            'recursive': recursive,                                            # AC-05
            'selectable': selectable,                                          # AC-07
            'inactive_reason': reason,                                         # AC-07
            'aggregator': meta.get('aggregator') or False,
            'store': bool(meta.get('store', True)),
        }

    def _fields_used_by_widgets(self):
        """Множина імен полів/мір датасету, на які посилаються віджети (ВИМ-10).
        Stage-1: читаємо віджети, що вказують на цей датасет, і збираємо назви з їх конфігу."""
        used = set()
        Widget = self.env['td.bi.widget']
        if 'dataset_id' not in Widget._fields:
            return used
        widgets = Widget.search([('dataset_id', '=', self.id)])
        for w in widgets:
            config = getattr(w, 'config', None) or getattr(w, 'spec', None)
            if isinstance(config, dict):
                for key in ('groupby', 'measures', 'dimensions', 'aggregates'):
                    for item in (config.get(key) or []):
                        name = self._path_of_spec_item(item)
                        if name:
                            used.add(name.split(':', 1)[0])
        return used

    @staticmethod
    def _path_of_spec_item(item):
        """Витягти ім'я поля/path зі спеки groupby/aggregate (рядок 'field:gran' або dict)."""
        if isinstance(item, str):
            return item.split(':', 1)[0]
        if isinstance(item, dict):
            return item.get('field') or item.get('path') or item.get('name')
        if isinstance(item, (list, tuple)) and item:
            return BiDataset._path_of_spec_item(item[0])
        return None

    def _suggest_field_name(self, model_name, name):
        """Найближче ім'я поля для підказки (AC-10) — за простою префікс/підрядок-евристикою."""
        try:
            candidates = list(self.env[model_name].fields_get().keys())
        except Exception:  # pragma: no cover — модель може бути недоступна
            return False
        lowered = name.lower()
        for cand in candidates:
            cl = cand.lower()
            if cl.startswith(lowered) or lowered.startswith(cl) or lowered in cl:
                return cand
        return False

    def _parse_domain_text(self, text):
        """Парс текстового домену через ast.literal_eval (НЕ eval/safe_eval) — §2.4.3."""
        if not text:
            return []
        try:
            parsed = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            raise ValidationError(_("Некоректний синтаксис домену: %s", text))
        return self._coerce_domain(parsed)

    @staticmethod
    def _coerce_domain(value):
        """Привести значення домену до списку (без конкатенації; склейку робить Domain.AND)."""
        if value in (None, False, ''):
            return []
        if isinstance(value, (list, tuple)):
            return list(value)
        raise ValidationError(_("Домен має бути списком."))

    def _postprocess_result(self, result, query_spec):
        """Пост-обробка результату run_query (AC-06): для попереднього перегляду таблиці
        обрізаємо до PREVIEW_ROW_LIMIT (≤80) рядків. Stage-1 — мінімальна нормалізація."""
        if not isinstance(result, dict):
            return result
        if query_spec.get('preview') and isinstance(result.get('rows'), list):
            limit = min(int(query_spec.get('limit') or PREVIEW_ROW_LIMIT), PREVIEW_ROW_LIMIT)
            result = dict(result)
            result['rows'] = result['rows'][:limit]
            result['preview_limited'] = len(result.get('rows', [])) >= limit
        return result
