# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
import logging

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class TdBiSubscription(models.Model):
    _name = 'td.bi.subscription'
    _description = 'BI: Підписка (розсилка за розкладом)'

    # === Fields ===
    dashboard_id = fields.Many2one(
        'td.bi.dashboard', string="Дашборд", required=True, ondelete='cascade',
    )
    page_ids = fields.Many2many('td.bi.dashboard.page', string="Сторінки")
    recipient_user_ids = fields.Many2many(
        'res.users', 'td_bi_subscription_user_rel', 'subscription_id', 'user_id',
        string="Отримувачі-користувачі",
    )  # внутрішні; рендер від імені отримувача (AC-33, AC-61)
    recipient_partner_ids = fields.Many2many(
        'res.partner', 'td_bi_subscription_partner_rel', 'subscription_id', 'partner_id',
        string="Отримувачі-партнери",
    )
    emails = fields.Text(string="Зовнішні email")  # рендер від імені автора (ОВ-7)
    schedule_type = fields.Selection(
        [
            ('daily', 'Щодня'),
            ('weekly', 'Щотижня'),
            ('monthly', 'Щомісяця'),
            ('cron', 'Cron-вираз (адмін)'),
        ],
        string="Тип розкладу",
    )
    weekday_ids = fields.Many2many(
        'td.bi.dashboard.tag', 'td_bi_subscription_weekday_rel', 'subscription_id', 'tag_id',
        string="Дні тижня",
    )  # OPEN: comodel weekday-довідника SPEC не фіксує
    monthday = fields.Integer(string="День місяця")
    time = fields.Float(string="Година доби")
    cron_expr = fields.Char(string="Cron-вираз")
    format = fields.Selection(
        [
            ('pdf', 'PDF'),
            ('xlsx', 'XLSX'),
            ('link', 'Посилання'),
        ],
        string="Формат розсилки",
    )
    filters_payload = fields.Json(string="Фіксовані фільтри")
    only_if_data = fields.Boolean(string="Лише якщо є дані")
    active = fields.Boolean(string="Активна", default=True)
    last_run = fields.Datetime(string="Останній запуск")
    next_run = fields.Datetime(string="Наступний запуск")
    mail_template_id = fields.Many2one('mail.template', string="Шаблон листа")

    # === Constraints ===
    # SPEC: SQL constraints — None. Record rule «лише свої» (create_uid = user.id) — ir.rule.

    # === Compute ===
    # SPEC: Computed fields — None.

    # === Actions ===
    def action_send_now(self):
        """Рендерить серверний знімок ВІД ІМЕНІ кожного внутрішнього отримувача (with_user —
        дані за його правами, AC-33/AC-61) і ставить лист у чергу (mail.mail). Збій одного
        отримувача НЕ блокує інших. Повертає мапу {user_id: результат}.
        only_if_data -> отримувачам без даних не шлемо (ОВ-7)."""
        results = {}
        for sub in self:
            for recipient in sub.recipient_user_ids:
                try:
                    results[recipient.id] = sub._send_to_recipient(recipient)
                except Exception as exc:  # noqa: BLE001 — AC-61: збій одного не валить інших
                    _logger.warning("BI підписка %s -> користувач %s: збій доставки: %s",
                                    sub.id, recipient.id, exc)
                    results[recipient.id] = 'error'
            sub.last_run = fields.Datetime.now()
        return results

    def _send_to_recipient(self, recipient):
        """Знімок дашборда ВІД ІМЕНІ отримувача (RLS ∧ filters_payload) -> лист у черзі.
        only_if_data -> пропуск без даних. Без email -> 'no-email'."""
        self.ensure_one()
        snapshot = self.dashboard_id.render_snapshot(self.filters_payload, as_user=recipient)
        if self.only_if_data and not self.dashboard_id.snapshot_has_data(snapshot):
            return 'skipped(no-data)'
        if not recipient.email:
            return 'no-email'
        self.env['mail.mail'].sudo().create({
            'subject': _("BI-розсилка: %s", snapshot.get('name') or self.dashboard_id.name),
            'body_html': self._snapshot_html(snapshot),
            'email_to': recipient.email,
        })
        return 'sent'

    def _snapshot_html(self, snapshot):
        """Простий HTML-зміст знімка (назва + віджети з к-стю рядків). PDF/XLSX-рендер — далі."""
        parts = ['<h2>%s</h2>' % (snapshot.get('name') or '')]
        for page in snapshot.get('pages', []):
            parts.append('<h3>%s</h3><ul>' % (page.get('name') or ''))
            for widget in page.get('widgets', []):
                data = widget.get('data') or {}
                n = len(data.get('rows') or []) if isinstance(data, dict) else 0
                parts.append('<li>%s — рядків: %d</li>' % (widget.get('title') or '', n))
            parts.append('</ul>')
        return ''.join(parts)

    @api.model
    def _cron_run_subscriptions(self):
        """AC-33/34 — планово шле активні підписки з next_run <= now (або без next_run).
        Кожна підписка у власному try/except: збій рендера/доставки не «зависає» — last_run/
        next_run оновлюються НЕЗАЛЕЖНО (стан рухається далі)."""
        now = fields.Datetime.now()
        due = self.search([
            '&', ('active', '=', True),
            '|', ('next_run', '=', False), ('next_run', '<=', now),
        ])
        for sub in due:
            try:
                sub.action_send_now()
            except Exception as exc:  # noqa: BLE001 — AC-34: збій не блокує оновлення стану
                _logger.warning("BI підписка %s: збій планового запуску: %s", sub.id, exc)
            sub.last_run = now
            sub.next_run = sub._compute_next_run(now)
        return True

    def _compute_next_run(self, now):
        """Наступний запуск за schedule_type (daily/weekly/monthly; cron/інше -> +1 день)."""
        self.ensure_one()
        st = self.schedule_type
        if st == 'weekly':
            return now + relativedelta(weeks=1)
        if st == 'monthly':
            return now + relativedelta(months=1)
        return now + relativedelta(days=1)
