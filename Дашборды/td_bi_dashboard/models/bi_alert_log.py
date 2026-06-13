# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
from odoo import api, fields, models, _


class TdBiAlertLog(models.Model):
    _name = 'td.bi.alert.log'
    _description = 'BI: Журнал алертів'
    _order = 'create_date desc, id desc'
    # Журнал пише система (cron); без W/C/D для користувачів (ACL).

    # === Fields ===
    alert_id = fields.Many2one(
        'td.bi.alert', string="Алерт", required=True, ondelete='cascade',
    )  # create_date — авто-поле ORM (момент спрацювання)
    value = fields.Float(string="Зафіксоване значення")
    delivery = fields.Text(string="Результат доставки")

    # === Constraints ===
    # SPEC: SQL constraints — None.

    # === Compute ===
    # SPEC: Computed fields — None.

    # === Actions ===
    # SPEC: Key methods — None (запис системою у _cron_check_alerts, AC-35).
