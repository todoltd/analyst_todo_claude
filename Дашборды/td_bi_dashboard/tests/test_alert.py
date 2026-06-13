# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
# Stage-2 алерти: _cron_check_alerts — поріг, журнал, троттлінг (AC-35).
# Виконується на живій Odoo 19:  odoo-bin -u td_bi_dashboard --test-enable
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'td_bi', 'td_bi_alert')
class TestAlert(TransactionCase):
    """Алерт оцінює значення віджета ВІД ІМЕНІ власника, порівнює з порогом, пише журнал
    на кожне спрацювання й троттлить доставку (hourly/daily)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        partner_im = cls.env['ir.model']._get('res.partner')
        recs = cls.env['res.partner'].create(
            [{'name': 'AL %d' % i} for i in range(4)])  # рівно 4 контакти
        cls.ds = cls.env['td.bi.dataset'].create({
            'name': 'Alert dataset', 'mode': 'model', 'model_id': partner_im.id,
            'visibility': 'global', 'domain': repr([('id', 'in', recs.ids)]),
        })
        cls.dash = cls.env['td.bi.dashboard'].create({'name': 'Alert dash'})
        cls.page = cls.env['td.bi.dashboard.page'].create({
            'dashboard_id': cls.dash.id, 'name': 'P'})
        cls.widget = cls.env['td.bi.widget'].create({
            'page_id': cls.page.id, 'dataset_id': cls.ds.id, 'widget_type': 'kpi_card',
            'title': 'Count', 'config': {'data': {'groupby': [], 'aggregates': ['__count']}},
        })

    def _alert(self, operator, threshold, throttle=False):
        return self.env['td.bi.alert'].create({
            'widget_id': self.widget.id, 'operator': operator, 'threshold': threshold,
            'throttle': throttle, 'channels': ['email'],
        })

    # --- Умова виконана -> журнал зі значенням, last_triggered проставлено ---
    def test_alert_fires_and_logs(self):
        alert = self._alert('>', 2.0)  # 4 > 2 -> спрацьовує
        alert._cron_check_alerts()
        self.assertEqual(len(alert.trigger_log_ids), 1, "Спрацювання -> один запис у журналі.")
        self.assertEqual(alert.trigger_log_ids.value, 4.0, "Зафіксоване значення = 4.")
        self.assertTrue(alert.last_triggered, "last_triggered проставлено при доставці.")

    # --- Умова не виконана -> ні журналу, ні last_triggered ---
    def test_alert_not_triggered(self):
        alert = self._alert('>', 10.0)  # 4 > 10 -> ні
        alert._cron_check_alerts()
        self.assertEqual(len(alert.trigger_log_ids), 0, "Без виконання умови — без журналу.")
        self.assertFalse(alert.last_triggered)

    # --- AC-35 троттлінг daily: умова двічі -> доставка раз, обидва у журналі ---
    def test_alert_throttle_daily(self):
        alert = self._alert('>', 2.0, throttle='daily')
        alert._cron_check_alerts()
        first_ts = alert.last_triggered
        self.assertEqual(len(alert.trigger_log_ids), 1)
        self.assertTrue(str(alert.trigger_log_ids[0].delivery or '').startswith('sent'))
        # Другий прогін у межах доби -> журнал так, доставка throttled, last_triggered без змін.
        alert._cron_check_alerts()
        self.assertEqual(len(alert.trigger_log_ids), 2, "Обидва спрацювання у журналі (AC-35).")
        throttled = alert.trigger_log_ids.filtered(lambda l: l.delivery == 'throttled')
        self.assertEqual(len(throttled), 1, "Друга доставка — throttled (лист один раз).")
        self.assertEqual(alert.last_triggered, first_ts, "last_triggered не оновлюється у вікні троттлінгу.")
