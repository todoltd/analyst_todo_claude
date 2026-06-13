# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
# Stage-2 підписки + знімок: render_snapshot / action_send_now / _cron_run_subscriptions (AC-33/34/61).
# Виконується на живій Odoo 19:  odoo-bin -u td_bi_dashboard --test-enable
from odoo.tests import TransactionCase, tagged, new_test_user


@tagged('post_install', '-at_install', 'td_bi', 'td_bi_subscription')
class TestSubscription(TransactionCase):
    """Знімок дашборда рендериться ВІД ІМЕНІ отримувача (RLS); підписка ставить лист у чергу;
    cron оновлює next_run незалежно від збоїв."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        partner_im = cls.env['ir.model']._get('res.partner')
        recs = cls.env['res.partner'].create([{'name': 'SUB %d' % i} for i in range(3)])
        cls.recipient = new_test_user(
            cls.env, login='bi_sub_user', name='Sub User',
            groups='base.group_user,td_bi_dashboard.group_bi_user')
        cls.recipient.email = 'sub@example.com'
        cls.ds = cls.env['td.bi.dataset'].create({
            'name': 'Sub dataset', 'mode': 'model', 'model_id': partner_im.id,
            'visibility': 'global', 'domain': repr([('id', 'in', recs.ids)]),
        })
        cls.dash = cls.env['td.bi.dashboard'].create({
            'name': 'Sub dash', 'state': 'published', 'owner_id': cls.recipient.id})
        cls.page = cls.env['td.bi.dashboard.page'].create({
            'dashboard_id': cls.dash.id, 'name': 'P'})
        cls.widget = cls.env['td.bi.widget'].create({
            'page_id': cls.page.id, 'dataset_id': cls.ds.id, 'widget_type': 'kpi_card',
            'title': 'Count', 'config': {'data': {'groupby': [], 'aggregates': ['__count']}}})
        cls.sub = cls.env['td.bi.subscription'].create({
            'dashboard_id': cls.dash.id, 'schedule_type': 'daily', 'format': 'link',
            'recipient_user_ids': [(6, 0, [cls.recipient.id])]})

    # --- render_snapshot ВІД ІМЕНІ отримувача повертає дані віджетів ---
    def test_render_snapshot_as_user(self):
        snap = self.dash.render_snapshot(as_user=self.recipient)
        self.assertEqual(snap['name'], 'Sub dash')
        rows = snap['pages'][0]['widgets'][0]['data'].get('rows')
        self.assertTrue(rows, "Знімок містить дані віджета (як отримувач).")
        self.assertEqual(rows[0].get('__count'), 3, "Бачить рівно 3 свої контакти.")

    # --- action_send_now ставить лист у чергу для отримувача ---
    def test_action_send_now_queues_mail(self):
        before = self.env['mail.mail'].search_count([('email_to', '=', 'sub@example.com')])
        res = self.sub.action_send_now()
        self.assertEqual(res.get(self.recipient.id), 'sent')
        after = self.env['mail.mail'].search_count([('email_to', '=', 'sub@example.com')])
        self.assertEqual(after, before + 1, "Один лист у черзі для отримувача.")
        self.assertTrue(self.sub.last_run, "last_run проставлено.")

    # --- cron оновлює next_run (daily -> ~ +1 день) ---
    def test_cron_sets_next_run(self):
        self.sub.next_run = False
        self.env['td.bi.subscription']._cron_run_subscriptions()
        self.assertTrue(self.sub.next_run, "next_run обчислено після cron.")
        self.assertTrue(self.sub.last_run)

    # --- only_if_data: знімок без рядків -> доставку пропущено ---
    def test_only_if_data_skips_empty(self):
        empty_ds = self.env['td.bi.dataset'].create({
            'name': 'Empty ds', 'mode': 'model',
            'model_id': self.env['ir.model']._get('res.partner').id,
            'visibility': 'global', 'domain': repr([('id', '=', 0)])})
        empty_widget = self.env['td.bi.widget'].create({
            'page_id': self.page.id, 'dataset_id': empty_ds.id, 'widget_type': 'table',
            'title': 'Empty', 'config': {'data': {'groupby': ['country_id'], 'aggregates': ['__count']}}})
        dash2 = self.env['td.bi.dashboard'].create({
            'name': 'Empty dash', 'state': 'published', 'owner_id': self.recipient.id})
        page2 = self.env['td.bi.dashboard.page'].create({'dashboard_id': dash2.id, 'name': 'P2'})
        empty_widget.page_id = page2
        sub2 = self.env['td.bi.subscription'].create({
            'dashboard_id': dash2.id, 'schedule_type': 'daily', 'format': 'link',
            'only_if_data': True, 'recipient_user_ids': [(6, 0, [self.recipient.id])]})
        res = sub2.action_send_now()
        self.assertEqual(res.get(self.recipient.id), 'skipped(no-data)',
                         "Порожній знімок із only_if_data -> доставку пропущено.")
