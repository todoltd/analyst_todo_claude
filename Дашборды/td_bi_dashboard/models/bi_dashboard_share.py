# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


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
        """Формує full_url із id, access_token і base_url.  # TODO: AC-26 — /bi/share/<id>/<token>"""
        # TODO: AC-26 — base = ir.config_parameter 'web.base.url' + '/bi/share/%s/%s' % (id, token)
        for record in self:
            record.full_url = False

    # === Constraints ===
    # SPEC: SQL constraints — None. Створювати запис може лише group_bi_admin (ACL).

    # === Actions ===
    def action_revoke(self):
        """Деактивація запису (active=False) -> негайна недоступність посилання.
        # TODO: AC-30 — наступне відкриття того ж URL -> сторінка «посилання недійсне»."""
        # TODO: AC-30 — self.write({'active': False}); запис у td.bi.audit.log (share_revoke)
        return True

    # Примітки реалізації (контролер /bi/share, controllers/main.py):
    # TODO: AC-26 — звірка токена через consteq (constant-time); некоректний -> «посилання недійсне»,
    #               вичерпаний expiration_date -> «термін дії вичерпано».
    # TODO: AC-27 — with_user(create_uid).has_access('read') на дашборд; автор втратив право -> доступ закрито,
    #               живі запити до даних не виконуються.
    # TODO: AC-29 — доступний лише frozen-режим знімка (опції «живого» публічного доступу немає, ОВ-4).
