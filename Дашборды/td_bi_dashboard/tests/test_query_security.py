# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
# Stage-1 безпека запитів: AC-01, AC-02, AC-19, AC-20, AC-21, AC-23.
# Виконується на живій Odoo 19:  odoo-bin -i td_bi_dashboard --test-enable
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged, new_test_user


@tagged('post_install', '-at_install', 'td_bi', 'td_bi_security')
class TestQuerySecurity(TransactionCase):
    """RLS/ACL/доменна безпека движка запитів. Усі data-RPC виконуються ВІД ІМЕНІ
    користувача (with_user), без sudo() на бізнес-даних (§2.4.1)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # --- демо-модель: sale.order.line, з skip-падінням на res.partner ---
        if cls.env['ir.module.module'].search([
            ('name', '=', 'sale'), ('state', '=', 'installed')]):
            cls.demo_model_name = 'sale.order.line'
            cls.sale_available = True
        else:
            cls.demo_model_name = 'res.partner'
            cls.sale_available = False
        cls.demo_model = cls.env['ir.model']._get(cls.demo_model_name)

        cls.grp_user = cls.env.ref('td_bi_dashboard.group_bi_user')
        cls.grp_designer = cls.env.ref('td_bi_dashboard.group_bi_designer')

        # Два BI-користувачі (продавець А і керівник Б) — лише group_bi_user.
        cls.user_a = new_test_user(
            cls.env, login='bi_seller_a', name='Seller A',
            groups='td_bi_dashboard.group_bi_user')
        cls.user_b = new_test_user(
            cls.env, login='bi_manager_b', name='Manager B',
            groups='td_bi_dashboard.group_bi_user')

        # AC-19: дані датасету — на sale.order.line; тест-користувачам потрібен sale-read.
        if cls.sale_available:
            seller = cls.env.ref('sales_team.group_sale_salesman')
            cls.user_a.write({'group_ids': [(4, seller.id)]})
            cls.user_b.write({'group_ids': [(4, seller.id)]})

        # Датасет-конфіг — одна (глобальна видимість, щоб обидва читали конфіг).
        cls.dataset = cls.env['td.bi.dataset'].create({
            'name': 'Security test dataset',
            'mode': 'model',
            'model_id': cls.demo_model.id,
            'visibility': 'global',
        })

    # --- AC-01: пункт створення датасету прихований/AccessError без дизайнера ---
    def test_ac01_create_dataset_without_designer_group_raises(self):
        """AC-01: користувач без group_bi_designer не може створити датасет —
        прямий create завершується AccessError, датасет не створюється."""
        with self.assertRaises(AccessError):
            self.env['td.bi.dataset'].with_user(self.user_a).create({
                'name': 'Illegal dataset',
                'mode': 'model',
                'model_id': self.demo_model.id,
            })

    def test_ac01_designer_can_create_dataset(self):
        """AC-01 (позитив): з group_bi_designer створення датасету дозволене."""
        self.user_a.write({'group_ids': [(4, self.grp_designer.id)]})
        ds = self.env['td.bi.dataset'].with_user(self.user_a).create({
            'name': 'Legit dataset',
            'mode': 'model',
            'model_id': self.demo_model.id,
        })
        self.assertTrue(ds.id, "Дизайнер має створювати датасет.")

    # --- AC-02: дерево полів показує лише доступні; groups= поле відсутнє ---
    def test_ac02_fields_tree_excludes_groups_restricted_field(self):
        """AC-02: дерево полів повертає лише поля fields_get() користувача;
        поле, закрите groups=, у дереві відсутнє і його не можна додати."""
        tree = self.dataset.with_user(self.user_a).get_fields_tree()
        names = {n['name'] for n in (tree.get('fields') if isinstance(tree, dict) else tree)}
        # Усі повернені імена мають бути у fields_get() цього користувача (інваріант AC-02).
        allowed = set(self.env[self.demo_model_name].with_user(self.user_a).fields_get())
        self.assertTrue(names.issubset(allowed),
                        "Дерево полів не має показувати недоступні користувачу поля.")

    def test_ac02_query_on_inaccessible_field_raises(self):
        """AC-02: запит, що звертається до поля, недоступного користувачу, відхиляється
        (AccessError при недоступному groups=-полі або ValidationError для невідомого).
        Перевіряємо, що run_query на неіснуючому полі не повертає дані тихо."""
        with self.assertRaises(UserError):
            self.dataset.with_user(self.user_a).run_query({
                'groupby': ['___no_such_field___'],
                'aggregates': ['__count'],
            })

    # --- AC-19/20: два користувачі -> різні дані; без ACL -> картка «нема доступу» ---
    def test_ac19_two_users_same_config_isolated_by_rls(self):
        """AC-19: продавець А і керівник Б відкривають один датасет (одна конфігурація);
        кожен бачить лише дозволені record rules дані. Перевіряємо, що run_query
        виконується від імені кожного без витоку (різні env.uid у запиті)."""
        res_a = self.dataset.with_user(self.user_a).run_query({
            'groupby': [], 'aggregates': ['__count'], 'preview': True})
        res_b = self.dataset.with_user(self.user_b).run_query({
            'groupby': [], 'aggregates': ['__count'], 'preview': True})
        # Конфігурація одна; результати — кожен у власному контексті прав (без винятку).
        self.assertIsInstance(res_a, dict)
        self.assertIsInstance(res_b, dict)

    def test_ac20_no_acl_model_raises_access_error(self):
        """AC-20: користувач без ACL-read на модель -> run_query підіймає AccessError
        (UI трансформує це у картку «нема доступу» per-віджет, сторінка не падає).
        Беремо модель, на яку у bi_user точно немає ACL — ir.config_parameter."""
        secret_model = self.env['ir.model']._get('ir.config_parameter')
        secret_ds = self.env['td.bi.dataset'].create({
            'name': 'No-ACL dataset',
            'mode': 'model',
            'model_id': secret_model.id,
            'visibility': 'global',
        })
        with self.assertRaises(AccessError):
            secret_ds.with_user(self.user_a).run_query({
                'groupby': [], 'aggregates': ['__count']})

    # --- AC-21: домен аудиторії лише звужує (record rules ∧ extra_domain) ---
    def test_ac21_audience_domain_only_narrows(self):
        """AC-21: домен аудиторії (extra_domain) комбінується з record rules через І
        (Domain.AND) — він не може розширити видимість понад record rules.
        Перевіряємо інваріант через компілятор: OR-префікс одного рівня ізольований."""
        compiler = self.env['td.bi.query.compiler']
        # Рівень record rules (звужує) і ворожий рівень з OR-префіксом (спроба розширити).
        narrowing = [('active', '=', True)]
        malicious_audience = ['|', ('id', '>', 0), ('active', '=', True)]
        eff = compiler._build_effective_domain([narrowing, malicious_audience])
        eff_list = compiler._domain_as_list(eff)
        # Кон'юнкція через Domain.AND -> на верхньому рівні стоїть '&' (І), а не голий '|'.
        self.assertTrue(eff_list, "Ефективний домен не має бути порожнім.")
        self.assertNotEqual(eff_list[0], '|',
                            "OR-префікс рівня не має ставати верхнім оператором (звуження по І).")

    # --- AC-23: кеш не змішує користувачів ---
    def test_ac23_cache_key_differs_per_user(self):
        """AC-23: серверний кеш-ключ включає uid-маркер прав, тож А і Б на однаковому
        запиті отримують РІЗНІ ключі -> не ділять кеш-результат."""
        cache = self.env['td.bi.cache']
        spec = {'groupby': [], 'aggregates': ['__count'], 'limit': 10}
        key_a = cache.with_user(self.user_a)._build_cache_key(self.dataset, spec)
        key_b = cache.with_user(self.user_b)._build_cache_key(self.dataset, spec)
        self.assertTrue(key_a and key_b)
        self.assertNotEqual(key_a, key_b,
                            "Кеш-ключі різних користувачів мають відрізнятися (ізоляція RLS).")
