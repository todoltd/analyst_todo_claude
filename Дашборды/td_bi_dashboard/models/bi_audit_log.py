# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
from odoo import api, fields, models, _


class TdBiAuditLog(models.Model):
    _name = 'td.bi.audit.log'
    _description = 'BI: Журнал аудиту'
    _order = 'create_date desc, id desc'
    # Записує система у точках подій; лише читання для group_bi_admin (ACL; етап 2, ВИМ-40).

    # === Fields ===
    event_type = fields.Selection(
        [
            ('view', 'Перегляд'),
            ('export', 'Експорт'),
            ('share_create', 'Створення посилання'),
            ('share_revoke', 'Відкликання посилання'),
            ('access_change', 'Зміна доступу'),
            ('sql_run', 'Виконання SQL'),
        ],
        string="Тип події", required=True,
    )
    dashboard_id = fields.Many2one('td.bi.dashboard', string="Дашборд")
    dataset_id = fields.Many2one('td.bi.dataset', string="Датасет")
    user_id = fields.Many2one('res.users', string="Користувач", required=True)
    payload = fields.Json(string="Деталі події")
    # create_date — авто-поле ORM (коли)

    # === Constraints ===
    # SPEC: SQL constraints — None.

    # === Compute ===
    # SPEC: Computed fields — None.

    # === Actions ===
    # SPEC: Key methods — None.
