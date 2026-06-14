# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
# Stage-2 бленд (mode='blend'): CTE-конвеєр із RLS у кожному джерелі (AC-38/39/40/41).
# Виконується на живій Odoo 19:  odoo-bin -u td_bi_dashboard --test-enable
from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged, new_test_user


@tagged('post_install', '-at_install', 'td_bi', 'td_bi_blend')
class TestBlendQuery(TransactionCase):
    """Бленд: предагрегація кожного джерела ДО зʼєднання, JOIN за ключами (left/inner),
    RLS у WHERE кожного CTE (без sudo). Демо-бленд: res.partner LEFT/INNER res.country."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_im = cls.env['ir.model']._get('res.partner')
        cls.country_im = cls.env['ir.model']._get('res.country')
        cls.blend = cls.env['td.bi.dataset'].create({
            'name': 'Blend partners x countries', 'mode': 'blend',
            'visibility': 'global', 'cache_ttl': 0,  # без кешу — кожен прогін перекомпілює
        })
        F = cls.env['td.bi.dataset.field']
        cls.f_pc = F.create({'dataset_id': cls.blend.id, 'name': 'partner_country',
                             'path': 'country_id', 'field_type': 'many2one', 'role': 'dimension'})
        cls.f_pcount = F.create({'dataset_id': cls.blend.id, 'name': 'partner_count',
                                 'path': 'id', 'field_type': 'integer', 'role': 'measure',
                                 'aggregator': 'count'})
        cls.f_ckey = F.create({'dataset_id': cls.blend.id, 'name': 'country_key',
                               'path': 'id', 'field_type': 'integer', 'role': 'dimension'})
        cls.f_ccode = F.create({'dataset_id': cls.blend.id, 'name': 'country_code',
                                'path': 'code', 'field_type': 'char', 'role': 'dimension'})
        cls.join_partner = cls.env['td.bi.dataset.join'].create({
            'dataset_id': cls.blend.id, 'sequence': 0,
            'source_model_id': cls.partner_im.id,
            'included_field_ids': [(6, 0, [cls.f_pc.id, cls.f_pcount.id])],
        })
        cls.join_country = cls.env['td.bi.dataset.join'].create({
            'dataset_id': cls.blend.id, 'sequence': 1,
            'source_model_id': cls.country_im.id, 'join_type': 'left',
            'included_field_ids': [(6, 0, [cls.f_ckey.id, cls.f_ccode.id])],
            'key_ids': [(0, 0, {'left_field': 'partner_country', 'right_field': 'country_key'})],
        })
        cls.measure = cls.env['td.bi.measure'].create({
            'dataset_id': cls.blend.id, 'name': 'Партнерів',
            'field_id': cls.f_pcount.id, 'aggregator': 'count',
        })
        cls.spec = {'groupby': ['country_code'], 'measures': ['Партнерів']}

    # --- AC-38: left зберігає групу без країни, inner — ні (різна к-сть рядків) ---
    def test_blend_left_vs_inner_rowcount(self):
        self.env['res.partner'].create({'name': 'Blend no-country', 'country_id': False})
        res_left = self.blend.run_query(dict(self.spec))
        self.join_country.join_type = 'inner'
        self.blend.invalidate_recordset()
        res_inner = self.blend.run_query(dict(self.spec))
        left_null = any(r.get('country_code') in (None, False) for r in res_left['rows'])
        inner_null = any(r.get('country_code') in (None, False) for r in res_inner['rows'])
        self.assertTrue(left_null, "LEFT JOIN зберігає групу без країни (country_code=NULL).")
        self.assertFalse(inner_null, "INNER JOIN відкидає групу без країни.")
        self.assertEqual(len(res_left['rows']), len(res_inner['rows']) + 1,
                         "Left має рівно на одну (NULL) групу більше за inner.")

    # --- AC-39: RLS у кожному CTE -> обмежений користувач бачить менше (без sudo) ---
    def test_blend_rls_per_user(self):
        ua = self.env.ref('base.ua')
        pair = self.env['res.partner'].create([
            {'name': 'RLS A', 'country_id': ua.id}, {'name': 'RLS B', 'country_id': ua.id}])
        grp = self.env['res.groups'].create({'name': 'BI RLS test grp'})
        self.env['ir.rule'].create({
            'name': 'RLS test only-pair', 'model_id': self.partner_im.id,
            'groups': [(4, grp.id)], 'domain_force': repr([('id', 'in', pair.ids)]),
            'perm_read': True, 'perm_write': False, 'perm_create': False, 'perm_unlink': False,
        })
        user = new_test_user(
            self.env, login='bi_blend_rls', name='Blend RLS',
            groups='base.group_user,td_bi_dashboard.group_bi_user')
        user.write({'group_ids': [(4, grp.id)]})
        res_restricted = self.blend.with_user(user).run_query(dict(self.spec))
        res_admin = self.blend.run_query(dict(self.spec))
        tot_r = sum((r.get('Партнерів') or 0) for r in res_restricted['rows'])
        tot_a = sum((r.get('Партнерів') or 0) for r in res_admin['rows'])
        self.assertEqual(tot_r, 2, "Обмежений користувач бачить лише 2 партнери (RLS у CTE).")
        self.assertGreater(tot_a, tot_r, "Адмін бачить більше — RLS звужує per-user без sudo.")

    # --- AC-40: > 5 таблиць-джерел блокується ---
    def test_blend_max_five_sources(self):
        # Додаємо джерела до 5 (вже 2) — ще 3 ок, 6-те -> помилка.
        for i in range(3):
            self.env['td.bi.dataset.join'].create({
                'dataset_id': self.blend.id, 'sequence': 10 + i,
                'source_model_id': self.country_im.id, 'join_type': 'left',
                'included_field_ids': [(6, 0, [self.f_ckey.id])],
            })
        self.assertEqual(len(self.blend.join_ids), 5)
        with self.assertRaises(ValidationError):
            self.env['td.bi.dataset.join'].create({
                'dataset_id': self.blend.id, 'sequence': 99,
                'source_model_id': self.country_im.id, 'join_type': 'left',
                'included_field_ids': [(6, 0, [self.f_ckey.id])],
            })

    # --- AC-38 (негатив): right/full/cross недоступні ---
    def test_blend_join_type_guard(self):
        with self.assertRaises(ValidationError):
            self.env['td.bi.dataset.join'].create({
                'dataset_id': self.blend.id, 'sequence': 5,
                'source_model_id': self.country_im.id, 'join_type': 'cross',
                'included_field_ids': [(6, 0, [self.f_ckey.id])],
            })

    # --- Контракт виходу збігається з compile_model_query ---
    def test_blend_contract_shape(self):
        res = self.blend.run_query(dict(self.spec))
        self.assertEqual(set(res.keys()), {'rows', 'groupby', 'measures', 'domain'})
        self.assertIsInstance(res['rows'], list)
        self.assertEqual(res['measures'], ['Партнерів'])
        self.assertTrue(all('__extra_domain' in r for r in res['rows']),
                        "Кожен рядок несе __extra_domain (drill-парність).")

    # --- DSL-міра у бленді: арифметика над пред-агрегованими операндами (re-агрегація коректна) ---
    def test_blend_dsl_measure(self):
        recs = self.env['res.partner'].create(
            [{'name': 'DSL co %d' % i, 'is_company': True} for i in range(3)]
            + [{'name': 'DSL p %d' % i, 'is_company': False} for i in range(2)])
        ds = self.env['td.bi.dataset'].create({
            'name': 'Blend DSL ds', 'mode': 'blend', 'visibility': 'global', 'cache_ttl': 0,
            'domain': repr([('id', 'in', recs.ids)])})
        f_isc = self.env['td.bi.dataset.field'].create({
            'dataset_id': ds.id, 'name': 'isc', 'path': 'is_company',
            'field_type': 'boolean', 'role': 'dimension'})
        f_idf = self.env['td.bi.dataset.field'].create({
            'dataset_id': ds.id, 'name': 'idf', 'path': 'id',
            'field_type': 'integer', 'role': 'measure', 'aggregator': 'count'})
        self.env['td.bi.dataset.join'].create({
            'dataset_id': ds.id, 'sequence': 0, 'source_model_id': self.partner_im.id,
            'included_field_ids': [(6, 0, [f_isc.id, f_idf.id])]})
        self.env['td.bi.measure'].create({
            'dataset_id': ds.id, 'name': 'cnt', 'field_id': f_idf.id, 'aggregator': 'count'})
        self.env['td.bi.measure'].create({
            'dataset_id': ds.id, 'name': 'ratio', 'expression': 'COUNT([idf]) * 100'})
        res = ds.run_query({'groupby': ['isc'], 'measures': ['cnt', 'ratio']})
        by = {r.get('isc'): r for r in res['rows']}
        self.assertEqual(by[True].get('cnt'), 3)
        self.assertEqual(by[False].get('cnt'), 2)
        for r in res['rows']:
            self.assertEqual(r.get('ratio'), (r.get('cnt') or 0) * 100,
                             "DSL над блендом: COUNT([idf])*100 == cnt*100 (re-агрегація часткових).")

    # --- DSL-ratio з NULLIF: ділення на нуль -> None (AC-11) ---
    def test_blend_dsl_div_zero(self):
        recs = self.env['res.partner'].create([{'name': 'DZ %d' % i} for i in range(2)])
        ds = self.env['td.bi.dataset'].create({
            'name': 'Blend DSL0 ds', 'mode': 'blend', 'visibility': 'global', 'cache_ttl': 0,
            'domain': repr([('id', 'in', recs.ids)])})
        f_idf = self.env['td.bi.dataset.field'].create({
            'dataset_id': ds.id, 'name': 'idf', 'path': 'id',
            'field_type': 'integer', 'role': 'measure', 'aggregator': 'count'})
        # zero-міра: count поля active=False серед цих (усі active=True) -> 0 через фільтр? Простіше:
        # ділимо на (COUNT - COUNT) = 0 -> NULLIF -> None.
        self.env['td.bi.dataset.join'].create({
            'dataset_id': ds.id, 'sequence': 0, 'source_model_id': self.partner_im.id,
            'included_field_ids': [(6, 0, [f_idf.id])]})
        self.env['td.bi.measure'].create({
            'dataset_id': ds.id, 'name': 'divz',
            'expression': 'COUNT([idf]) / NULLIF(COUNT([idf]) - COUNT([idf]), 0)'})
        res = ds.run_query({'groupby': [], 'measures': ['divz']})
        self.assertIsNone(res['rows'][0].get('divz'), "Ділення на нуль через NULLIF -> None (AC-11).")

    # --- AC-41: предагрегація не множить рядки (унікальний ключ країни) ---
    def test_blend_pre_aggregation_no_explosion(self):
        # Кількість груп <= кількості країн + 1 (NULL) — без декартового множення.
        res = self.blend.run_query(dict(self.spec))
        n_countries = self.env['res.country'].search_count([])
        self.assertLessEqual(len(res['rows']), n_countries + 1,
                             "Предагрегація per-джерело не дає декартового множення рядків.")
