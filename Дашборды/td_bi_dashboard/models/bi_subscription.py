# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


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
        """Рендерить серверний знімок (той самий конвеєр, що frozen-посилання) і шле mail.template
        із вкладенням; внутрішньому отримувачу — від його імені (with_user, дані за його правами),
        зовнішньому email — від імені автора з поміткою (ОВ-7).
        # TODO: AC-61 — render_snapshot під with_user(recipient); збій одного не блокує інших."""
        # TODO: AC-33 — дані = права отримувача (RLS) ∧ filters_payload
        # TODO: AC-61 — for recipient: try render_snapshot(... as_user=recipient) except -> _logger + журнал
        return True

    @api.model
    def _cron_run_subscriptions(self):
        """Плановий запуск розсилок за schedule_type; стійкість до таймаутів через _commit_progress;
        оновлює last_run/next_run.
        # TODO: AC-34 — збій рендера: лист не шлеться, помилка в журнал; стан не «зависає»."""
        # TODO: AC-33 — обхід активних підписок з next_run <= now; той самий конвеєр render_snapshot
        # TODO: AC-34 — try/except навколо рендера; last_run/next_run оновлюються незалежно від збою
        return True
