# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    # Розділ Configuration SPEC. Значення зберігаються в ir.config_parameter (config_parameter=...)
    # -> читаються движком запитів (td.bi.query.compiler) і клієнтом (biDataService).

    # === Fields === (імена узгоджені з res_config_settings_views.xml; дефолти зі SPEC §Configuration)
    td_bi_statement_timeout = fields.Integer(
        string="statement_timeout BI-запиту (с)", default=30,
        config_parameter='td_bi_dashboard.statement_timeout',
    )  # ставиться на курсор перед виконанням; таймаут -> UserError (AC-49)
    td_bi_max_concurrent_rpc = fields.Integer(
        string="Макс. паралельних data-RPC", default=6,
        config_parameter='td_bi_dashboard.max_concurrent_rpc',
    )  # черга biDataService (AC-46)
    td_bi_control_debounce_ms = fields.Integer(
        string="Дебаунс контролів (мс)", default=400,
        config_parameter='td_bi_dashboard.control_debounce_ms',
    )  # AC-46
    td_bi_max_response_mb = fields.Integer(
        string="Ліміт відповіді (МБ JSON)", default=5,
        config_parameter='td_bi_dashboard.max_response_mb',
    )
    td_bi_max_groups = fields.Integer(
        string="Ліміт груп за замовч.", default=50,
        config_parameter='td_bi_dashboard.max_groups',
    )
    td_bi_max_time_points = fields.Integer(
        string="Ліміт точок часу", default=366,
        config_parameter='td_bi_dashboard.max_time_points',
    )
    td_bi_max_table_rows = fields.Integer(
        string="Ліміт рядків таблиці", default=80,
        config_parameter='td_bi_dashboard.max_table_rows',
    )  # AC-06 (preview ≤80)
    td_bi_field_tree_max_depth = fields.Integer(
        string="Макс. глибина дерева полів", default=5,
        config_parameter='td_bi_dashboard.field_tree_max_depth',
    )  # AC-04
    td_bi_csp_frame_ancestors = fields.Char(
        string="CSP frame-ancestors (embed)",
        config_parameter='td_bi_dashboard.csp_frame_ancestors',
    )  # Content-Security-Policy: frame-ancestors для /bi/embed

    # === Constraints / Compute / Actions ===
    # SPEC: окремих constraints/compute/actions для налаштувань не визначено.
