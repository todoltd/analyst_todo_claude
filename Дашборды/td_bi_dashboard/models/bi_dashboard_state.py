# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
from odoo import api, fields, models, _


class TdBiDashboardState(models.Model):
    _name = 'td.bi.dashboard.state'
    _description = 'BI: Закладка / збережений стан дашборда'
    _order = 'sequence, id'
    # Since: 19.0.1.0.0

    # === Fields ===
    dashboard_id = fields.Many2one(
        'td.bi.dashboard', string="Дашборд", required=True, ondelete='cascade',
    )
    user_id = fields.Many2one(
        'res.users', string="Користувач", default=lambda self: self.env.user,
    )  # порожній = авторська спільна закладка
    name = fields.Char(string="Назва")
    kind = fields.Selection(
        [
            ('bookmark', 'Закладка'),
            ('autosave', 'Автозбереження'),
            ('personal_default', 'Стан за замовчуванням'),
        ],
        string="Вид",
    )
    payload = fields.Json(string="Дані стану")  # контроли, cross-фільтри, drill-стек, сторінка
    apply_scope = fields.Selection(
        [('data', 'Фільтри'), ('display', 'Видимість'), ('all', 'Усе')],
        string="Область застосування",
    )
    sequence = fields.Integer(string="Послідовність")

    # === Constraints ===
    # SPEC: SQL constraints — None.
    # TODO: AC-16 — drill-стек (рівні + хлібні крихти) серіалізується у payload і
    #               відновлюється при відкритті за особистою закладкою (kind='bookmark').
    # TODO: AC-30 — миттєве відкликання/деактивація (узгодженість стану публічного знімка).

    # === Compute ===
    # SPEC: Computed fields — None.

    # === Actions ===
    # SPEC: Key methods — None.
