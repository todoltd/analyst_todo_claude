# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
from odoo import api, fields, models, _


class BiDatasetJoinKey(models.Model):
    _name = 'td.bi.dataset.join.key'
    _description = 'BI Ключ зʼєднання'
    _order = 'id'

    # === Fields ===
    join_id = fields.Many2one(
        'td.bi.dataset.join', string="Таблиця бленда",
        required=True, ondelete='cascade',
    )
    left_field = fields.Char(string="Поле зліва")
    right_field = fields.Char(string="Поле справа")

    # === SQL constraints ===
    # SPEC: SQL-constraints для td.bi.dataset.join.key не задано.
    # Умови зʼєднання — лише рівність пар полів left_field = right_field.
    # TODO: AC-38 — пари ключів формують умову JOIN (left/inner)
    # TODO: AC-41 — унікальний ключ у вимірах для коректної предагрегації

    # === Compute === None
    # === Actions === None
