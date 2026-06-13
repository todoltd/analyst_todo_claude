# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.http import Controller, request, route, Response
from odoo.tools import consteq

import logging

_logger = logging.getLogger(__name__)


class BiShareController(Controller):
    """Публічний контур frozen-посилань на дашборд (auth='public').

    Звірка токена через consteq (constant-time), рендер виключно знімка
    (snapshot_attachment_id) без живих запитів до бізнес-моделей.
    Сам запис td.bi.dashboard.share читається через sudo лише службово
    (НЕ бізнес-дані); токен / термін / право автора перевіряються вручну.
    """

    def _get_share_or_invalid(self, share_id, token):
        """Службове читання запису-посилання + звірка токена через consteq.

        Повертає (share, None) при валідному токені або (None, response)
        зі сторінкою-помилкою при невідповідності/деактивації/терміні.
        """
        # sudo() ЛИШЕ для службового читання запису share (метадані, не бізнес-дані);
        # consteq — constant-time звірка токена; далі _check_public_validity (AC-26/27/30):
        # active ∧ не прострочене ∧ автор досі має право читати дашборд.
        share = request.env['td.bi.dashboard.share'].sudo().browse(int(share_id)).exists()
        if not share or not consteq(share.access_token or '', token or ''):
            return None, request.not_found()
        if not share._check_public_validity():
            return None, request.not_found()
        return share, None

    @route('/bi/share/<int:share_id>/<string:token>', type='http', auth='public', website=False, csrf=False)
    def bi_share(self, share_id, token, **kwargs):
        """Frozen-сторінка дашборда за публічним посиланням (auth='public').  # AC-26, AC-27, AC-29, AC-30"""
        share, err = self._get_share_or_invalid(share_id, token)
        if err is not None:
            return err
        # Лише frozen-знімок (AC-29): жодних живих запитів — мінімальна HTML-обгортка,
        # дані тягне /data (також із замороженого знімка).
        snapshot = share.get_frozen_data()
        name = (snapshot.get('name') if isinstance(snapshot, dict) else '') or _("Дашборд")
        html = '<!DOCTYPE html><html><head><meta charset="utf-8"><title>%s</title></head>' \
               '<body><h1>%s</h1><p>BI frozen snapshot.</p></body></html>' % (name, name)
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])

    @route('/bi/share/<int:share_id>/<string:token>/data', type='json', auth='public', csrf=False)
    def bi_share_data(self, share_id, token, **kwargs):
        """Заморожені точки даних знімка (БЕЗ живих запитів до бізнес-моделей).  # AC-26, AC-29"""
        share, err = self._get_share_or_invalid(share_id, token)
        if err is not None:
            return {}
        return share.get_frozen_data()

    @route('/bi/share/<int:share_id>/<string:token>/export', type='http', auth='public', csrf=False)
    def bi_share_export(self, share_id, token, **kwargs):
        """Експорт ЗАМОРОЖЕНОГО знімка публічного посилання (лише allow_export).  # AC-31, AC-37
        Рендер із frozen-даних (без живих запитів, AC-29); порожня вибірка -> файл лише
        із заголовками (AC-37). format=pdf|xlsx (за замовч. xlsx)."""
        share, err = self._get_share_or_invalid(share_id, token)
        if err is not None:
            return err
        if not share.allow_export:
            return request.not_found()  # AC-31: експорт не дозволено для цього посилання
        snapshot = share.get_frozen_data()
        dashboard = share.dashboard_id.sudo()  # рендер зі знімка (sudo лише для виклику, не для даних)
        fmt = (kwargs.get('format') or 'xlsx').lower()
        if fmt == 'pdf':
            content = dashboard.export_pdf(snapshot=snapshot)
            ctype, fname = 'application/pdf', 'bi_snapshot.pdf'
        else:
            content = dashboard.export_xlsx(snapshot=snapshot)
            ctype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            fname = 'bi_snapshot.xlsx'
        return request.make_response(content, headers=[
            ('Content-Type', ctype),
            ('Content-Disposition', 'attachment; filename="%s"' % fname)])


class BiEmbedController(Controller):
    """Embed-контур дашборда (auth='public') з CSP frame-ancestors."""

    @route('/bi/embed/<int:dashboard_id>', type='http', auth='public', website=False, csrf=False)
    def bi_embed(self, dashboard_id, **kwargs):
        """Embed дашборда з заголовком Content-Security-Policy: frame-ancestors.  # AC-26, AC-29"""
        # TODO: AC-26 — embed віддає лише frozen-знімок (без живих запитів до бізнес-моделей).
        # TODO: AC-29 — лише frozen-режим (live-публічного доступу немає, ОВ-4).
        # CSP frame-ancestors виставляється з allowed_frame_ancestors запису share (контролер віддає заголовок сам).
        frame_ancestors = "'none'"
        headers = [
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Content-Security-Policy', 'frame-ancestors %s' % frame_ancestors),
        ]
        return request.make_response('', headers=headers)


class BiExportController(Controller):
    """Експорт даних/дашборда для автентифікованого користувача (auth='user')."""

    @route('/bi/export/xlsx', type='http', auth='user', methods=['POST'], csrf=False)
    def bi_export_xlsx(self, **kwargs):
        """Експорт дашборда у XLSX (ВІД ІМЕНІ користувача — RLS).  # AC-31, AC-36, AC-37"""
        if not request.env.user.has_group('base.group_allow_export'):
            raise AccessError(_("У вас немає права на експорт даних."))
        dashboard = request.env['td.bi.dashboard'].browse(
            int(kwargs.get('dashboard_id') or 0)).exists()
        if not dashboard:
            return request.not_found()
        content = dashboard.export_xlsx(as_user=request.env.user)
        return request.make_response(
            content,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', 'attachment; filename="bi_export.xlsx"'),
            ],
        )

    @route('/bi/export/pdf', type='http', auth='user', methods=['POST'], csrf=False)
    def bi_export_pdf(self, **kwargs):
        """Експорт дашборда у PDF (ВІД ІМЕНІ користувача — RLS; wkhtmltopdf).  # AC-31, AC-32"""
        if not request.env.user.has_group('base.group_allow_export'):
            raise AccessError(_("У вас немає права на експорт даних."))
        dashboard = request.env['td.bi.dashboard'].browse(
            int(kwargs.get('dashboard_id') or 0)).exists()
        if not dashboard:
            return request.not_found()
        content = dashboard.export_pdf(as_user=request.env.user)
        return request.make_response(
            content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', 'attachment; filename="bi_export.pdf"'),
            ],
        )
