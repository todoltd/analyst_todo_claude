# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
# Stage-2 похідні показники show_as: percent_of_total / running_total / rank (AC-55).
# Виконується на живій Odoo 19:  odoo-bin -u td_bi_dashboard --test-enable
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'td_bi', 'td_bi_show_as')
class TestShowAs(TransactionCase):
    """Похідні показники рахуються на сервері пост-обробкою над RLS-безпечними рядками:
    % від підсумку, накопичувальний підсумок, ранг. Колонки <value_key>_pct/_running/_rank."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_im = cls.env['ir.model']._get('res.partner')
        cls.ua = cls.env.ref('base.ua')
        cls.pl = cls.env.ref('base.pl')
        cls.de = cls.env.ref('base.de')
        P = cls.env['res.partner']
        recs = P.create(
            [{'name': 'SA UA %d' % i, 'country_id': cls.ua.id} for i in range(3)]
            + [{'name': 'SA PL %d' % i, 'country_id': cls.pl.id} for i in range(2)]
            + [{'name': 'SA DE %d' % i, 'country_id': cls.de.id} for i in range(1)])
        cls.ids = recs.ids  # UA=3, PL=2, DE=1 (total 6)
        cls.ds = cls.env['td.bi.dataset'].create({
            'name': 'show_as dataset', 'mode': 'model',
            'model_id': cls.partner_im.id, 'visibility': 'global',
            'domain': repr([('id', 'in', cls.ids)]),
        })
        cls.f_country = cls.env['td.bi.dataset.field'].create({
            'dataset_id': cls.ds.id, 'name': 'country', 'path': 'country_id',
            'field_type': 'many2one', 'role': 'dimension'})
        cls.f_cnt = cls.env['td.bi.dataset.field'].create({
            'dataset_id': cls.ds.id, 'name': 'cnt', 'path': 'id',
            'field_type': 'integer', 'role': 'measure', 'aggregator': 'count'})
        cls.m_pct = cls.env['td.bi.measure'].create({
            'dataset_id': cls.ds.id, 'name': 'PCT', 'field_id': cls.f_cnt.id,
            'aggregator': 'count', 'show_as': 'percent_of_total'})
        cls.m_rt = cls.env['td.bi.measure'].create({
            'dataset_id': cls.ds.id, 'name': 'RT', 'field_id': cls.f_cnt.id,
            'aggregator': 'count', 'show_as': 'running_total'})
        cls.m_rank = cls.env['td.bi.measure'].create({
            'dataset_id': cls.ds.id, 'name': 'RANK', 'field_id': cls.f_cnt.id,
            'aggregator': 'count', 'show_as': 'rank'})

    def _rows(self, measure_name):
        return self.ds.run_query({
            'groupby': ['country_id'], 'measures': [measure_name]})['rows']

    # --- percent_of_total: кожен рядок / підсумок; UA = 3/6 = 0.5 ---
    def test_percent_of_total(self):
        rows = self._rows('PCT')
        by_country = {(r['country_id'][0] if isinstance(r.get('country_id'), (list, tuple))
                       else r.get('country_id')): r for r in rows}
        self.assertAlmostEqual(by_country[self.ua.id].get('id:count_pct'), 0.5,
                               msg="UA = 3/6 = 0.5 (percent_of_total читає value_key, не name).")
        total = sum((r.get('id:count_pct') or 0) for r in rows)
        self.assertAlmostEqual(total, 1.0, msg="Сума часток = 1.0.")

    # --- running_total: накопичувальний; максимум == загальний підсумок (6), монотонний ---
    def test_running_total(self):
        rows = self._rows('RT')
        running = [r.get('id:count_running') for r in rows]
        self.assertTrue(all(v is not None for v in running), "Кожен рядок має _running.")
        self.assertEqual(max(running), 6, "Накопичений максимум == загальна кількість (6).")
        self.assertEqual(running, sorted(running), "Накопичувальний підсумок монотонно зростає.")

    # --- rank: за спаданням; UA(3)=1, PL(2)=2, DE(1)=3 ---
    def test_rank(self):
        rows = self._rows('RANK')
        by_country = {(r['country_id'][0] if isinstance(r.get('country_id'), (list, tuple))
                       else r.get('country_id')): r for r in rows}
        self.assertEqual(by_country[self.ua.id].get('id:count_rank'), 1, "UA (3) — ранг 1.")
        self.assertEqual(by_country[self.pl.id].get('id:count_rank'), 2, "PL (2) — ранг 2.")
        self.assertEqual(by_country[self.de.id].get('id:count_rank'), 3, "DE (1) — ранг 3.")
