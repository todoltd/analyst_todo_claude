# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class TdBiAlert(models.Model):
    _name = 'td.bi.alert'
    _description = 'BI: Алерт'

    # === Fields ===
    widget_id = fields.Many2one(
        'td.bi.widget', string="Віджет", ondelete='cascade',
    )  # domain: KPI/gauge/card
    measure_key = fields.Char(string="Ключ міри")
    operator = fields.Selection(
        [
            ('>', 'Більше'),
            ('>=', 'Більше або дорівнює'),
            ('<', 'Менше'),
            ('<=', 'Менше або дорівнює'),
            ('=', 'Дорівнює'),
            ('!=', 'Не дорівнює'),
        ],
        string="Оператор",
    )
    threshold = fields.Float(string="Поріг-константа")
    threshold_parameter_id = fields.Many2one(
        'td.bi.parameter', string="Поріг-параметр",
    )
    check_interval = fields.Selection(
        selection='_selection_check_interval', string="Інтервал перевірки",
    )  # OPEN: SPEC «ТР не наводить довідник значень для check_interval»
    throttle = fields.Selection(
        [
            ('hourly', 'Не частіше разу на годину'),
            ('daily', 'Не частіше разу на день'),
        ],
        string="Троттлінг",
    )
    recipient_user_ids = fields.Many2many(
        'res.users', 'td_bi_alert_user_rel', 'alert_id', 'user_id',
        string="Отримувачі",
    )
    channels = fields.Json(string="Канали доставки")  # email/inbox/activity
    last_triggered = fields.Datetime(string="Останнє спрацювання")
    trigger_log_ids = fields.One2many(
        'td.bi.alert.log', 'alert_id', string="Журнал спрацювань",
    )

    # === Constraints ===
    # SPEC: SQL constraints — None. Record rule «лише свої» — ir.rule.

    # === Compute ===
    # SPEC: Computed fields — None.

    @api.model
    def _selection_check_interval(self):
        """Динамічний довідник інтервалів перевірки (SPEC: значення не зафіксовані)."""
        # OPEN: SPEC «ТР не наводить довідник значень для check_interval»
        return []

    # === Actions ===
    @api.model
    def _cron_check_alerts(self):
        """Перевіряє правило «значення оператор поріг», застосовує троттлінг (hourly/daily),
        доставляє по каналах email/inbox/activity, пише запис у td.bi.alert.log і оновлює
        last_triggered.
        # TODO: AC-35 — троттлінг «раз на день»: умова виконується двічі -> лист один раз,
                 обидва спрацювання у журналі."""
        # TODO: AC-35 — value <operator> threshold(/threshold_parameter_id); if not in throttle-window: deliver
        # TODO: AC-35 — канал activity через activity_schedule; запис td.bi.alert.log на КОЖНЕ спрацювання
        return True

    def action_view_trigger_log(self):
        """Smart-кнопка «Журнал спрацювань»: перехід до td.bi.alert.log з фільтром по alert_id."""
        # TODO: AC-35 — повертає ir.actions.act_window на td.bi.alert.log domain=[('alert_id','in',self.ids)]
        return True
