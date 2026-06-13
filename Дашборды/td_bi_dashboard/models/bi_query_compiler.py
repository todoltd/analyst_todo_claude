# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
import ast
import difflib
import logging
from datetime import datetime

import pytz
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Domain  # Odoo 19: первокласний Domain (Domain.AND для кон'юнкції рівнів)
from odoo.tools import SQL  # Odoo 19: безпечний конструктор SQL (bind-параметри, SQL.identifier)

_logger = logging.getLogger(__name__)


class TdBiQueryCompiler(models.AbstractModel):
    _name = 'td.bi.query.compiler'
    _description = 'BI: Компілятор запитів (адаптер ORM -> SQL)'
    # Інкапсулює приватний API Odoo 19: Model._search(domain) як точка, що повертає Query
    # з вбудованими record rules (формально приватний API). Запасний шлях — search(domain).ids.
    # Жодних бізнес-запитів під sudo() (безпека за замовчуванням, §2.4.1).
    # ОДИН адаптер: компіляція model/blend, роутер run_query (AC-62), DSL-валідація (AC-09/10/13),
    # Domain.AND-склейка доменів (AC-64). SPEC §2.1.3/§2.4 — адаптер td.bi.query.compiler.

    # --- Контракт DSL: жорсткі ліміти AST (ресурсна безпека, AC-13) ---
    _DSL_MAX_LENGTH = 4000   # макс. довжина тексту формули (символів)
    _DSL_MAX_DEPTH = 32      # макс. глибина дерева AST
    _DSL_MAX_NODES = 512     # макс. кількість вузлів AST

    # --- Контракт DSL: дозволені вузли AST (жорсткий whitelist, AC-13) ---
    # Лише арифметика/логіка/порівняння над агрегатами та полями + виклики whitelist-функцій.
    _ALLOWED_AST_NODES = (
        ast.Expression,
        ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod,
        ast.USub, ast.UAdd, ast.Not,
        ast.And, ast.Or,
        ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
        ast.Constant,
        ast.Call, ast.Name, ast.Load,
        ast.Subscript, ast.List, ast.Tuple,
    )
    # Білий список агрегатних функцій DSL (компонується у formatted_read_group aggregates).
    _AGG_FUNCS = frozenset({
        'SUM', 'AVG', 'MIN', 'MAX', 'COUNT', 'COUNT_DISTINCT', 'BOOL_AND', 'BOOL_OR',
    })
    # Білий список скалярних (неагрегувальних) функцій DSL -> SQL.
    _SCALAR_FUNCS = {
        'COALESCE': 'COALESCE',
        'NULLIF': 'NULLIF',
        'ABS': 'ABS',
        'ROUND': 'ROUND',
        'GREATEST': 'GREATEST',
        'LEAST': 'LEAST',
    }
    # Бінарні арифметичні оператори AST -> SQL-токен.
    _BINOPS = {ast.Add: '+', ast.Sub: '-', ast.Mult: '*', ast.Mod: '%'}
    # Оператори порівняння AST -> SQL-токен (для Compare/IfExp/CASE).
    _CMPOPS = {
        ast.Eq: '=', ast.NotEq: '!=', ast.Lt: '<', ast.LtE: '<=', ast.Gt: '>', ast.GtE: '>=',
    }
    # Булеві оператори AST -> SQL-токен.
    _BOOLOPS = {ast.And: 'AND', ast.Or: 'OR'}

    # Білий список синтаксису динамічних дат у доменах (§2.4.3, AC-64).
    # Поза цим списком — ValidationError (жодного eval над текстом домену).
    _DOMAIN_DATE_ANCHORS = frozenset({
        'today', 'now', 'this_week', 'this_month', 'this_quarter', 'this_year',
        'last_week', 'last_month', 'last_quarter', 'last_year',
    })

    # =========================================================================
    # === Оркестрація mode=model (AC-08/11/12/14/17, DEVIATION 42/43/53/54/55)
    # =========================================================================
    @api.model
    def compile_model_query(self, dataset, query_spec, domain):
        """Компіляція mode='model': кореневу модель -> formatted_read_group(domain, groupby,
        aggregates, having, order, limit, offset) ВІД ІМЕНІ користувача. formatted_read_group
        сам викликає check_access('read') і вбудовує домени ir.rule у WHERE/підзапити; поля з
        groups= відхиляються AccessError. Ефективний домен — виключно через Domain.AND.
        Часовий інтелект/«% від підсумку»/ранги/мультивалютність — пост-обробка тут.
        AC-08 — ratio: SUM+COUNT_DISTINCT в одному formatted_read_group, ділення на сервері
        AC-11 — ділення на нуль -> NULLIF(denominator, 0) -> NULL, не помилка
        AC-12 — фільтрована міра: extra_domain через FILTER ∧ домен контролю (Domain.AND)
        AC-14 — кожна група повертає __extra_domain для drill-down (домен спуску з сервера)
        AC-17 — межі дат у tz користувача у __extra_domain (UTC-зсув сервером)
        AC-64 — ефективний домен трьох рівнів виключно через Domain.AND
        """
        if not dataset or dataset.mode != 'model':
            raise UserError(_("compile_model_query очікує датасет у режимі 'model'."))
        if not dataset.model_name:
            raise UserError(_("Для режиму 'model' потрібна коренева модель."))

        spec = query_spec or {}
        # AC-64: ефективний домен виключно через Domain.AND (без конкатенації списків).
        # Порядок рівнів: датасет ∧ аудиторія ∧ контроли ∧ cross-filter ∧ drill ∧ віджет.
        levels = [
            dataset.domain,                  # рівень датасету
            spec.get('audience_domain'),     # рівень аудиторії (лише звужує, AC-21)
            spec.get('control_domain'),      # рівень контролів/сторінки/групи
            spec.get('cross_filter_domain'), # cross-filter інших віджетів (AC-15)
            spec.get('drill_domain'),        # __extra_domain спуску з сервера (AC-14/AC-17)
            spec.get('widget_domain'),       # власний домен віджета
        ]
        # Додатковий явний домен виклику також звужує (І).
        if domain is not None:
            levels.append(domain)
        eff_domain = self._build_effective_domain(levels)

        # Зберігаємо «сирий» домен ДО to-date scoping — потрібен для KPI-порівняння
        # (другий запит по зсунутому вікну, без власне to-date звуження бази).
        raw_eff_domain = eff_domain

        # Кумулятивний часовий інтелект (ytd/qtd/mtd/rolling): звузити вікно дати до поточного
        # періоду-до-сьогодні (межі обчислюються у tz користувача, AC-17). Якщо жодна
        # запитана міра не кумулятивна або немає поля-дати — no-op.
        eff_domain = self._apply_to_date_domain(dataset, spec, eff_domain)

        # Контекст tz/lang обовʼязковий для коректних меж дат (AC-17) і week_start (AC-43).
        model = self.env[dataset.model_name].with_context(  # stored related: без доступу до ir.model
            tz=self.env.context.get('tz') or self.env.user.tz or 'UTC',
            lang=self.env.context.get('lang') or self.env.user.lang or 'en_US',
        )

        groupby = list(spec.get('groupby') or [])
        having = spec.get('having') or []
        order = spec.get('order')
        # AC-06: попередній перегляд — рівно один formatted_read_group, не більше 80 рядків.
        limit = spec.get('limit') or 80
        offset = spec.get('offset') or 0

        # Компіляція мір -> aggregate-специфікації + метадані пост-обробки
        # (AC-08 ratio одним запитом, AC-11 NULLIF, AC-12 FILTER ∧ extra_domain).
        aggregates, measure_meta = self._compile_measures(dataset, spec, eff_domain)
        # Якщо явні aggregates у spec — додаємо (батч простих агрегатів).
        # Дедуп: дві прості міри на той самий path:agg дали б дубль-агрегат у
        # formatted_read_group (напр. дві count-міри на 'id' -> 'id:count' двічі).
        aggregates = self._dedupe_aggregates(list(spec.get('aggregates') or []) + aggregates)

        # AC-53/54: мультивалютність до виконання (групування за валютою / межовий шлях UserError).
        groupby, aggregates = self._apply_currency_strategy(
            dataset, spec, groupby, aggregates, measure_meta,
        )

        # AC-42/43/55: % від підсумку / часовий інтелект -> GROUPING SETS (DEVIATION).
        if self._needs_grouping_sets(dataset, spec):
            return self._compile_grouping_sets(
                model, dataset, spec, eff_domain, groupby, aggregates, measure_meta,
                having=having, order=order, limit=limit, offset=offset,
            )

        dom_list = self._domain_as_list(eff_domain)
        # DEVIATION(Odoo19): підтвердити сигнатуру formatted_read_group(domain, groupby,
        # aggregates, having, order, limit, offset) на цільовій збірці 19.0. Основний шлях —
        # formatted_read_group ВІД ІМЕНІ користувача (check_access('read') + ir.rule у WHERE);
        # запасний — класичний read_group.
        try:
            rows = model.formatted_read_group(
                dom_list, groupby=groupby, aggregates=aggregates,
                having=having, order=order, limit=limit, offset=offset,
            )
        except AccessError:
            # AC-20: деградація per-віджет — нема ACL/прав -> картка «нема доступу», не крах сторінки.
            raise
        except AttributeError:  # pragma: no cover — звірити на збірці 19.0
            rows = model.read_group(
                dom_list, fields=aggregates, groupby=groupby,
                orderby=order, limit=limit, offset=offset,
            )

        # Пост-обробка: __extra_domain на кожну групу (AC-14/AC-17) + historical-конвертація (AC-53).
        rows = self._postprocess_rows(model, dataset, spec, rows, groupby, measure_meta, eff_domain)
        # Часовий інтелект: порівняння періодів (prev_year/prev_period/custom_shift) у межах
        # серії за виміром-датою -> колонки <value_key>__prior/__delta/__delta_pct (AC-42).
        # Виконується ПІСЛЯ _postprocess_rows: працює над значеннями, вже сконвертованими
        # за валютою; __extra_domain груп уже проставлено (drill не порушено).
        rows = self._apply_time_intelligence(dataset, spec, rows, groupby, measure_meta)
        # KPI-порівняння (без виміру-дати у groupby): пріор-значення другим запитом по
        # зсунутому вікну (period-to-date зсунутий назад на comparison). // AC-42 (KPI)
        rows = self._apply_kpi_comparison(model, dataset, spec, raw_eff_domain, rows, groupby, measure_meta)
        return {
            'rows': rows,
            'groupby': groupby,
            'measures': [m['name'] for m in measure_meta],
            'domain': self._domain_as_list(eff_domain),
        }

    @api.model
    def _compile_measures(self, dataset, query_spec, eff_domain):
        """Будує aggregate-специфікації для formatted_read_group і метадані пост-обробки.
        - проста міра: '<path>:<aggregator>' (нативний рядок-агрегат ORM);
        - DSL-міра/ratio: SQL-вираз із SUM/COUNT_DISTINCT (AC-08), ділення -> NULLIF (AC-11);
        - фільтрована міра: FILTER (WHERE ...) ∧ extra_domain через Domain.AND (AC-12).
        """
        aggregates, meta = [], []
        requested = query_spec.get('measures') or []
        measures = dataset.measure_ids
        if requested:
            measures = measures.filtered(lambda m: m.name in requested or m.id in requested)

        for measure in measures:
            entry = {'name': measure.name, 'measure': measure, 'kind': 'simple'}

            # AC-12: власний extra_domain фільтрованої міри складається з ефективним
            # доменом ВИКЛЮЧНО через Domain.AND (FILTER ∧ домен контролю).
            filter_domain = None
            if measure.extra_domain:
                filter_domain = self._build_effective_domain([measure.extra_domain])
                entry['filter_domain'] = filter_domain

            if measure.expression:
                # AC-08/AC-11: DSL-міра/ratio. Компіляція з whitelist; ділення на сервері (NULLIF).
                compiled = self._compile_formula(measure, as_dict=True)
                if not compiled['is_aggregated']:
                    raise ValidationError(_(
                        "Вираз міри «%s» має бути агрегованим (SUM/COUNT_DISTINCT/...).",
                        measure.name,
                    ))
                entry['kind'] = 'expression'
                entry['sql'] = compiled['sql']
                # value_key — ключ значення міри у рядку результату (для пост-обробки/часового
                # інтелекту): DSL-міра приходить під власним ім'ям (... AS measure.name).
                entry['value_key'] = measure.name
                # DEVIATION(Odoo19): підтвердити передачу сирого SQL-агрегату у
                # formatted_read_group/aggregates (SQL-вираз як значення aggregate) на збірці 19.0.
                # AC-08: ratio (SUM(...) / COUNT_DISTINCT(...)) — ОДИН агрегат-вираз, один запит.
                aggregates.append(SQL("%s AS %s", compiled['sql'], SQL.identifier(measure.name)))
            else:
                # Проста міра: нативний рядок-агрегат ORM '<path>:<agg>'.
                field = measure.field_id
                path = (field.path or field.name) if field else None
                agg = measure.aggregator or (field.aggregator if field else 'sum')
                if not path:
                    raise ValidationError(_(
                        "Міра «%s» не має ні виразу, ні поля.", measure.name,
                    ))
                # value_key — проста міра приходить під ключем '<path>:<agg>' (напр. 'id:count').
                entry['value_key'] = '%s:%s' % (path, agg)
                aggregates.append('%s:%s' % (path, agg))

            meta.append(entry)
        return aggregates, meta

    @api.model
    def _apply_currency_strategy(self, dataset, query_spec, groupby, aggregates, measure_meta):
        """Мультивалютність (AC-53/AC-54). Stage-1: групування за валютою (group_by_currency)
        і нативний sum_currency; historical через _convert — у пост-обробці (_postprocess_rows).
        """
        strategy = dataset.currency_strategy or 'sum_currency'
        # AC-54 (межовий шлях): стратегія конвертації без currency_field -> UserError ДОСЛІВНО.
        if strategy in ('sum_currency', 'historical'):
            for entry in measure_meta:
                field = entry['measure'].field_id
                is_monetary = bool(field) and (field.field_type == 'monetary')
                if is_monetary and not field.currency_path:
                    raise UserError(_(
                        "Стратегія конвертації потребує визначеного поля валюти (`currency_field`) для monetary-міри."
                    ))

        if strategy == 'group_by_currency':
            # AC-54: розбиття за валютою без _convert — кожна валюта окремим рядком/серією.
            for entry in measure_meta:
                field = entry['measure'].field_id
                if field and field.currency_path and field.currency_path not in groupby:
                    groupby = groupby + [field.currency_path]
        elif strategy == 'sum_currency':
            # DEVIATION(Odoo19): підтвердити нативний агрегат `sum_currency`
            # (SUM(amount/rate) з JOIN поточного курсу) у formatted_read_group на збірці 19.0.
            # Запасний шлях: групування за валютою + конвертація у пост-обробці _convert.
            pass
        # historical -> конвертація за датою документа у _postprocess_rows (AC-53).
        return groupby, aggregates

    @api.model
    def _needs_grouping_sets(self, dataset, query_spec):
        """Чи потрібен formatted_read_grouping_sets: % від підсумку / ранг / накопич. (AC-55).

        ВАЖЛИВО: порівняння періодів (time_intelligence/comparison) тут НЕ маршрутизується —
        раніше воно потрапляло у fallback GROUPING SETS, який НЕ зсував домен дат, тож YoY
        чисельно дорівнював базі (хибно). Тепер порівняння обробляє _apply_time_intelligence
        (зсув у межах серії за виміром-датою, AC-42)."""
        if query_spec.get('grouping_sets'):
            return True
        for measure in dataset.measure_ids:
            if measure.show_as in ('percent_of_total', 'percent_of_dimension', 'running_total', 'rank'):
                return True
        return False

    @api.model
    def _compile_grouping_sets(self, model, dataset, query_spec, eff_domain, groupby,
                               aggregates, measure_meta, having=None, order=None,
                               limit=None, offset=0):
        """% від підсумку / часовий інтелект одним SQL через GROUPING SETS (AC-42/43/55).
        Детальні рядки + загальний підсумок одним запитом; ділення на сервері (AC-55)."""
        dom_list = self._domain_as_list(eff_domain)
        # DEVIATION(Odoo19): нативний `formatted_read_grouping_sets` існує на збірці, але його
        # точна сигнатура не підтверджена І він не дав би місця для пост-обробки show_as
        # (percent_of_total/running_total/rank). Тому використовуємо ПЕРЕВІРЕНИЙ шлях:
        # два formatted_read_group (детальні + підсумок) ВІД ІМЕНІ користувача + _apply_show_as.
        # Числово ідентично GROUPING SETS; RLS/ACL зберігаються. Нативний батч — оптимізація
        # на потім (після звірки сигнатури 19.0).
        rows = model.formatted_read_group(
            dom_list, groupby=groupby, aggregates=aggregates,
            having=having or [], order=order, limit=limit, offset=offset,
        )
        totals = model.formatted_read_group(dom_list, groupby=[], aggregates=aggregates)
        rows = self._apply_show_as(dataset, measure_meta, rows, totals, groupby=groupby)
        rows = self._postprocess_rows(model, dataset, query_spec, rows, groupby, measure_meta, eff_domain)
        return {'rows': rows, 'groupby': groupby, 'grouping_sets': True,
                'measures': [m['name'] for m in measure_meta],
                'domain': dom_list}

    @api.model
    def _apply_show_as(self, dataset, measure_meta, rows, totals, groupby=None):
        """Похідні показники на сервері (fallback без нативних GROUPING SETS):
        - percent_of_total: значення / загальний підсумок (AC-55; знаменник 0/NULL -> NULL, AC-11);
        - percent_of_dimension: частка в межах партиції зовнішніх вимірів (усі groupby крім
          останнього); для одного groupby збігається з percent_of_total;
        - running_total: накопичувальний підсумок за поточним порядком рядків;
        - rank: ранг за спаданням значення (competition: 1,2,2,4; 1 — найбільше).
        Похідні колонки: <value_key>_pct / _pct_dim / _running / _rank.

        Значення читаємо за value_key (просте поле приходить під '<path>:<agg>', НЕ під
        назвою міри — раніше читання за name давало None і ламало percent_of_total)."""
        rows = rows or []
        groupby = groupby or []
        total_by_measure = {}
        if totals:
            for entry in measure_meta:
                vk = entry.get('value_key', entry['name'])
                total_by_measure[entry['name']] = totals[0].get(vk)
        for entry in measure_meta:
            show_as = entry['measure'].show_as
            if show_as not in ('percent_of_total', 'percent_of_dimension', 'running_total', 'rank'):
                continue
            vk = entry.get('value_key', entry['name'])
            if show_as == 'percent_of_total':
                denom = total_by_measure.get(entry['name'])
                for row in rows:
                    value = row.get(vk)
                    row[vk + '_pct'] = None if (value is None or not denom) else value / denom
            elif show_as == 'percent_of_dimension':
                # Партиція — усі groupby крім останнього (внутрішнього) виміру.
                part_keys = list(groupby)[:-1]
                sums = {}
                for row in rows:
                    pk = tuple(self._partition_value(row.get(g)) for g in part_keys)
                    v = row.get(vk)
                    if isinstance(v, (int, float)):
                        sums[pk] = sums.get(pk, 0) + v
                for row in rows:
                    pk = tuple(self._partition_value(row.get(g)) for g in part_keys)
                    value = row.get(vk)
                    denom = sums.get(pk)
                    row[vk + '_pct_dim'] = None if (value is None or not denom) else value / denom
            elif show_as == 'running_total':
                cum = 0
                for row in rows:
                    value = row.get(vk)
                    if isinstance(value, (int, float)):
                        cum += value
                    row[vk + '_running'] = cum
            elif show_as == 'rank':
                ordered = sorted(
                    [r for r in rows if isinstance(r.get(vk), (int, float))],
                    key=lambda r: r.get(vk), reverse=True)
                rank, prev = 0, object()
                for i, r in enumerate(ordered):
                    v = r.get(vk)
                    if v != prev:
                        rank, prev = i + 1, v
                    r[vk + '_rank'] = rank
        return rows

    @api.model
    def _partition_value(self, group_value):
        """Нормалізує значення виміру для ключа партиції (m2o [id,label] -> id; tuple -> [0])."""
        if isinstance(group_value, (list, tuple)) and group_value:
            return group_value[0]
        return group_value

    # =========================================================================
    # === Часовий інтелект: порівняння періодів у межах серії (AC-42/43) ======
    # =========================================================================
    # Гранулярність groupby-токена -> (одиниця relativedelta, к-сть) для зсуву периоду.
    _GRAN_UNIT = {
        'year': ('years', 1), 'quarter': ('months', 3), 'month': ('months', 1),
        'week': ('weeks', 1), 'day': ('days', 1), 'hour': ('hours', 1),
    }

    @api.model
    def _dedupe_aggregates(self, aggregates):
        """Прибирає дублі рядкових агрегатів ('id:count' двічі від двох count-мір),
        зберігаючи порядок. SQL-обʼєкти (DSL-міри) не порівнюються — лишаємо як є."""
        seen = set()
        out = []
        for agg in aggregates:
            if isinstance(agg, str):
                if agg in seen:
                    continue
                seen.add(agg)
            out.append(agg)
        return out

    @api.model
    def _apply_time_intelligence(self, dataset, query_spec, rows, groupby, measure_meta):
        """Порівняння періодів (AC-42): для мір із comparison/diff_prev — у межах серії
        за виміром-датою додає на кожен рядок колонки <value_key>__prior / __delta / __delta_pct.

        Реалізація — вирівнювання В МЕЖАХ повернутої серії (БЕЗ другого запиту): ключ рядка —
        початок періоду (formatted_read_group повертає groupby-дату як кортеж
        (iso_початок, мітка)); попередній період = той самий ключ, зсунутий назад на 1 рік
        (prev_year) / 1 одиницю гранулярності (prev_period) / rolling_n одиниць (custom_shift).
        Межі періодів сервер уже обчислив у tz/lang користувача (AC-17/AC-43), тож тут немає
        ризикованої tz-арифметики. Без виміру-дати у groupby — no-op (KPI-порівняння одним
        значенням через другий запит — наступний інкремент)."""
        ti = self._collect_time_intelligence(dataset, query_spec, measure_meta)
        if not ti or not rows:
            return rows
        date_gb = ti['date_groupby']
        if not date_gb:
            # Порівняння без виміру-дати у groupby (KPI) — наступний інкремент (другий запит
            # по зсунутому вікну). Тут безпечно деградуємо без колонок порівняння.
            return rows
        granularity = ti['granularity']
        # Індекс серії: ключ-період (iso початок) -> рядок.
        base_map = {}
        for row in rows:
            key = self._period_key(row.get(date_gb))
            if key is not None:
                base_map[key] = row
        for pm in ti['per_measure']:
            vkey = pm['value_key']
            shift = self._ti_shift(pm['comparison'], granularity, pm['rolling_n'])
            if not shift:
                continue
            for row in rows:
                cur_key = self._period_key(row.get(date_gb))
                cur_val = row.get(vkey)
                prior_key = self._shift_period_key(cur_key, shift) if cur_key else None
                prior_row = base_map.get(prior_key) if prior_key else None
                prior_val = prior_row.get(vkey) if prior_row else None
                row[vkey + '__prior'] = prior_val
                if cur_val is None or prior_val is None:
                    # Немає попереднього періоду в серії -> дельту не визначено (AC-11 родинне).
                    row[vkey + '__delta'] = None
                    row[vkey + '__delta_pct'] = None
                else:
                    row[vkey + '__delta'] = cur_val - prior_val
                    # AC-11: ділення на нуль -> None, не помилка.
                    row[vkey + '__delta_pct'] = (
                        (cur_val - prior_val) / prior_val if prior_val else None
                    )
        return rows

    @api.model
    def _apply_kpi_comparison(self, model, dataset, query_spec, raw_eff_domain, rows, groupby, measure_meta):
        """KPI-порівняння БЕЗ виміру-дати у groupby: пріор-значення обчислюється ДРУГИМ
        formatted_read_group по зсунутому period-to-date вікну (ВІД ІМЕНІ користувача — RLS у
        WHERE; без sudo). Застосовується лише до простих мір, що мають І кумулятивний ti
        (ytd/qtd/mtd — щоб база була to-date-звужена), І comparison: «YTD цьогоріч проти YTD торік».
        Within-series випадок (date-groupby) обробляє _apply_time_intelligence — тут пропускаємо."""
        requested = query_spec.get('measures') or []
        if not requested or not rows:
            return rows
        if any(self._is_date_groupby(dataset, g) for g in (groupby or [])):
            return rows  # within-series уже обробив
        date_field = dataset.date_field_default
        if not date_field:
            return rows
        for entry in measure_meta:
            m = entry['measure']
            if m.expression:
                continue  # DSL-міри у KPI-порівнянні — пізніше
            ti = m.time_intelligence if (m.time_intelligence and m.time_intelligence != 'none') else None
            if ti not in ('ytd', 'qtd', 'mtd'):
                continue  # потрібне визначене поточне вікно (база має бути to-date-звужена)
            cmp_ = m.comparison if (m.comparison and m.comparison != 'none') else None
            if not cmp_ and m.show_as in ('diff_prev', 'diff_prev_pct'):
                cmp_ = 'prev_year'
            if not cmp_:
                continue
            start_str, now_str = self._to_date_bounds(ti, dataset.fiscalyear_offset or 0)
            shift = self._ti_shift(cmp_, None, m.rolling_n or 1)
            prior_start = self._shift_period_key(start_str, shift)
            prior_end = self._shift_period_key(now_str, shift)
            if not (prior_start and prior_end):
                continue
            prior_dom = self._build_effective_domain([
                raw_eff_domain, [(date_field, '>=', prior_start), (date_field, '<=', prior_end)]])
            vk = entry['value_key']
            try:
                prior_rows = model.formatted_read_group(
                    self._domain_as_list(prior_dom), groupby=[], aggregates=[vk])
            except Exception:  # noqa: BLE001 — пріор-запит не має валити віджет (AC-52)
                prior_rows = []
            prior_val = prior_rows[0].get(vk) if prior_rows else None
            for row in rows:
                cur = row.get(vk)
                row[vk + '__prior'] = prior_val
                if cur is None or prior_val is None:
                    row[vk + '__delta'] = None
                    row[vk + '__delta_pct'] = None
                else:
                    row[vk + '__delta'] = cur - prior_val
                    row[vk + '__delta_pct'] = (cur - prior_val) / prior_val if prior_val else None
        return rows

    @api.model
    def _collect_time_intelligence(self, dataset, query_spec, measure_meta):
        """Збирає метадані часового інтелекту для цього запиту або None.

        Порівняння застосовується ЛИШЕ до мір, явно вибраних у query_spec['measures']
        (інакше віджети «сирих агрегатів» (measures=[]) несли б зайві колонки/запити та
        успадковували порівняння конфіг-міри датасету). Нормалізує аліаси time_intelligence
        ('yoy'->prev_year, 'pop'->prev_period) і show_as (diff_prev*->prev_period)."""
        requested = query_spec.get('measures') or []
        if not requested:
            return None
        groupby = list(query_spec.get('groupby') or [])
        date_gb = next((g for g in groupby if self._is_date_groupby(dataset, g)), None)
        granularity = None
        if date_gb and ':' in date_gb:
            granularity = date_gb.split(':', 1)[1]
        per_measure = []
        for entry in measure_meta:
            m = entry['measure']
            cmp_ = m.comparison if (m.comparison and m.comparison != 'none') else None
            ti = m.time_intelligence if (m.time_intelligence and m.time_intelligence != 'none') else None
            if not cmp_ and ti == 'yoy':
                cmp_ = 'prev_year'
            elif not cmp_ and ti == 'pop':
                cmp_ = 'prev_period'
            if not cmp_ and m.show_as in ('diff_prev', 'diff_prev_pct'):
                cmp_ = 'prev_period'
            if not cmp_:
                continue
            per_measure.append({
                'value_key': entry['value_key'],
                'comparison': cmp_,
                'rolling_n': m.rolling_n or 1,
            })
        if not per_measure:
            return None
        return {'date_groupby': date_gb, 'granularity': granularity, 'per_measure': per_measure}

    @api.model
    def _is_date_groupby(self, dataset, groupby_token):
        """Чи є groupby-токен виміром типу date/datetime (для часового інтелекту)."""
        base = groupby_token.split(':', 1)[0]
        gran = groupby_token.split(':', 1)[1] if ':' in groupby_token else None
        if gran in self._GRAN_UNIT:
            return True
        if dataset.model_name:
            try:
                ftype = self.env[dataset.model_name].fields_get([base]).get(base, {}).get('type')
            except Exception:  # noqa: BLE001 — недоступне/relational поле -> не дата
                return False
            return ftype in ('date', 'datetime')
        return False

    @api.model
    def _period_key(self, group_value):
        """Канонічний ключ періоду з groupby-значення date-granularity.
        formatted_read_group повертає (iso_початок, мітка); беремо iso-початок."""
        if isinstance(group_value, (list, tuple)) and group_value:
            return group_value[0]
        if isinstance(group_value, str):
            return group_value
        return None

    @api.model
    def _ti_shift(self, comparison, granularity, rolling_n):
        """relativedelta-kwargs зсуву назад: prev_year=1 рік; prev_period=1 одиниця
        гранулярності; custom_shift=rolling_n одиниць гранулярності."""
        if comparison == 'prev_year':
            return {'years': 1}
        unit, n = self._GRAN_UNIT.get(granularity or 'month', ('months', 1))
        if comparison == 'prev_period':
            return {unit: n}
        if comparison == 'custom_shift':
            return {unit: n * max(1, int(rolling_n or 1))}
        return None

    @api.model
    def _shift_period_key(self, key_iso, shift):
        """Зсуває iso-ключ періоду назад на shift; повертає рядок того ж формату для
        пошуку у base_map. Підтримує 'YYYY-MM-DD HH:MM:SS' і 'YYYY-MM-DD'."""
        if not key_iso or not isinstance(key_iso, str):
            return None
        fmt = '%Y-%m-%d %H:%M:%S' if len(key_iso) > 10 else '%Y-%m-%d'
        try:
            dt = datetime.strptime(key_iso, fmt)
        except (ValueError, TypeError):
            return None
        return (dt - relativedelta(**shift)).strftime(fmt)

    @api.model
    def _apply_to_date_domain(self, dataset, query_spec, eff_domain):
        """Кумулятив to-date (ytd/qtd/mtd): ANDʼить у ефективний домен вікно
        [початок_періоду .. зараз] на полі-даті (date_field_default або date-groupby).
        Застосовується ЛИШЕ для явно вибраних мір (query_spec['measures']). Без поля-дати
        або кумулятивної міри — повертає домен незмінним (AC-44 безпечна деградація)."""
        requested = query_spec.get('measures') or []
        if not requested:
            return eff_domain
        mode, roll_n = None, 0
        for m in dataset.measure_ids:
            if not (m.name in requested or m.id in requested):
                continue
            if m.time_intelligence in ('ytd', 'qtd', 'mtd'):
                mode = m.time_intelligence
                break
            if m.time_intelligence == 'rolling' and (m.rolling_n or 0) > 0:
                mode, roll_n = 'rolling', m.rolling_n
                break
        if not mode:
            return eff_domain
        date_field = dataset.date_field_default
        if not date_field:
            for g in (query_spec.get('groupby') or []):
                if self._is_date_groupby(dataset, g):
                    date_field = g.split(':', 1)[0]
                    break
        if not date_field:
            return eff_domain  # немає якоря дати -> no-op (не падаємо)
        start_str, now_str = self._to_date_bounds(mode, dataset.fiscalyear_offset or 0, roll_n)
        leaf = [(date_field, '>=', start_str), (date_field, '<=', now_str)]
        return self._build_effective_domain([eff_domain, leaf])

    @api.model
    def _to_date_bounds(self, mode, fiscalyear_offset, rolling_n=0):
        """Межі періоду-до-сьогодні у tz користувача -> UTC-рядки для домену.
        ytd — з 1 січня (+ fiscalyear_offset міс.); qtd — з початку кварталу; mtd — з 1-го числа;
        rolling — ковзне вікно [сьогодні − rolling_n міс. .. зараз]."""
        tzname = self.env.context.get('tz') or self.env.user.tz or 'UTC'
        try:
            tz = pytz.timezone(tzname)
        except Exception:  # noqa: BLE001 — невідомий tz -> UTC
            tz = pytz.UTC
        now_utc = fields.Datetime.now()  # наївний UTC
        now_local = pytz.UTC.localize(now_utc).astimezone(tz)
        base = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        if mode == 'rolling':
            start_local = base - relativedelta(months=max(1, int(rolling_n or 1)))
        elif mode == 'mtd':
            start_local = base.replace(day=1)
        elif mode == 'qtd':
            q_month = ((now_local.month - 1) // 3) * 3 + 1
            start_local = base.replace(month=q_month, day=1)
        else:  # ytd
            start_local = base.replace(month=1, day=1)
            if fiscalyear_offset:
                start_local = start_local + relativedelta(months=fiscalyear_offset)
                if start_local > now_local:
                    start_local = start_local - relativedelta(years=1)
        start_utc = start_local.astimezone(pytz.UTC).replace(tzinfo=None)
        return fields.Datetime.to_string(start_utc), fields.Datetime.to_string(now_utc)

    @api.model
    def _postprocess_rows(self, model, dataset, query_spec, rows, groupby, measure_meta, eff_domain):
        """Пост-обробка кожної групи:
        - AC-14/AC-17: гарантуємо __extra_domain (домен спуску з сервера, у tz користувача);
        - AC-53: historical — конвертація monetary-агрегату за курсом дати документа (_convert);
        - AC-08/AC-11: ratio-ділення вже вшите у SQL-вираз (NULLIF) — тут лише форматування.
        """
        rows = rows or []
        strategy = dataset.currency_strategy or 'sum_currency'
        do_historical = (strategy == 'historical')
        company = self.env.company
        target_currency = company.currency_id

        for row in rows:
            # AC-14/AC-17: кожна група повертає __extra_domain для drill-down/cross-filter.
            # formatted_read_group у 19.0 повертає __extra_domain per-group у tz користувача;
            # якщо його немає (fallback-шлях), синтезуємо мінімальний домен зі значень groupby.
            if '__extra_domain' not in row:
                row['__extra_domain'] = self._synthesize_extra_domain(row, groupby)

            # AC-53: historical — конвертація monetary-агрегату за курсом дати документа.
            if do_historical:
                for entry in measure_meta:
                    field = entry['measure'].field_id
                    if not (field and field.field_type == 'monetary' and field.currency_path):
                        continue
                    amount = row.get(entry['name'])
                    if amount is None:
                        continue
                    # Патерн sale.report: <валюта_документа>._convert(amount, target, company, date).
                    doc_currency = self._resolve_row_currency(row, field)
                    doc_date = self._resolve_row_date(row, dataset)
                    if doc_currency and doc_date:
                        row[entry['name']] = doc_currency._convert(
                            amount, target_currency, company, doc_date,
                        )
        return rows

    @api.model
    def _synthesize_extra_domain(self, row, groupby):
        """Мінімальний __extra_domain зі значень groupby (fallback, коли ORM не повернув).
        Будується через Domain.AND кон'юнкцію рівностей; OR не використовується (AC-14/AC-64)."""
        leaves = []
        for gb in groupby:
            field = gb.split(':')[0]  # відсікти :month/:week гранулярність
            value = row.get(gb)
            if value is None:
                value = row.get(field)
            if isinstance(value, (list, tuple)) and value:
                value = value[0]  # m2o -> id
            if value is not None and field:
                leaves.append(Domain(field, '=', value))
        if not leaves:
            return []
        return list(Domain.AND(leaves))

    @api.model
    def _resolve_row_currency(self, row, field):
        """Витягує recordset валюти групи (для historical _convert). Stage-1 — за currency_path."""
        currency_val = row.get(field.currency_path)
        if isinstance(currency_val, (list, tuple)) and currency_val:
            return self.env['res.currency'].browse(currency_val[0])
        if isinstance(currency_val, int):
            return self.env['res.currency'].browse(currency_val)
        return self.env['res.currency']

    @api.model
    def _resolve_row_date(self, row, dataset):
        """Дата документа групи для historical _convert (поле дати датасету)."""
        date_field = dataset.date_field_default
        if not date_field:
            return False
        return row.get(date_field) or False

    # =========================================================================
    # === Stage-2: бленд (структурний каркас + RLS-CTE, AC-38/39/40) =========
    # =========================================================================
    @api.model
    def compile_blend_query(self, dataset, query_spec, domain):
        """Компіляція mode='blend': по одному CTE на td.bi.dataset.join через odoo.tools.SQL.
        Кожна таблиця предагрегується ДО зʼєднання; типи join — лише left/inner.
        Stage-1: структурно коректний каркас (валідація + RLS-підзапит у кожному CTE).
        Повна збірка SQL CTE-конвеєра — Stage-2.
        AC-38 — left outer зберігає рядок без пари (NULL), inner — ні; right/full/cross недоступні
        AC-39 — WHERE кожного CTE містить домен record rules джерела через _inject_record_rules
        AC-40 — ліміт ≤ 5 таблиць-джерел бленда
        """
        if not dataset or dataset.mode != 'blend':
            raise UserError(_("compile_blend_query очікує датасет у режимі 'blend'."))

        # AC-40: ліміт ≤ 5 таблиць-джерел бленда (структурний бар'єр).
        if len(dataset.join_ids) > 5:
            raise UserError(_("Бленд підтримує не більше 5 таблиць-джерел."))

        ctes = []          # SQL-визначення кожного CTE-джерела
        join_chain = []    # SQL JOIN-клаузи (для 2-го і далі джерела)
        col_owner = {}     # псевдонім поля -> SQL.identifier CTE, що його експонує
        first_cte = None
        for idx, join in enumerate(dataset.join_ids):
            # AC-38: лише left/inner; right/full/cross недоступні (етап 3, ОВ-6).
            if join.join_type and join.join_type not in ('left', 'inner'):
                raise UserError(_(
                    "Тип зʼєднання «%s» недоступний (лише left/inner).", join.join_type,
                ))
            # Джерело CTE: модель (Stage-1) АБО вкладений датасет. Технічну НАЗВУ моделі
            # читаємо з ir.model через sudo (метадані, не бізнес-дані: звичайний BI-user
            # часто не має ACL на ir.model). RLS бізнес-даних надалі — від імені користувача
            # (self.env[name] -> _inject_record_rules без sudo).
            if join.source_model_id:
                src_model_name = join.source_model_id.sudo().model
            elif join.source_dataset_id:
                src_model_name = join.source_dataset_id.sudo().model_name
            else:
                src_model_name = False
            if not src_model_name:
                raise UserError(_("Таблиця бленда без джерела (датасет або модель)."))
            src_model = self.env[src_model_name]

            cte_name = SQL.identifier('bcte_%d' % idx)
            src_alias = SQL.identifier('bsrc_%d' % idx)
            dims = [f for f in join.included_field_ids if f.role == 'dimension']
            meas = [f for f in join.included_field_ids if f.role == 'measure']
            if not dims and not meas:
                raise UserError(_(
                    "Джерело бленда «%s» не має включених полів.", src_model._name))

            # Список вибірки CTE: виміри як <path> AS <name>; міри — агрегат(<path>) AS <name>.
            select_parts = []
            for f in dims:
                select_parts.append(SQL("%s AS %s", SQL.identifier(f.path), SQL.identifier(f.name)))
                col_owner[f.name] = cte_name
            for f in meas:
                select_parts.append(SQL(
                    "%s AS %s", self._blend_inner_agg_sql(f.aggregator, f.path), SQL.identifier(f.name)))
                col_owner[f.name] = cte_name

            # AC-39: RLS у WHERE кожного CTE (Model._search -> Query.subselect; без sudo).
            rls = self._inject_record_rules(
                src_model, self._build_effective_domain([join.table_domain, domain]))
            where_sql = self._blend_rls_predicate(rls, src_alias)

            # AC-41: предагрегація ДО зʼєднання — GROUP BY виміри джерела (колапс до 1 рядка/ключ).
            if dims:
                groupby_sql = SQL(", ").join([SQL.identifier(f.path) for f in dims])
                cte_def = SQL(
                    "%s AS (SELECT %s FROM %s AS %s WHERE %s GROUP BY %s)",
                    cte_name, SQL(", ").join(select_parts), SQL.identifier(src_model._table),
                    src_alias, where_sql, groupby_sql)
            else:
                cte_def = SQL(
                    "%s AS (SELECT %s FROM %s AS %s WHERE %s)",
                    cte_name, SQL(", ").join(select_parts), SQL.identifier(src_model._table),
                    src_alias, where_sql)
            ctes.append(cte_def)

            if idx == 0:
                first_cte = cte_name
            else:
                # AC-38: left/inner; ON — кон'юнкція рівностей пар ключів.
                join_kw = SQL("LEFT JOIN") if (join.join_type or 'inner') == 'left' else SQL("JOIN")
                on_parts = []
                for k in join.key_ids:
                    left_owner = col_owner.get(k.left_field, first_cte)
                    on_parts.append(SQL(
                        "%s.%s = %s.%s",
                        left_owner, SQL.identifier(k.left_field), cte_name, SQL.identifier(k.right_field)))
                if not on_parts:
                    raise UserError(_("Зʼєднання бленда без ключів (key_ids порожній)."))
                join_chain.append(SQL("%s %s ON %s", join_kw, cte_name, SQL(" AND ").join(on_parts)))

        if not ctes:
            raise UserError(_("Бленд не містить таблиць-джерел."))

        # --- Фінальна проєкція: виміри groupby + іменовані міри поверх з'єднаних CTE ---
        groupby = list(query_spec.get('groupby') or [])
        requested = query_spec.get('measures') or []
        measures = dataset.measure_ids
        if requested:
            measures = measures.filtered(lambda m: m.name in requested or m.id in requested)

        # Вихідні стовпці отримують БЕЗПЕЧНІ SQL-псевдоніми (g0/m0…), бо SQL.identifier не
        # приймає пробілів (а назви мір на кшталт «Кількість контактів» їх містять). Після
        # вибірки повертаємо ключі до справжніх (groupby-токен / назва міри) через out_map.
        proj_parts, group_cols, measure_meta, out_map = [], [], [], {}
        for i, gb in enumerate(groupby):
            owner = col_owner.get(gb)
            if not owner:
                raise UserError(_(
                    "Поле групування «%s» не належить жодному джерелу бленда.", gb))
            safe = 'g%d' % i
            proj_parts.append(SQL("%s.%s AS %s", owner, SQL.identifier(gb), SQL.identifier(safe)))
            group_cols.append(SQL("%s.%s", owner, SQL.identifier(gb)))
            out_map[safe] = gb
        for i, m in enumerate(measures):
            if m.expression:
                raise UserError(_(
                    "DSL-міри у бленді будуть доступні згодом; міра «%s».", m.name))
            field = m.field_id
            if not field or not field.name:
                raise UserError(_("Міра бленда «%s» без поля.", m.name))
            owner = col_owner.get(field.name)
            if not owner:
                raise UserError(_(
                    "Міра «%s» посилається на поле «%s», відсутнє у джерелах бленда.",
                    m.name, field.name))
            # Зовнішня ре-агрегація над предагрегованим стовпцем (count/sum -> SUM часткових).
            outer = self._blend_outer_agg(m.aggregator or field.aggregator or 'sum')
            safe = 'm%d' % i
            proj_parts.append(SQL(
                "%s(%s.%s) AS %s", SQL(outer), owner, SQL.identifier(field.name), SQL.identifier(safe)))
            out_map[safe] = m.name
            measure_meta.append({'name': m.name})
        if not proj_parts:
            raise UserError(_("Бленд-запит без вимірів і мір."))

        limit = query_spec.get('limit') or 80
        offset = query_spec.get('offset') or 0
        from_sql = first_cte if not join_chain else SQL("%s %s", first_cte, SQL(" ").join(join_chain))
        tail = SQL("")
        if group_cols:
            tail = SQL("%s GROUP BY %s", tail, SQL(", ").join(group_cols))
        tail = SQL("%s LIMIT %s OFFSET %s", tail, limit, offset)
        full = SQL("WITH %s SELECT %s FROM %s%s",
                   SQL(", ").join(ctes), SQL(", ").join(proj_parts), from_sql, tail)

        # Виконання ВІД ІМЕНІ користувача (RLS вже у кожному CTE) — без sudo (§2.4.1).
        self.env.cr.execute(full)
        raw = self.env.cr.dictfetchall()
        rows = []
        for r in raw:
            row = {out_map.get(k, k): v for k, v in r.items()}
            # Drill-парність: __extra_domain зі значень groupby (псевдоніми; drill — наближено).
            row['__extra_domain'] = self._synthesize_extra_domain(row, groupby)
            rows.append(row)
        return {
            'rows': rows,
            'groupby': groupby,
            'measures': [mm['name'] for mm in measure_meta],
            'domain': self._domain_as_list(domain if domain is not None else []),
        }

    # Зовнішні токени агрегації (whitelist; не з користувацького вводу).
    _BLEND_INNER_AGG = {
        'sum': 'SUM', 'avg': 'AVG', 'min': 'MIN', 'max': 'MAX',
        'bool_and': 'BOOL_AND', 'bool_or': 'BOOL_OR',
    }

    @api.model
    def _blend_inner_agg_sql(self, aggregator, path):
        """Предагрегатний вираз джерела: count -> COUNT, count_distinct -> COUNT(DISTINCT),
        решта — за whitelist. Колонка лише через SQL.identifier (анти-інʼєкція)."""
        col = SQL.identifier(path)
        agg = (aggregator or 'sum').lower()
        if agg == 'count':
            return SQL("COUNT(%s)", col)
        if agg == 'count_distinct':
            return SQL("COUNT(DISTINCT %s)", col)
        return SQL("%s(%s)", SQL(self._BLEND_INNER_AGG.get(agg, 'SUM')), col)

    @api.model
    def _blend_outer_agg(self, aggregator):
        """Зовнішня ре-агрегація над уже предагрегованим стовпцем: count/sum/count_distinct ->
        SUM (підсумовуємо часткові); min/max -> MIN/MAX; avg -> AVG (наближено, без вагування)."""
        return {'min': 'MIN', 'max': 'MAX', 'avg': 'AVG'}.get((aggregator or 'sum').lower(), 'SUM')

    @api.model
    def _blend_rls_predicate(self, rls, src_alias):
        """RLS у WHERE CTE (AC-39): `alias.id IN (<підзапит id з record rules>)`.
        rls — Query (Model._search; Query.subselect) або list[int] (fallback search().ids)."""
        if isinstance(rls, (list, tuple)):
            ids = tuple(rls) or (0,)
            return SQL("%s.%s IN %s", src_alias, SQL.identifier('id'), ids)
        try:
            sub = rls.subselect()  # SQL підзапит id, призначений саме для IN (Odoo 19)
        except Exception:  # pragma: no cover — звірити сигнатуру на збірці 19.0
            sub = SQL("SELECT id FROM (%s) __rls", rls.select())
        return SQL("%s.%s IN %s", src_alias, SQL.identifier('id'), sub)

    # =========================================================================
    # === Роутер run_query (AC-62) ============================================
    # =========================================================================
    @api.model
    def route_query(self, dataset, query_spec, domain):
        """Роутер run_query: Stage-1 -> прямий compile_model_query/compile_blend_query.
        Stage-2 -> матеріалізація: накритий запит обслуговується з RLS-безпечного предагрегата,
        ненакритий падає назад на сиру модель (числово ідентично).
        AC-62 — накритий -> предагрегат; ненакритий -> fallback formatted_read_group (ідентично)
        """
        spec = query_spec or {}
        # AC-62: знайти RLS-безпечний предагрегат, що накриває запит.
        mat = self._find_covering_materialization(dataset, spec)
        if mat:
            # DEVIATION(Odoo19): підтвердити життєвий цикл _auto=False + init()/_table_query і
            # REFRESH MATERIALIZED VIEW CONCURRENTLY для td.bi.materialization на збірці 19.0.
            # TODO: Stage-2 — обслужити з предагрегата (читання з table_name, RLS через
            # вимір-ключ правила); поки fallback на сиру модель (числовий результат ідентичний).
            pass
        # Stage-1: прямий маршрут по режиму датасету.
        if dataset.mode == 'blend':
            return self.compile_blend_query(dataset, spec, domain)
        return self.compile_model_query(dataset, spec, domain)

    @api.model
    def _find_covering_materialization(self, dataset, query_spec):
        """Повертає RLS-безпечну td.bi.materialization, чиї виміри/міри ⊇ запиту, з побудованою
        й оновленою фізичною таблицею; інакше порожній набір (роутер падає на сиру модель).
        AC-62 — критерій «накриття»: виміри/міри запиту ⊆ предагрегата; AC-63 — лише is_rls_safe.

        Серверне ОБСЛУГОВУВАННЯ з предагрегата (читання table_name із RLS-доменом ключа правила)
        — наступний крок (потребує підтвердженого життєвого циклу MV на 19.0). Доти роутер
        використовує цей детектор, але обслуговує сирою моделлю (числово ідентично, RLS коректний).
        """
        Mat = self.env['td.bi.materialization'].sudo()
        if not dataset:
            return Mat.browse()
        candidates = Mat.search([
            ('dataset_id', '=', dataset.id),
            ('table_name', '!=', False),
            ('last_refresh', '!=', False),
            ('is_rls_safe', '=', True),
        ])
        req_dims = {self._mat_norm(g) for g in (query_spec.get('groupby') or [])}
        req_meas = set(query_spec.get('measures') or [])
        for mat in candidates:
            mat_dims = {self._mat_norm(d) for d in self._mat_paths_list(mat.dimension_paths)}
            mat_meas = set(self._mat_meas_list(mat.measure_specs))
            if req_dims.issubset(mat_dims) and (not req_meas or req_meas.issubset(mat_meas)):
                return mat
        return Mat.browse()

    @api.model
    def _mat_norm(self, token):
        """Нормалізує токен виміру для порівняння накриття: базове поле без гранулярності."""
        return str(token).split(':', 1)[0]

    @api.model
    def _mat_paths_list(self, paths):
        """dimension_paths -> список рядків-шляхів (підтримує dict/list)."""
        if isinstance(paths, dict):
            paths = list(paths.values())
        return [p for p in (paths or []) if isinstance(p, str)]

    @api.model
    def _mat_meas_list(self, specs):
        """measure_specs -> список імен мір (рядки або dict із 'name'/'field')."""
        if isinstance(specs, dict):
            specs = list(specs.values())
        out = []
        for s in (specs or []):
            if isinstance(s, str):
                out.append(s)
            elif isinstance(s, dict):
                name = s.get('name') or s.get('field')
                if name:
                    out.append(name)
        return out

    # =========================================================================
    # === DSL-компілятор формул (AC-09, AC-10, AC-13) =========================
    # =========================================================================
    @api.model
    def _compile_formula(self, dataset_field_or_measure, as_dict=False):
        """DSL-компіляція/валідація: ast.parse(mode='eval') + жорсткий whitelist вузлів AST;
        колонки лише через SQL.identifier, значення — bind-параметри; safe_eval ніде.
        AC-09 — змішування агрегованого/неагрегованого операндів -> ValidationError
        AC-10 — невідоме поле -> ValidationError «невідоме поле» з підказкою найближчого імені
        AC-11 — ділення -> NULLIF(denominator, 0) -> NULL, не помилка (компонується тут)
        AC-13 — dunder/__import__ -> відмова whitelist AST + запис у td.bi.audit.log
        Повертає скомпільований текст SQL (за замовч.) або dict {'sql', 'is_aggregated', 'fields'}.
        """
        formula, record = self._formula_text(dataset_field_or_measure)
        if not formula or not formula.strip():
            return {'sql': SQL(''), 'is_aggregated': False, 'fields': set()} if as_dict else False
        formula = formula.strip()

        # AC-13: ліміт довжини ДО parse (захист від ресурсної атаки).
        if len(formula) > self._DSL_MAX_LENGTH:
            raise ValidationError(_(
                "Формула задовга (%s символів, максимум %s).", len(formula), self._DSL_MAX_LENGTH,
            ))

        # AC-13: dunder / __import__ — найдешевша і найжорсткіша перевірка ще до parse.
        if '__' in formula:
            self._log_dsl_incident(record, formula, reason='dunder')
            raise ValidationError(_(
                "Формула містить заборонену конструкцію з подвійним підкресленням "
                "(наприклад, '__import__'). Такий синтаксис заборонено."
            ))

        try:
            tree = ast.parse(formula, mode='eval')
        except SyntaxError as exc:
            raise ValidationError(_("Синтаксична помилка у формулі: %s", exc.msg)) from exc

        # AC-13: жорсткий whitelist вузлів AST + ліміти глибини/кількості.
        self._assert_ast_whitelist(tree, record, formula)
        self._assert_ast_limits(tree)

        known_fields = self._known_field_names(record)
        # AC-13: циклічні посилання — формула не може посилатись на власний псевдонім.
        self_alias = getattr(record, 'name', False)
        ctx = {'fields': set(), 'self_alias': self_alias}
        # AC-09/10/11: семантична перевірка + збір SQL-виразу.
        sql_expr, agg_state = self._compile_ast_node(
            tree.body, known_fields=known_fields, record=record, ctx=ctx,
        )
        if as_dict:
            return {'sql': sql_expr, 'is_aggregated': agg_state, 'fields': ctx['fields']}
        # SQL.code зберігаємо як текст (кеш компіляції); реальний bind — у run_query.
        return sql_expr.code if isinstance(sql_expr, SQL) else str(sql_expr)

    # --- DSL: приватні помічники ---
    @api.model
    def _assert_ast_whitelist(self, tree, record, formula):
        """AC-13: обходить усі вузли AST; будь-що поза _ALLOWED_AST_NODES або імʼя з '__'
        -> ValidationError + інцидент в аудит. Атрибутний доступ / lambda / comprehension заборонені.
        """
        for node in ast.walk(tree):
            if not isinstance(node, self._ALLOWED_AST_NODES):
                self._log_dsl_incident(record, formula, reason=type(node).__name__)
                raise ValidationError(_(
                    "Конструкція '%s' заборонена у формулі (дозволені лише агрегати, "
                    "арифметика, порівняння, COALESCE/NULLIF/CASE над полями).",
                    type(node).__name__,
                ))
            # Атрибутний доступ (наприклад obj.__class__) — повністю заборонено.
            if isinstance(node, ast.Attribute):
                self._log_dsl_incident(record, formula, reason='attribute')
                raise ValidationError(_("Атрибутний доступ у формулі заборонено."))
            if isinstance(node, ast.Name) and '__' in node.id:
                self._log_dsl_incident(record, formula, reason='dunder_name')
                raise ValidationError(_(
                    "Імʼя '%s' з подвійним підкресленням заборонено.", node.id,
                ))

    @api.model
    def _assert_ast_limits(self, tree):
        """AC-13: ліміт глибини й кількості вузлів AST (ресурсна безпека)."""
        node_count = 0

        def _walk(node, depth):
            nonlocal node_count
            node_count += 1
            if depth > self._DSL_MAX_DEPTH:
                raise ValidationError(_(
                    "Формула надто глибока (ліміт вкладеності %s).", self._DSL_MAX_DEPTH,
                ))
            if node_count > self._DSL_MAX_NODES:
                raise ValidationError(_(
                    "Формула надто складна (ліміт вузлів %s).", self._DSL_MAX_NODES,
                ))
            for child in ast.iter_child_nodes(node):
                _walk(child, depth + 1)

        _walk(tree, 0)

    @api.model
    def _compile_ast_node(self, node, known_fields, record, ctx):
        """Рекурсивно компілює вузол AST у SQL-вираз і повертає (SQL, is_aggregated).
        AC-09 — кон'юнкція агрег./неагрег. у BinOp -> ValidationError.
        AC-10 — невідоме поле (Name/Subscript) -> ValidationError з підказкою.
        AC-11 — Div -> NULLIF(знаменник, 0), щоб ділення на нуль давало NULL.
        Повертає кортеж (SQL-вираз, прапор «вираз агрегований»).
        """
        # --- Константа: значення — bind-параметр (ніколи не інлайн у текст SQL) ---
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or node.value is None or isinstance(node.value, (int, float, str)):
                return SQL("%s", node.value), False
            raise ValidationError(_("Недозволений тип константи у формулі."))

        # --- Голе імʼя поля -> SQL.identifier (неагрегований операнд) ---
        if isinstance(node, ast.Name):
            return self._resolve_field(node.id, known_fields, record, ctx), False

        # --- [field] DSL-синтаксис посилання на поле у [дужках] ---
        # ВАЖЛИВО (Odoo BI DSL §2.4.2): `[price_subtotal]` парситься Python як ast.List
        # з одного елемента-Name (НЕ Subscript). Це канонічний токен поля DSL.
        if isinstance(node, ast.List):
            if len(node.elts) != 1 or not isinstance(node.elts[0], (ast.Name, ast.Constant)):
                raise ValidationError(_(
                    "Посилання на поле має містити рівно один псевдонім у [дужках]."
                ))
            elt = node.elts[0]
            field_name = elt.id if isinstance(elt, ast.Name) else elt.value
            if not isinstance(field_name, str):
                raise ValidationError(_("Некоректне посилання на поле у формулі."))
            return self._resolve_field(field_name, known_fields, record, ctx), False

        # --- obj[key] -> ідентифікатор поля (альтернативний синтаксис, неагрегований) ---
        if isinstance(node, ast.Subscript):
            field_name = self._subscript_name(node)
            return self._resolve_field(field_name, known_fields, record, ctx), False

        # --- Унарний мінус/плюс/not ---
        if isinstance(node, ast.UnaryOp):
            operand, agg = self._compile_ast_node(node.operand, known_fields, record, ctx)
            if isinstance(node.op, ast.USub):
                return SQL("(-%s)", operand), agg
            if isinstance(node.op, ast.UAdd):
                return SQL("(+%s)", operand), agg
            if isinstance(node.op, ast.Not):
                return SQL("(NOT %s)", operand), agg
            raise ValidationError(_("Недозволений унарний оператор у формулі."))

        # --- Виклик функції (агрегатна / скалярна / CASE) ---
        if isinstance(node, ast.Call):
            return self._compile_call(node, known_fields, record, ctx)

        # --- Бінарна арифметика a +-*% b та ділення (NULLIF) ---
        if isinstance(node, ast.BinOp):
            left, left_agg = self._compile_ast_node(node.left, known_fields, record, ctx)
            right, right_agg = self._compile_ast_node(node.right, known_fields, record, ctx)
            # AC-09: змішування агрегованого і неагрегованого операндів заборонене
            # (дозволено лише агр.-vs-константа, наприклад SUM(x) / 100).
            self._check_mix(node.left, node.right, left_agg, right_agg)
            result_agg = left_agg or right_agg
            if isinstance(node.op, ast.Div):
                # AC-11: ділення на нуль -> NULL через NULLIF(знаменник, 0).
                return SQL("(%s / NULLIF(%s, 0))", left, right), result_agg
            op = self._BINOPS.get(type(node.op))
            if op is None:
                raise ValidationError(_("Оператор у формулі не підтримується."))
            return SQL("(%s %s %s)", left, SQL(op), right), result_agg

        # --- Булева логіка: a AND b / a OR b ---
        if isinstance(node, ast.BoolOp):
            op = self._BOOLOPS.get(type(node.op))
            if not op:
                raise ValidationError(_("Недозволений булевий оператор у формулі."))
            parts, agg = [], False
            for value in node.values:
                part, part_agg = self._compile_ast_node(value, known_fields, record, ctx)
                parts.append(part)
                agg = agg or part_agg
            return SQL("(%s)", SQL(" %s " % op).join(parts)), agg

        # --- Порівняння: a < b (ланцюги a < b < c -> AND) ---
        if isinstance(node, ast.Compare):
            left, left_agg = self._compile_ast_node(node.left, known_fields, record, ctx)
            agg = left_agg
            comparisons, prev = [], left
            for op, comparator in zip(node.ops, node.comparators):
                token = self._CMPOPS.get(type(op))
                if not token:
                    raise ValidationError(_("Недозволений оператор порівняння у формулі."))
                right, right_agg = self._compile_ast_node(comparator, known_fields, record, ctx)
                agg = agg or right_agg
                comparisons.append(SQL("(%s %s %s)", prev, SQL(token), right))
                prev = right
            return SQL("(%s)", SQL(" AND ").join(comparisons)), agg

        # --- IfExp: <true> if <cond> else <false> -> CASE WHEN ... ---
        if isinstance(node, ast.IfExp):
            cond, cond_agg = self._compile_ast_node(node.test, known_fields, record, ctx)
            body, body_agg = self._compile_ast_node(node.body, known_fields, record, ctx)
            orelse, else_agg = self._compile_ast_node(node.orelse, known_fields, record, ctx)
            return (SQL("CASE WHEN %s THEN %s ELSE %s END", cond, body, orelse),
                    (cond_agg or body_agg or else_agg))

        raise ValidationError(_("Невідомий вузол формули: %s", type(node).__name__))

    @api.model
    def _compile_call(self, node, known_fields, record, ctx):
        """Компіляція виклику функції DSL: агрегатна (SUM/...) / скалярна (COALESCE/NULLIF/...) / CASE.
        Ім'я функції — лише ast.Name з білого списку; жодних атрибутів (obj.method) (AC-13)."""
        if not isinstance(node.func, ast.Name):
            self._log_dsl_incident(record, ast.dump(node.func)[:300], reason='call_non_name')
            raise ValidationError(_(
                "Дозволені лише виклики функцій з білого списку (без атрибутів/вкладень)."
            ))
        if node.keywords:
            raise ValidationError(_("Іменовані аргументи у функціях DSL не підтримуються."))
        func_name = node.func.id

        # CASE(cond1, val1, ..., [default]) -> SQL CASE WHEN ... END.
        if func_name == 'CASE':
            return self._compile_case(node, known_fields, record, ctx)

        # Агрегатні функції SUM/AVG/MIN/MAX/COUNT/COUNT_DISTINCT/BOOL_AND/BOOL_OR (AC-08).
        if func_name in self._AGG_FUNCS:
            if len(node.args) != 1:
                raise ValidationError(_("Агрегатна функція приймає рівно один аргумент."))
            inner, inner_agg = self._compile_ast_node(node.args[0], known_fields, record, ctx)
            if inner_agg:
                # AC-09: SUM(SUM(...)) — вкладені агрегати заборонені.
                raise ValidationError(_("Вкладені агрегати у формулі заборонено."))
            if func_name == 'COUNT_DISTINCT':
                return SQL("COUNT(DISTINCT %s)", inner), True
            return SQL("%s(%s)", SQL(func_name), inner), True

        # Скалярні функції COALESCE/NULLIF/ABS/ROUND/GREATEST/LEAST.
        if func_name in self._SCALAR_FUNCS:
            arg_sqls, any_agg = [], False
            for arg in node.args:
                arg_sql, arg_agg = self._compile_ast_node(arg, known_fields, record, ctx)
                arg_sqls.append(arg_sql)
                any_agg = any_agg or arg_agg
            return SQL("%s(%s)", SQL(self._SCALAR_FUNCS[func_name]), SQL(", ").join(arg_sqls)), any_agg

        # Невідома/заборонена функція -> відмова whitelist (AC-13) з підказкою.
        known = sorted(self._AGG_FUNCS) + sorted(self._SCALAR_FUNCS) + ['CASE']
        suggestion = difflib.get_close_matches(func_name, known, n=1)
        hint = _(" Можливо: «%s»?", suggestion[0]) if suggestion else ""
        self._log_dsl_incident(record, func_name, reason='unknown_func')
        raise ValidationError(_(
            "Функція '%s' не дозволена у формулі.%s", func_name, hint,
        ))

    @api.model
    def _compile_case(self, node, known_fields, record, ctx):
        """CASE(cond1, val1, ..., [default]) -> SQL CASE WHEN ... END."""
        args = node.args
        if len(args) < 2:
            raise ValidationError(_("CASE потребує щонайменше пару умова/значення."))
        has_default = (len(args) % 2 == 1)
        pair_count = (len(args) - 1) if has_default else len(args)
        whens, agg = [], False
        for i in range(0, pair_count, 2):
            cond, cond_agg = self._compile_ast_node(args[i], known_fields, record, ctx)
            val, val_agg = self._compile_ast_node(args[i + 1], known_fields, record, ctx)
            agg = agg or cond_agg or val_agg
            whens.append(SQL("WHEN %s THEN %s", cond, val))
        body = SQL(" ").join(whens)
        if has_default:
            default, default_agg = self._compile_ast_node(args[-1], known_fields, record, ctx)
            agg = agg or default_agg
            return SQL("CASE %s ELSE %s END", body, default), agg
        return SQL("CASE %s END", body), agg

    @api.model
    def _check_mix(self, left_node, right_node, left_agg, right_agg):
        """AC-09 — заборона змішування агрегованого і неагрегованого операндів.
        Допускається лише агр.-vs-константа (SUM(x) / 100); агр.-vs-поле — ні
        (SUM([price_subtotal]) / [qty])."""
        if left_agg == right_agg:
            return
        non_agg_node = right_node if left_agg else left_node
        if isinstance(non_agg_node, ast.Constant):
            return
        if isinstance(non_agg_node, ast.UnaryOp) and isinstance(non_agg_node.operand, ast.Constant):
            return
        raise ValidationError(_(
            "Змішування агрегованого і неагрегованого операндів у формулі заборонено "
            "(наприклад, SUM([price_subtotal]) / [qty]). Загорніть неагрегований операнд "
            "у агрегатну функцію."
        ))

    @api.model
    def _resolve_field(self, name, known_fields, record, ctx):
        """AC-10: перевіряє, що поле існує; інакше ValidationError з підказкою найближчого імені.
        AC-13: циклічне посилання на власний псевдонім -> ValidationError.
        Колонка матеріалізується лише через SQL.identifier (анти-інʼєкція).
        """
        if '__' in name:  # додатковий бар'єр (AC-13)
            raise ValidationError(_("Імʼя '%s' з подвійним підкресленням заборонено.", name))
        # AC-13: циклічне посилання формули на власний псевдонім.
        if ctx.get('self_alias') and name == ctx['self_alias']:
            raise ValidationError(_(
                "Циклічне посилання: формула не може посилатись на власне поле «%s».", name,
            ))
        if name not in known_fields:
            suggestion = difflib.get_close_matches(name, list(known_fields), n=1, cutoff=0.4)
            hint = _(" Можливо, ви мали на увазі «%s»?", suggestion[0]) if suggestion else ""
            raise ValidationError(_("Невідоме поле «%s» у формулі.%s", name, hint))
        ctx['fields'].add(name)
        return SQL.identifier(name)

    @api.model
    def _subscript_name(self, node):
        """Дістає імʼя поля з вузла Subscript [field] (Index сумісність py3.8 / py3.9+)."""
        sl = node.slice
        # py3.9+: slice — це безпосередньо вузол; py3.8: ast.Index(value=...).
        if sl.__class__.__name__ == 'Index':  # pragma: no cover — стара версія Python
            sl = sl.value
        if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
            return sl.value
        if isinstance(sl, ast.Name):
            return sl.id
        raise ValidationError(_("Некоректне посилання на поле у формулі."))

    @api.model
    def _known_field_names(self, record):
        """Множина допустимих імен полів для формули: псевдоніми полів датасету.
        AC-10 — джерело істини для перевірки «невідоме поле» + підказки.
        """
        dataset = getattr(record, 'dataset_id', False)
        if not dataset:
            return set()
        # Не дозволяємо посилатись на інші формули-колонки напряму у SQL-агрегаті.
        plain = dataset.field_ids.filtered(lambda f: not f.is_formula)
        return set(plain.mapped('name')) | set(plain.filtered('path').mapped('path'))

    @api.model
    def _formula_text(self, dataset_field_or_measure):
        """Повертає (текст формули, запис) для поля датасету або міри."""
        record = dataset_field_or_measure
        # td.bi.dataset.field -> formula; td.bi.measure -> expression.
        formula = getattr(record, 'formula', False) or getattr(record, 'expression', False)
        return formula, record

    @api.model
    def _log_dsl_incident(self, record, formula, reason):
        """AC-13: записує інцидент DSL у td.bi.audit.log (event_type='sql_run' — найближчий тип).
        Запис системою; не блокує (best-effort), сама помилка кидається у виклику.
        """
        try:
            dataset = getattr(record, 'dataset_id', False)
            self.env['td.bi.audit.log'].sudo().create({
                'event_type': 'sql_run',
                'dataset_id': dataset.id if dataset else False,
                'user_id': self.env.uid,
                'payload': {
                    'kind': 'dsl_rejected',
                    'reason': reason,
                    'formula': (formula or '')[:2000],
                    'model': record._name if record else False,
                },
            })
        except Exception:  # pragma: no cover — аудит не повинен ламати валідацію
            _logger.warning("BI DSL rejected (%s) but audit.log write failed", reason)

    # =========================================================================
    # === Доменна безпека: Domain.AND рівнів (AC-14, AC-17, AC-64) ============
    # =========================================================================
    @api.model
    def _build_effective_domain(self, levels):
        """Доменна безпека: ефективний домен рівнів виключно через Domain.AND;
        парс текстових доменів ast.literal_eval; білий список динамічних дат -> інакше
        ValidationError; без конкатенації списків.
        AC-64 — Domain.AND рівнів; OR-префікс ізольований у своєму рівні (нейтралізація атаки).
        AC-14 — домен спуску (__extra_domain) приходить готовим рівнем і додається через AND.
        AC-17 — межі дат у tz користувача вже включені у відповідний рівень (str/list).
        """
        domains = []
        for level in levels:
            if level in (None, False, '', '[]'):
                continue
            parsed = self._parse_domain_level(level)
            if parsed is None:
                continue
            domains.append(parsed)
        if not domains:
            return Domain.TRUE
        # AC-64: КОН'ЮНКЦІЯ виключно через Domain.AND — кожен рівень ізольований у власному
        # Domain, тож шкідливий OR-префікс (['|', ...]) не розширює сумарну вибірку.
        return Domain.AND(domains)

    @api.model
    def _parse_domain_level(self, level):
        """Парсить один рівень домену у Domain. Текст -> ast.literal_eval (не eval),
        список -> Domain(list). Кожен рівень загортається у власний Domain (ізоляція OR).
        AC-64 — динамічні дати приймаються лише за білим списком синтаксису ORM.
        """
        if isinstance(level, Domain):
            return level
        if isinstance(level, str):
            text = level.strip()
            if not text:
                return None
            try:
                parsed = ast.literal_eval(text)
            except (ValueError, SyntaxError) as exc:
                raise ValidationError(_("Некоректний домен: %s", level)) from exc
        elif isinstance(level, (list, tuple)):
            parsed = list(level)
        else:
            raise ValidationError(_("Непідтримуваний тип рівня домену: %r", level))
        if not parsed:
            return None
        if not isinstance(parsed, (list, tuple)):
            raise ValidationError(_("Домен має бути списком, отримано: %r", parsed))
        # AC-64: динамічні дати — лише за білим списком синтаксису ORM.
        self._validate_domain_dynamic_dates(parsed)
        return Domain(list(parsed))

    @api.model
    def _validate_domain_dynamic_dates(self, domain_list):
        """Білий список синтаксису динамічних дат у значеннях умов домену (AC-64).
        Дозволено: ORM-якорі ('today', 'this_month', ...) і відносні зсуви (-30d/+2w/1m/3y).
        Підозрілий шаблон (eval/datetime/context_today/__) -> ValidationError."""
        for leaf in domain_list:
            if isinstance(leaf, (list, tuple)) and len(leaf) == 3:
                value = leaf[2]
                if isinstance(value, str):
                    self._check_dynamic_date_token(value)

    @api.model
    def _check_dynamic_date_token(self, token):
        """Перевірка одного рядкового значення домену проти білого списку дин.-дат (AC-64)."""
        raw = token.strip()
        if not raw:
            return
        if raw.lower() in self._DOMAIN_DATE_ANCHORS:
            return
        # Відносний зсув: опц. знак + цифри + одиниця (d/w/m/q/y).
        body = raw[1:] if raw[:1] in ('+', '-') else raw
        if body and body[:-1].isdigit() and body[-1:].lower() in ('d', 'w', 'm', 'q', 'y'):
            return
        # Не схоже на дата-вираз — звичайне значення-рядок, пропускаємо.
        # Підозрілий шаблон (eval/datetime/context_today/relativedelta/__) -> заборонено.
        lowered = raw.lower()
        for forbidden in ('eval', 'datetime', 'context_today', 'relativedelta', '__'):
            if forbidden in lowered:
                raise ValidationError(_(
                    "Динамічна дата поза білим списком синтаксису ORM: «%s».", token,
                ))

    @api.model
    def _domain_as_list(self, domain):
        """Нормалізує Domain/список у канонічний список (для кеш-ключа й діагностики)."""
        if isinstance(domain, Domain):
            return list(domain)
        return list(domain or [])

    # =========================================================================
    # === RLS-підзапит: record rules у WHERE (AC-39, AC-62) ===================
    # =========================================================================
    @api.model
    def _inject_record_rules(self, model, domain):
        """Повертає SQL-підзапит набору id, доступних поточному користувачу, із вбудованими
        record rules. Основний шлях — Model._search(domain) (Query, приватний API); запасний —
        model.search(domain).ids (публічний). RLS діє в кожному CTE бленда і не обходиться. Без sudo().
        AC-39 — RLS у кожному CTE; AC-62 — RLS через вимір-ключ правила у накритому запиті.
        """
        eff = self._build_effective_domain([domain]) if domain is not None else Domain.TRUE
        dom_list = self._domain_as_list(eff)
        # DEVIATION(Odoo19): підтвердити, що Model._search(domain) повертає Query з вбудованими
        # record rules (формально приватний API) як SQL-підзапит для WHERE CTE на збірці 19.0.
        # Запасний шлях — публічний search(domain).ids.
        try:
            # Основний (приватний) шлях — Query з record rules у WHERE як підзапит.
            return model._search(dom_list)
        except Exception:  # pragma: no cover — звірити сигнатуру/виняток на збірці 19.0
            _logger.info("BI: Model._search недоступний — fallback на search().ids для %s", model._name)
            # Запасний шлях: публічний search -> лише дозволені id.
            return model.search(dom_list).ids
