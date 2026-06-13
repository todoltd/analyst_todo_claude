# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
from odoo import api, fields, models, _


class TdBiDashboardGroup(models.Model):
    _name = 'td.bi.dashboard.group'
    _description = 'BI: Розділ каталогу дашбордів'
    _order = 'sequence, id'
    # Since: 19.0.1.0.0

    # === Fields ===
    name = fields.Char(string="Назва розділу")
    sequence = fields.Integer(string="Послідовність")

    # === Constraints ===
    # SPEC: SQL constraints — None.

    # === Compute ===
    # SPEC: Computed fields — None.

    # === Actions ===
    # SPEC: Key methods — None.
