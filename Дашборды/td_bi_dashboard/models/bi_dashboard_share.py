# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
import json
import logging
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class TdBiDashboardShare(models.Model):
    _name = 'td.bi.dashboard.share'
    _description = 'BI: Публічне посилання'

    # === Fields ===
    dashboard_id = fields.Many2one(
        'td.bi.dashboard', string="Дашборд", required=True, ondelete='cascade',
    )
    access_token = fields.Char(
        string="Токен доступу", default=lambda self: uuid.uuid4().hex, copy=False,
    )  # звірка через consteq (AC-26)
    snapshot_attachment_id = fields.Many2one(
        'ir.attachment', string="Frozen-знімок",
    )  # єдиний режим публічного доступу (ОВ-4; AC-29)
    expiration_date = fields.Datetime(string="Термін дії")
    password_hash = fields.Char(string="Хеш пароля")
    allowed_frame_ancestors = fields.Char(
        string="Дозволені домени embed",
    )  # Content-Security-Policy: frame-ancestors
    allow_export = fields.Boolean(string="Дозволити експорт")
    active = fields.Boolean(string="Активне", default=True)

    # === Computed fields ===
    full_url = fields.Char(
        string="Повне посилання", compute='_compute_full_url', readonly=True,
    )

    @api.depends('access_token')  # + base_url (ir.config_parameter 'web.base.url')
    def _compute_full_url(self):
        """Формує full_url із id, access_token і base_url (AC-26): /bi/share/<id>/<token>."""
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
        for record in self:
            if record.id and record.access_token:
                record.full_url = '%s/bi/share/%s/%s' % (base, record.id, record.access_token)
            else:
                record.full_url = False

    # === Constraints ===
    # SPEC: SQL constraints — None. Створювати запис може лише group_bi_admin (ACL).

    # === Actions ===
    def action_freeze_snapshot(self):
        """Заморожує ДАНІ дашборда у знімок (ir.attachment JSON) ВІД ІМЕНІ автора посилання
        (RLS на момент заморозки). Публічний контур віддає лише ці заморожені дані — жодних
        живих запитів до бізнес-моделей (AC-26/AC-29). Повертає attachment."""
        self.ensure_one()
        author = self.create_uid or self.env.user
        snapshot = self.dashboard_id.render_snapshot(as_user=author)
        payload = json.dumps(snapshot, default=str).encode('utf-8')
        attachment = self.env['ir.attachment'].sudo().create({
            'name': 'bi_snapshot_%s.json' % self.id,
            'raw': payload,
            'mimetype': 'application/json',
            'res_model': self._name,
            'res_id': self.id,
        })
        self.snapshot_attachment_id = attachment.id
        return attachment

    def get_frozen_data(self):
        """Заморожені дані знімка (dict) зі snapshot_attachment_id; {} якщо немає/пошкоджено.
        БЕЗ живих запитів до бізнес-моделей (AC-29)."""
        self.ensure_one()
        attachment = self.snapshot_attachment_id.sudo()
        if not attachment or not attachment.raw:
            return {}
        try:
            return json.loads(attachment.raw.decode('utf-8'))
        except (ValueError, TypeError, UnicodeDecodeError):
            return {}

    def _check_public_validity(self):
        """Чи дійсне посилання для публічного доступу (AC-26/27/30):
        active ∧ не прострочене ∧ автор досі має право читати дашборд (інакше доступ закрито)."""
        self.ensure_one()
        if not self.active:
            return False
        if self.expiration_date and self.expiration_date < fields.Datetime.now():
            return False
        author = self.create_uid
        if author:
            try:
                if not self.dashboard_id.with_user(author).has_access('read'):
                    return False
            except Exception:  # noqa: BLE001 — будь-яка проблема прав -> доступ закрито
                return False
        return True

    def action_revoke(self):
        """AC-30 — деактивація (active=False) -> негайна недоступність посилання
        (наступне відкриття того ж URL -> «посилання недійсне» через _check_public_validity)."""
        self.write({'active': False})
        return True

    # Примітки реалізації (контролер /bi/share, controllers/main.py):
    # TODO: AC-26 — звірка токена через consteq (constant-time); некоректний -> «посилання недійсне»,
    #               вичерпаний expiration_date -> «термін дії вичерпано».
    # TODO: AC-27 — with_user(create_uid).has_access('read') на дашборд; автор втратив право -> доступ закрито,
    #               живі запити до даних не виконуються.
    # TODO: AC-29 — доступний лише frozen-режим знімка (опції «живого» публічного доступу немає, ОВ-4).
