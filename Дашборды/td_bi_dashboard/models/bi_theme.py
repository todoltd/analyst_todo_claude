# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
from odoo import api, fields, models, _


class TdBiTheme(models.Model):
    _name = 'td.bi.theme'
    _description = 'BI: Тема оформлення'
    # Since: 19.0.1.0.0

    # === Fields ===
    name = fields.Char(string="Назва", translate=True)
    config = fields.Json(string="Конфігурація теми")  # палітра, шрифти, дефолти per widget_type
    is_default = fields.Boolean(string="За замовчуванням")
    company_id = fields.Many2one('res.company', string="Компанія")  # корпоративна тема
    logo = fields.Image(string="Логотип")  # для експорту / публічного вигляду

    # === Constraints ===
    # SPEC: SQL constraints — None.

    # === Compute ===
    # SPEC: Computed fields — None.

    # === Actions ===
    # SPEC: Key methods — None.
