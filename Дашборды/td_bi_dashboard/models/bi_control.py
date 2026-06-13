# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
from odoo import api, fields, models, _


class TdBiControl(models.Model):
    _name = 'td.bi.control'
    _description = 'BI: Контрол'
    _order = 'sequence, id'
    # Since: 19.0.1.0.0

    # === Fields ===
    dashboard_id = fields.Many2one('td.bi.dashboard', string="Дашборд")  # scope=dashboard
    page_id = fields.Many2one('td.bi.dashboard.page', string="Сторінка")  # scope=page
    group_key = fields.Char(string="Ключ групи")  # scope=group
    control_type = fields.Selection(
        selection=[
            ('date_range', 'Діапазон дат'),
            ('dropdown', 'Випадний список'),
            ('fixed_list', 'Фіксований список'),
            ('text_search', 'Текстовий пошук'),
            ('numeric_range', 'Числовий діапазон'),
            ('checkbox', 'Чекбокс'),
            ('hierarchical', 'Ієрархічний вибір'),
            ('parameter', 'Контрол параметра'),
            ('preset_buttons', 'Пресет-кнопки'),
            ('navigation', 'Кнопка-навігація'),
        ],
        string="Тип контролу",
    )  # коди потребують уточнення (SPEC рядок 954)
    label = fields.Char(string="Підпис", translate=True)
    sequence = fields.Integer(string="Послідовність")
    mapping_ids = fields.One2many(
        'td.bi.control.mapping', 'control_id', string="Сопоставлення полів",
    )  # AC-57
    default_value = fields.Json(string="Значення за замовчуванням")
    is_locked = fields.Boolean(string="Заблоковано")  # глядач бачить, не змінює (ВИМ-25)
    is_hidden = fields.Boolean(string="Прихований")
    cascade = fields.Boolean(string="Каскад", default=True)  # AC-58
    layout = fields.Json(string="Розташування")

    # === Constraints ===
    # SPEC: SQL constraints — None.

    # === Create ===
    @api.model_create_multi
    def create(self, vals_list):
        """Створення контролу(ів).  # TODO: AC-57 — автосопоставлення mapping_ids per-датасет."""
        # TODO: AC-57 — створити по одному td.bi.control.mapping на датасет; автосопоставлення
        #               field_path за збігом техімʼя/типу; enabled=True за замовчуванням.
        return super().create(vals_list)

    # === Compute ===
    # SPEC: Computed fields — None.

    # === Actions ===
    # SPEC: Key methods — None.
    # TODO: AC-15 — drill фільтрує інші віджети сторінки (cross-filter, чип у панелі).
    # TODO: AC-58 — ієрархічний контроль через child_of; каскадний перерахунок залежного контролю.
