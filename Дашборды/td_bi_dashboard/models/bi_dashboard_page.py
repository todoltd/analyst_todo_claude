# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
from odoo import api, fields, models, _


class TdBiDashboardPage(models.Model):
    _name = 'td.bi.dashboard.page'
    _description = 'BI: Сторінка дашборда'
    _order = 'sequence, id'
    # Since: 19.0.1.0.0

    # === Fields ===
    dashboard_id = fields.Many2one(
        'td.bi.dashboard', string="Дашборд", required=True, ondelete='cascade',
    )
    name = fields.Char(string="Назва", translate=True)
    sequence = fields.Integer(string="Послідовність")
    is_hidden = fields.Boolean(string="Прихована")
    is_drillthrough = fields.Boolean(string="Сторінка деталізації")  # drill-through (§2.2.4)
    drillthrough_field_ids = fields.Json(string="Поля drill-through")
    grid_rows_min = fields.Integer(string="Мін. рядків сітки")
    control_ids = fields.One2many(
        'td.bi.control', 'page_id', string="Контроли сторінки",
    )  # scope=page

    # === Constraints ===
    # SPEC: SQL constraints — None.

    # === Compute ===
    # SPEC: Computed fields — None.

    # === Actions ===
    # SPEC: Key methods — None.
