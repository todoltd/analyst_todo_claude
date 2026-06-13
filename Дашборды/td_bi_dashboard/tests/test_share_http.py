# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
# Stage-2 публічний контур frozen-посилань через HTTP (AC-26/29/30/31) — HttpCase.
# Виконується на живій Odoo 19:  odoo-bin -u td_bi_dashboard --test-enable
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install', 'td_bi', 'td_bi_http')
class TestShareHttp(HttpCase):
    """Кінцева перевірка публічних роутів: валідний токен -> 200 зі знімком; невалідний/
    відкликаний -> 404; експорт замороженого знімка -> XLSX. (Cursor спільний у test-mode.)"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        partner_im = cls.env['ir.model']._get('res.partner')
        recs = cls.env['res.partner'].create([{'name': 'HT %d' % i} for i in range(3)])
        cls.ds = cls.env['td.bi.dataset'].create({
            'name': 'HTTP share ds', 'mode': 'model', 'model_id': partner_im.id,
            'visibility': 'global', 'domain': repr([('id', 'in', recs.ids)])})
        cls.dash = cls.env['td.bi.dashboard'].create({'name': 'HTTP share dash', 'state': 'published'})
        cls.page = cls.env['td.bi.dashboard.page'].create({'dashboard_id': cls.dash.id, 'name': 'P'})
        cls.widget = cls.env['td.bi.widget'].create({
            'page_id': cls.page.id, 'dataset_id': cls.ds.id, 'widget_type': 'kpi_card',
            'title': 'Count', 'config': {'data': {'groupby': [], 'aggregates': ['__count']}}})
        cls.share = cls.env['td.bi.dashboard.share'].create({
            'dashboard_id': cls.dash.id, 'allow_export': True})
        cls.share.action_freeze_snapshot()

    def test_share_page_valid_token(self):
        resp = self.url_open('/bi/share/%s/%s' % (self.share.id, self.share.access_token))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('HTTP share dash', resp.text)

    def test_share_invalid_token_404(self):
        resp = self.url_open('/bi/share/%s/%s' % (self.share.id, 'deadbeefdeadbeef'))
        self.assertEqual(resp.status_code, 404, "Невалідний токен -> 404 (consteq).")

    def test_share_export_xlsx(self):
        resp = self.url_open('/bi/share/%s/%s/export?format=xlsx' % (
            self.share.id, self.share.access_token))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.content.startswith(b'PK'), "Експорт замороженого знімка -> XLSX.")

    def test_share_revoked_404(self):
        self.share.action_revoke()
        resp = self.url_open('/bi/share/%s/%s' % (self.share.id, self.share.access_token))
        self.assertEqual(resp.status_code, 404, "Відкликане посилання -> 404 (AC-30).")
