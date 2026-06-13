# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
from odoo import api, fields, models, _


class TdBiWidget(models.Model):
    _name = 'td.bi.widget'
    _description = 'BI: Віджет'
    _order = 'sequence, id'
    # Since: 19.0.1.0.0

    # === Fields ===
    page_id = fields.Many2one(
        'td.bi.dashboard.page', string="Сторінка", required=True, ondelete='cascade',
    )
    dataset_id = fields.Many2one('td.bi.dataset', string="Датасет", required=True)
    widget_type = fields.Selection(
        selection=[
            # MVP
            ('kpi_card', 'KPI-картка'),
            ('bar', 'Стовпці'),
            ('column', 'Смуги'),
            ('line', 'Лінія'),
            ('area', 'Область'),
            ('combo', 'Комбо'),
            ('pie', 'Pie/Donut'),
            ('table', 'Таблиця'),
            ('pivot', 'Pivot'),
            ('timeseries', 'Часовий ряд'),
            ('text', 'Текст'),
            ('image', 'Зображення'),
            # Етап 2
            ('multi_kpi', 'Мульти-KPI'),
            ('gauge', 'Gauge'),
            ('scatter', 'Scatter/Bubble'),
            ('treemap', 'Treemap'),
            ('heatmap', 'Heatmap'),
            ('waterfall', 'Waterfall'),
            ('funnel', 'Funnel'),
            ('choropleth', 'Гео-хороплет'),
            ('sparkline', 'Спарклайн'),
            # Етап 3
            ('bullet', 'Bullet'),
            ('sunburst', 'Sunburst'),
            ('sankey', 'Sankey'),
            ('radar', 'Radar'),
            ('geo_bubble', 'Гео-бульбашки'),
            ('iframe', 'Iframe/URL-embed'),
        ],
        string="Тип віджета",
    )  # ~28 типів (коди потребують уточнення, SPEC рядок 912)
    title = fields.Char(string="Заголовок", translate=True)  # шаблонізація {{param}}
    subtitle = fields.Char(string="Підзаголовок", translate=True)
    config = fields.Json(string="Конфігурація")  # data/style/interactions; conditional_rules[]
    domain = fields.Text(string="Домен віджета")  # ast.literal_eval (AC-12)
    pos_x = fields.Integer(string="Позиція X")  # сітка 24 колонки
    pos_y = fields.Integer(string="Позиція Y")
    width = fields.Integer(string="Ширина")
    height = fields.Integer(string="Висота")
    group_key = fields.Char(string="Ключ групи")  # scope контролів (§2.2.4)
    visible_condition = fields.Json(string="Умова видимості")
    sequence = fields.Integer(string="Послідовність")

    # === Constraints ===
    # SPEC: SQL constraints — None.
    # TODO: AC-18 — спуск у порожню групу не псує стан (порожній стан, не помилка).
    # TODO: AC-24 — «подивитися як» приховано без group_bi_admin.
    # TODO: AC-31 — без права експорту меню приховано, прямий виклик заборонено.
    # TODO: AC-45 — порядок правил умовного форматування визначає пріоритет (config.style.conditional_rules[]).
    # TODO: AC-46 — поріг з іншої міри; відсутнє значення -> правило не застосовується.
    # TODO: AC-49 — таймаут запиту дає картку помилки «повторити», не крах.
    # TODO: AC-56 — хороплет: нерозпізнаний код країни не валить рендер.
    # TODO: AC-58 — ієрархічний/каскадний контроль (child_of) залежних віджетів.

    # === Compute ===
    # SPEC: Computed fields — None.

    # === Actions ===
    # SPEC: Key methods — None (умовне форматування декларативно в config.style.conditional_rules[]).
