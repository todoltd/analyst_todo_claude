# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import SQL  # Odoo 19: безпечний конструктор SQL (SQL.identifier для імен об'єктів)

_logger = logging.getLogger(__name__)


class TdBiMaterialization(models.Model):
    _name = 'td.bi.materialization'
    _description = 'BI: Матеріалізація (предагрегат)'
    # Stage-1: звичайна таблиця-конфіг (ORM auto). Фізичний предагрегат (table_name) керується окремо.
    # DEVIATION(Odoo19) Stage-2: _auto=False + init()/REFRESH MATERIALIZED VIEW CONCURRENTLY (підтвердити життєвий цикл).
    # Примітка: фізична таблиця / MATERIALIZED VIEW створюється в init() через odoo.tools.SQL
    # (за зразком sale.report); потребує звірки з Odoo 19 (життєвий цикл _table_query/init() v19).
    # Лише читання для group_bi_user; CUD — group_bi_admin (ACL).

    # === Fields ===
    dataset_id = fields.Many2one(
        'td.bi.dataset', string="Датасет", required=True, ondelete='cascade',
    )
    dimension_paths = fields.Json(string="Фіксовані виміри")
    measure_specs = fields.Json(string="Фіксовані міри")
    granularity = fields.Char(string="Гранулярність дати")
    table_name = fields.Char(string="Ім'я таблиці / MV")
    refresh_cron_id = fields.Many2one('ir.cron', string="Cron оновлення")
    last_refresh = fields.Datetime(string="Останнє оновлення")

    # === Computed fields ===
    is_rls_safe = fields.Boolean(
        string="RLS-безпечна", compute='_compute_is_rls_safe', store=True,
    )

    @api.depends('dataset_id', 'dimension_paths')  # + домени record rules датасету
    def _compute_is_rls_safe(self):
        """True лише якщо RLS-варіативність відсутня або компенсована виміром-ключем правила
        (напр. предагрегат включає team_id). Конструктор відмовляє у небезпечних конфігураціях.
        AC-63 — is_rls_safe=False -> create перериває UserError, MV не створюється.

        Логіка: знаходимо поля record rules на кореневій моделі датасету (поля, до яких
        прив'язані домени ir.rule), і вважаємо предагрегат RLS-безпечним лише якщо КОЖНЕ
        таке поле-ключ присутнє серед dimension_paths (інакше предагрегат став би каналом
        витоку повз record rules).
        """
        for record in self:
            record.is_rls_safe = record._evaluate_rls_safety()

    def _evaluate_rls_safety(self):
        """AC-63 — повертає True, якщо всі вимір-ключі record rules датасету присутні
        у dimension_paths (RLS-варіативність компенсована); інакше False.
        Без правил, що звужують вибірку, — RLS-варіативності немає -> безпечно.
        """
        self.ensure_one()
        dataset = self.dataset_id
        if not dataset or not dataset.model_name:
            return False
        rule_fields = self._rule_key_fields(dataset.model_name)
        if not rule_fields:
            # Немає звужувальних record rules -> RLS-варіативності немає -> безпечно.
            return True
        dims = set(self._dimension_field_names())
        # Безпечно лише якщо КОЖЕН ключ правила накритий виміром предагрегата.
        return rule_fields.issubset(dims)

    def _rule_key_fields(self, model_name):
        """Множина імен полів кореневої моделі, до яких прив'язані домени ir.rule
        (вимір-ключі правил). Best-effort парс ir.rule.domain_force на кортежі.
        """
        keys = set()
        rules = self.env['ir.rule'].sudo().search([
            ('model_id.model', '=', model_name),
            ('active', '=', True),
            ('perm_read', '=', True),
        ])
        model_fields = set(self.env[model_name]._fields)
        for rule in rules:
            domain_force = rule.domain_force or ''
            for fname in model_fields:
                # Наявність "'field'" або "(\"field\"" у тексті домену — ознака ключа правила.
                if ("'%s'" % fname) in domain_force or ('"%s"' % fname) in domain_force:
                    keys.add(fname)
        return keys

    def _dimension_field_names(self):
        """Імена полів-вимірів предагрегата з dimension_paths (перший сегмент кожного шляху
        — поле кореневої моделі, до якого може бути прив'язане правило)."""
        self.ensure_one()
        return self._dimension_names_from_paths(self.dimension_paths)

    # === ORM overrides ===
    @api.model_create_multi
    def create(self, vals_list):
        """AC-63 — конструктор відмовляє у матеріалізації для RLS-небезпечної конфігурації.
        RLS-безпека обчислюється з vals ДО будь-якого створення запису/подання: якщо
        небезпечно -> UserError (дослівний текст SPEC) і жодного запису/MV не створено
        (стан БД незмінний). Лише безпечні конфігурації доходять до super().create().
        """
        for vals in vals_list:
            if not self._vals_are_rls_safe(vals):
                raise UserError(_(
                    "Неможливо створити матеріалізацію: датасет має RLS-варіативність, "
                    "не компенсовану виміром-ключем правила. Предагрегат став би каналом "
                    "витоку повз record rules."
                ))
        return super().create(vals_list)

    @api.model
    def _vals_are_rls_safe(self, vals):
        """AC-63 — оцінка RLS-безпеки з сирих vals (без створеного запису).
        Безпечно лише якщо КОЖЕН вимір-ключ record rules датасету присутній у dimension_paths;
        без звужувальних правил — RLS-варіативності немає -> безпечно.
        """
        dataset = self.env['td.bi.dataset'].browse(vals.get('dataset_id'))
        if not dataset or not dataset.model_name:
            return False
        rule_fields = self._rule_key_fields(dataset.model_name)
        if not rule_fields:
            return True
        dims = self._dimension_names_from_paths(vals.get('dimension_paths'))
        return rule_fields.issubset(dims)

    @api.model
    def _dimension_names_from_paths(self, paths):
        """Імена полів-вимірів (перший сегмент кожного шляху) з сирого dimension_paths."""
        if isinstance(paths, dict):
            paths = list(paths.values())
        names = set()
        for p in (paths or []):
            if isinstance(p, str) and p:
                names.add(p.split('.', 1)[0].split(':', 1)[0])
        return names

    # === Constraints ===
    # SPEC: SQL constraints — None.

    # === Actions ===
    def init(self):
        """Створення фізичної таблиці/MV через odoo.tools.SQL (патерн _auto=False).
        AC-62 — побудова MATERIALIZED VIEW предагрегата.
        Stage-1: структурно коректна заглушка — реальний DDL предагрегата (Stage-3).
        """
        # DEVIATION(Odoo19): підтвердити життєвий цикл _auto=False + init()/_table_query на
        # збірці 19.0 та підтримку REFRESH MATERIALIZED VIEW CONCURRENTLY (CONCURRENTLY вимагає
        # UNIQUE-індексу на MV). Основний шлях — odoo.tools.SQL у init(); запасний — без CONCURRENTLY.
        super().init()
        # TODO: AC-62 (Stage-3) — побудувати CREATE MATERIALIZED VIEW <table_name> AS <предагрегат>
        # через SQL("CREATE MATERIALIZED VIEW %s AS ...", SQL.identifier(self.table_name)).

    def action_refresh(self):
        """Будує/перебудовує фізичний предагрегат (звичайна ТАБЛИЦЯ через CREATE TABLE AS —
        портативно, без невизначеного на 19.0 лайфциклу MATERIALIZED VIEW/CONCURRENTLY) і
        оновлює last_refresh. Повний агрегат за доменом датасету (sudo: RLS реапплікується на
        стороні обслуговування лише у безпечному no-rules-кейсі, AC-62/63)."""
        for record in self.filtered('table_name'):
            try:
                record._build_preagg_table()
                record.last_refresh = fields.Datetime.now()
            except Exception:  # pragma: no cover — збій побудови не валить cron/інші
                _logger.exception("BI: побудова предагрегата #%s не вдалась", record.id)
        return True

    def _mat_dim_list(self):
        """Упорядкований список полів-вимірів предагрегата (базові, без гранулярності)."""
        self.ensure_one()
        paths = self.dimension_paths
        if isinstance(paths, dict):
            paths = list(paths.values())
        return [p.split(':', 1)[0] for p in (paths or []) if isinstance(p, str) and p]

    def _mat_measure_list(self):
        """Упорядкований список мір предагрегата: [{name, path, agg}]. measure_specs — список
        dict {name?, path, agg} (name за замовч. '<path>:<agg>' = value_key live-запиту)."""
        self.ensure_one()
        specs = self.measure_specs
        if isinstance(specs, dict):
            specs = list(specs.values())
        out = []
        for s in (specs or []):
            if isinstance(s, dict) and s.get('path'):
                agg = s.get('agg') or 'sum'
                out.append({'name': s.get('name') or ('%s:%s' % (s['path'], agg)),
                            'path': s['path'], 'agg': agg})
        return out

    def _mat_agg_sql(self, agg, path):
        col = SQL.identifier(path)
        a = (agg or 'sum').lower()
        if a == 'count':
            return SQL("COUNT(%s)", col)
        if a == 'count_distinct':
            return SQL("COUNT(DISTINCT %s)", col)
        token = {'sum': 'SUM', 'avg': 'AVG', 'min': 'MIN', 'max': 'MAX'}.get(a, 'SUM')
        return SQL("%s(%s)", SQL(token), col)

    def _build_preagg_table(self):
        """CREATE TABLE <table_name> AS <предагрегований SELECT> за доменом датасету (sudo)."""
        self.ensure_one()
        dataset = self.dataset_id
        if not dataset or not dataset.model_name or not self.table_name:
            return False
        dims = self._mat_dim_list()
        measures = self._mat_measure_list()
        if not dims and not measures:
            return False
        model = self.env[dataset.model_name].sudo()
        select_parts, group_parts = [], []
        for i, path in enumerate(dims):
            select_parts.append(SQL("%s AS %s", SQL.identifier(path), SQL.identifier('dim_%d' % i)))
            group_parts.append(SQL.identifier(path))
        for j, m in enumerate(measures):
            select_parts.append(SQL(
                "%s AS %s", self._mat_agg_sql(m['agg'], m['path']), SQL.identifier('meas_%d' % j)))
        import ast
        try:
            domain = ast.literal_eval(dataset.domain) if dataset.domain else []
        except (ValueError, SyntaxError):
            domain = []
        sub = model._search(domain).subselect()  # повний агрегат за доменом (sudo -> без RLS)
        table = SQL.identifier(self.table_name)
        group_sql = SQL(" GROUP BY %s", SQL(", ").join(group_parts)) if group_parts else SQL("")
        self.env.cr.execute(SQL("DROP TABLE IF EXISTS %s", table))
        self.env.cr.execute(SQL(
            "CREATE TABLE %s AS SELECT %s FROM %s AS s WHERE s.id IN %s%s",
            table, SQL(", ").join(select_parts), SQL.identifier(model._table), sub, group_sql))
        return True

    @api.model
    def _cron_refresh(self):
        """Плановий REFRESH MATERIALIZED VIEW CONCURRENTLY за розкладом refresh_cron_id.
        AC-62 — перший REFRESH — за розкладом крона (не post_init_hook).
        """
        # Обхід усіх матеріалізацій -> action_refresh() кожної (best-effort, збій однієї
        # не блокує інших — деградація без падіння cron).
        for record in self.search([]):
            try:
                record.action_refresh()
            except Exception:  # pragma: no cover — збій REFRESH не валить cron
                _logger.exception("BI: REFRESH матеріалізації #%s не вдався", record.id)
        return True
