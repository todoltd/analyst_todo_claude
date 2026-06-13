# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
# Stage-2 заморожені публічні посилання: знімок-attachment, валідність, відкликання (AC-26/29/30).
# Виконується на живій Odoo 19:  odoo-bin -u td_bi_dashboard --test-enable
from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'td_bi', 'td_bi_share')
class TestDashboardShare(TransactionCase):
    """Frozen-посилання: дані замороження у ir.attachment (рендер ВІД ІМЕНІ автора), публічний
    контур віддає лише знімок (без живих запитів); відкликання/термін роблять посилання недійсним."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        partner_im = cls.env['ir.model']._get('res.partner')
        recs = cls.env['res.partner'].create([{'name': 'SH %d' % i} for i in range(3)])
        cls.ds = cls.env['td.bi.dataset'].create({
            'name': 'Share dataset', 'mode': 'model', 'model_id': partner_im.id,
            'visibility': 'global', 'domain': repr([('id', 'in', recs.ids)])})
        cls.dash = cls.env['td.bi.dashboard'].create({'name': 'Share dash', 'state': 'published'})
        cls.page = cls.env['td.bi.dashboard.page'].create({'dashboard_id': cls.dash.id, 'name': 'P'})
        cls.widget = cls.env['td.bi.widget'].create({
            'page_id': cls.page.id, 'dataset_id': cls.ds.id, 'widget_type': 'kpi_card',
            'title': 'Count', 'config': {'data': {'groupby': [], 'aggregates': ['__count']}}})
        cls.share = cls.env['td.bi.dashboard.share'].create({'dashboard_id': cls.dash.id})

    # --- Заморозка -> attachment + get_frozen_data повертає дані знімка ---
    def test_freeze_and_frozen_data(self):
        self.share.action_freeze_snapshot()
        self.assertTrue(self.share.snapshot_attachment_id, "Знімок збережено як attachment.")
        data = self.share.get_frozen_data()
        self.assertEqual(data.get('name'), 'Share dash')
        rows = data['pages'][0]['widgets'][0]['data'].get('rows')
        self.assertEqual(rows[0].get('__count'), 3, "Заморожено рівно 3 контакти.")

    # --- full_url містить /bi/share/<id>/<token> ---
    def test_full_url(self):
        self.assertIn('/bi/share/%s/%s' % (self.share.id, self.share.access_token),
                      self.share.full_url or '')

    # --- Свіже посилання дійсне; відкликане — ні (AC-30) ---
    def test_revoke_invalidates(self):
        self.assertTrue(self.share._check_public_validity(), "Свіже посилання дійсне.")
        self.share.action_revoke()
        self.assertFalse(self.share.active)
        self.assertFalse(self.share._check_public_validity(), "Відкликане посилання недійсне.")

    # --- Прострочене посилання недійсне (AC-26) ---
    def test_expired_invalid(self):
        self.share.expiration_date = '2000-01-01 00:00:00'
        self.assertFalse(self.share._check_public_validity(), "Прострочене посилання недійсне.")

    # --- get_frozen_data читає СТАЛИЙ attachment (без живих запитів, AC-29) ---
    def test_frozen_data_is_static(self):
        self.share.action_freeze_snapshot()
        first = self.share.get_frozen_data()['pages'][0]['widgets'][0]['data']['rows'][0]['__count']
        # Створюємо ще контакти у БД — заморожений знімок НЕ перезапитує й лишається сталим.
        self.env['res.partner'].create([{'name': 'SH x %d' % i} for i in range(5)])
        second = self.share.get_frozen_data()['pages'][0]['widgets'][0]['data']['rows'][0]['__count']
        self.assertEqual(first, second, "Заморожені дані сталі (читаються з attachment, не з БД).")
