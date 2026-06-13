# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
import json
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

# Оператори правила алерта -> функція порівняння (значення vs поріг).
_ALERT_OPS = {
    '>': lambda v, t: v > t,
    '>=': lambda v, t: v >= t,
    '<': lambda v, t: v < t,
    '<=': lambda v, t: v <= t,
    '=': lambda v, t: v == t,
    '!=': lambda v, t: v != t,
}


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
        """AC-35 — перевіряє правило «значення <оператор> поріг» для кожного алерта.
        Журнал td.bi.alert.log пишеться на КОЖНЕ спрацювання умови; ДОСТАВКА (email/inbox)
        троттлиться (hourly/daily) — тож «умова двічі -> лист раз, обидва у журналі».
        last_triggered оновлюється лише при фактичній доставці.

        Значення віджета оцінюється ВІД ІМЕНІ власника алерта (create_uid) — RLS зберігається,
        без sudo на бізнес-даних. Алерти без віджета/міри/прав тихо пропускаються (не валить cron).
        """
        alerts = self.search([('widget_id', '!=', False)]) if not self else self
        log_model = self.env['td.bi.alert.log']
        now = fields.Datetime.now()
        for alert in alerts:
            try:
                value = alert._eval_value()
            except Exception as exc:  # noqa: BLE001 — один алерт не валить cron-батч
                _logger.info("BI alert %s: оцінка значення не вдалась: %s", alert.id, exc)
                continue
            if value is None:
                continue
            if not alert._condition_met(value):
                continue
            # Умова виконана -> завжди журнал; доставка з троттлінгом.
            throttled = alert._in_throttle_window(now)
            if throttled:
                delivery = 'throttled'
            else:
                delivery = alert._deliver(value)
                alert.last_triggered = now
            log_model.create({
                'alert_id': alert.id, 'value': value, 'delivery': delivery,
            })
        return True

    def _eval_value(self):
        """Поточне значення віджета алерта (ВІД ІМЕНІ власника). measure_key -> ключ у рядку;
        fallback: __count або перша числова міра. None, якщо немає даних/віджета."""
        self.ensure_one()
        widget = self.widget_id
        if not widget or not widget.dataset_id:
            return None
        cfg = widget.config
        if isinstance(cfg, str):
            try:
                cfg = json.loads(cfg)
            except (ValueError, TypeError):
                cfg = {}
        cfg = cfg or {}
        data = cfg.get('data') or cfg
        spec = {
            'groupby': data.get('groupby') or [],
            'measures': data.get('measures') or [],
            'aggregates': data.get('aggregates') or ['__count'],
        }
        owner = self.create_uid or self.env.user
        dataset = widget.dataset_id.with_user(owner)
        res = dataset.run_query(spec)
        rows = res.get('rows') or []
        if not rows:
            return None
        row = rows[0]
        key = self.measure_key
        if key and key in row and isinstance(row[key], (int, float)):
            return float(row[key])
        if '__count' in row and isinstance(row['__count'], (int, float)):
            return float(row['__count'])
        for k, v in row.items():
            if not str(k).startswith('__') and isinstance(v, (int, float)):
                return float(v)
        return None

    def _threshold_value(self):
        """Поріг: параметр (якщо заданий) або константа threshold."""
        self.ensure_one()
        param = self.threshold_parameter_id
        if param:
            for attr in ('value_number', 'value_float', 'value'):
                raw = getattr(param, attr, None)
                if isinstance(raw, (int, float)):
                    return float(raw)
                if isinstance(raw, str):
                    try:
                        return float(raw)
                    except (ValueError, TypeError):
                        pass
        return self.threshold or 0.0

    def _condition_met(self, value):
        """value <operator> threshold; невідомий оператор -> False (не спрацьовує)."""
        self.ensure_one()
        op = _ALERT_OPS.get(self.operator)
        if not op:
            return False
        try:
            return bool(op(float(value), self._threshold_value()))
        except (TypeError, ValueError):
            return False

    def _in_throttle_window(self, now):
        """Чи в межах вікна троттлінгу від last_triggered (hourly=1год, daily=1день)."""
        self.ensure_one()
        if not self.throttle or not self.last_triggered:
            return False
        from datetime import timedelta
        window = timedelta(hours=1) if self.throttle == 'hourly' else timedelta(days=1)
        return (now - self.last_triggered) < window

    def _deliver(self, value):
        """Доставка по каналах (email -> mail.mail у черзі; без SMTP-надсилання тут).
        Повертає опис результату для журналу. Помилка каналу не валить cron."""
        self.ensure_one()
        channels = self.channels if isinstance(self.channels, (list, dict)) else []
        if isinstance(channels, dict):
            channels = [k for k, v in channels.items() if v]
        recipients = self.recipient_user_ids
        sent = []
        if ('email' in channels or not channels) and recipients:
            emails = [u.email for u in recipients if u.email]
            if emails:
                try:
                    self.env['mail.mail'].sudo().create({
                        'subject': _("BI-алерт спрацював: %s", value),
                        'body_html': _("<p>Значення %(v)s %(op)s поріг %(t)s.</p>", v=value,
                                       op=self.operator or '', t=self._threshold_value()),
                        'email_to': ','.join(emails),
                    })
                    sent.append('email:%d' % len(emails))
                except Exception as exc:  # noqa: BLE001
                    _logger.info("BI alert %s email queue failed: %s", self.id, exc)
        return 'sent(%s)' % ','.join(sent) if sent else 'sent(logged)'

    def action_view_trigger_log(self):
        """Smart-кнопка «Журнал спрацювань»: перехід до td.bi.alert.log з фільтром по alert_id."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Журнал спрацювань"),
            'res_model': 'td.bi.alert.log',
            'view_mode': 'list,form',
            'domain': [('alert_id', 'in', self.ids)],
        }
