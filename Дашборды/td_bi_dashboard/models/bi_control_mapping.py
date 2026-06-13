# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
from odoo import api, fields, models, _


class TdBiControlMapping(models.Model):
    _name = 'td.bi.control.mapping'
    _description = 'BI: Сопоставлення поля контролу'
    _order = 'id'
    # Since: 19.0.1.0.0

    # === Fields ===
    control_id = fields.Many2one(
        'td.bi.control', string="Контрол", required=True, ondelete='cascade',
    )
    dataset_id = fields.Many2one('td.bi.dataset', string="Датасет")  # датасет дії мапінгу
    field_path = fields.Char(string="Шлях поля")  # порожній -> датасет пропускається (AC-57)
    enabled = fields.Boolean(string="Увімкнено")  # виключення датасету («не діє»); AC-57

    # === Constraints ===
    # SPEC: SQL constraints — None.

    # === Compute ===
    # SPEC: Computed fields — None.

    # === Actions ===
    # SPEC: Key methods — None.
