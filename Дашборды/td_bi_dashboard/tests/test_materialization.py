# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
# Stage-2 матеріалізація: RLS-безпека (AC-63) + детектор накриття (AC-62).
# Виконується на живій Odoo 19:  odoo-bin -u td_bi_dashboard --test-enable
from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'td_bi', 'td_bi_mat')
class TestMaterialization(TransactionCase):
    """Матеріалізація створюється лише для RLS-безпечних конфігурацій (вимір-ключі правил
    накриті, AC-63); детектор повертає предагрегат лише за повного накриття вимірів/мір (AC-62)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # res.country — довідник без звужувальних record rules (детермінований RLS-контекст).
        cls.country_im = cls.env['ir.model']._get('res.country')
        cls.ds = cls.env['td.bi.dataset'].create({
            'name': 'Mat dataset', 'mode': 'model', 'model_id': cls.country_im.id,
            'visibility': 'global'})
        cls.compiler = cls.env['td.bi.query.compiler']

    # --- AC-63: record rule з ключем, не накритим вимірами -> create блокується ---
    def test_rls_unsafe_create_blocked(self):
        grp = self.env['res.groups'].create({'name': 'mat rls grp'})
        self.env['ir.rule'].create({
            'name': 'mat rule code', 'model_id': self.country_im.id,
            'groups': [(4, grp.id)], 'domain_force': repr([('code', '!=', False)]),
            'perm_read': True, 'perm_write': False, 'perm_create': False, 'perm_unlink': False})
        with self.assertRaises(UserError):
            self.env['td.bi.materialization'].create({
                'dataset_id': self.ds.id,
                'dimension_paths': ['name'],   # 'code' (ключ правила) відсутній -> небезпечно
                'measure_specs': ['cnt'], 'table_name': 'bi_mat_unsafe'})

    # --- AC-62: детектор повертає предагрегат лише за повного накриття ---
    def test_covering_materialization_detection(self):
        mat = self.env['td.bi.materialization'].create({
            'dataset_id': self.ds.id, 'dimension_paths': ['code', 'name'],
            'measure_specs': ['cnt'], 'table_name': 'bi_mat_test'})
        self.assertTrue(mat.is_rls_safe, "Без звужувальних правил предагрегат RLS-безпечний.")
        mat.last_refresh = fields.Datetime.now()  # позначаємо як побудований/оновлений
        found = self.compiler._find_covering_materialization(
            self.ds, {'groupby': ['code'], 'measures': ['cnt']})
        self.assertEqual(found, mat, "Накритий запит -> знайдено предагрегат.")
        # Вимір поза предагрегатом -> не накрито.
        miss = self.compiler._find_covering_materialization(
            self.ds, {'groupby': ['currency_id'], 'measures': ['cnt']})
        self.assertFalse(miss, "Ненакритий вимір -> предагрегат не повертається.")
        # Без last_refresh -> не кандидат (ще не побудовано).
        mat.last_refresh = False
        none2 = self.compiler._find_covering_materialization(
            self.ds, {'groupby': ['code'], 'measures': ['cnt']})
        self.assertFalse(none2, "Непобудований предагрегат (last_refresh порожній) не обслуговує.")
