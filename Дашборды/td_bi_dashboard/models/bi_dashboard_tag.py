# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
from odoo import api, fields, models, _


class TdBiDashboardTag(models.Model):
    _name = 'td.bi.dashboard.tag'
    _description = 'BI: Тег каталогу дашбордів'
    # Since: 19.0.1.0.0

    # === Fields ===
    name = fields.Char(string="Назва")
    color = fields.Integer(string="Колір")  # індекс палітри Odoo (штатний патерн тегів)

    # === Constraints ===
    # SPEC: SQL constraints — None.

    # === Compute ===
    # SPEC: Computed fields — None.

    # === Actions ===
    # SPEC: Key methods — None.
