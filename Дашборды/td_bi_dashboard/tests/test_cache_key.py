# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
# Stage-1 ключ серверного кешу: AC-23 (ключ включає маркер прав/lang/tz/company/version).
# Виконується на живій Odoo 19:  odoo-bin -i td_bi_dashboard --test-enable
from unittest.mock import patch

from odoo.tests import TransactionCase, tagged, new_test_user


@tagged('post_install', '-at_install', 'td_bi', 'td_bi_cache')
class TestCacheKey(TransactionCase):
    """td.bi.cache._build_cache_key: SHA-256 від нормалізованого запиту з маркером прав
    користувача, lang, tz, company_ids і version датасету (§2.4). Гарантує, що кеш не
    змішує результати різних користувачів/контекстів."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cache = cls.env['td.bi.cache']
        cls.partner_model = cls.env['ir.model']._get('res.partner')
        cls.dataset = cls.env['td.bi.dataset'].create({
            'name': 'Cache key dataset',
            'mode': 'model',
            'model_id': cls.partner_model.id,
            'visibility': 'global',
        })
        cls.spec = {'groupby': ['country_id'], 'aggregates': ['__count'], 'limit': 50}
        cls.user_a = new_test_user(
            cls.env, login='cache_user_a', name='Cache A',
            groups='td_bi_dashboard.group_bi_user')
        cls.user_b = new_test_user(
            cls.env, login='cache_user_b', name='Cache B',
            groups='td_bi_dashboard.group_bi_user')

    def test_ac23_key_is_deterministic(self):
        """AC-23: для того самого користувача/запиту/контексту ключ детермінований
        (SHA-256, незалежний від порядку ключів у query_spec)."""
        k1 = self.cache._build_cache_key(self.dataset, dict(self.spec))
        reordered = {'limit': 50, 'aggregates': ['__count'], 'groupby': ['country_id']}
        k2 = self.cache._build_cache_key(self.dataset, reordered)
        self.assertEqual(k1, k2, "Ключ має бути стабільним при перестановці ключів spec.")
        self.assertEqual(len(k1), 64, "Ключ — hex SHA-256 (64 символи).")

    def test_ac23_key_includes_user_perm_marker(self):
        """AC-23: ключ включає маркер прав користувача — два різні користувачі дають
        різні ключі для однакового запиту (кеш не змішує дані)."""
        ka = self.cache.with_user(self.user_a)._build_cache_key(self.dataset, self.spec)
        kb = self.cache.with_user(self.user_b)._build_cache_key(self.dataset, self.spec)
        self.assertNotEqual(ka, kb, "uid-маркер прав має розділяти ключі різних користувачів.")

    def test_ac23_key_includes_lang(self):
        """AC-23: різний lang -> різний ключ (форматування/переклади не змішуються)."""
        k_en = self.cache._build_cache_key(
            self.dataset, self.spec, uid_perm_marker=self.user_a.id, lang='en_US')
        k_uk = self.cache._build_cache_key(
            self.dataset, self.spec, uid_perm_marker=self.user_a.id, lang='uk_UA')
        self.assertNotEqual(k_en, k_uk, "lang має входити у ключ кешу (AC-23).")

    def test_ac23_key_includes_tz(self):
        """AC-23: різний tz -> різний ключ (межі періодів за tz користувача, AC-17)."""
        k1 = self.cache._build_cache_key(
            self.dataset, self.spec, uid_perm_marker=self.user_a.id, tz='Europe/Kyiv')
        k2 = self.cache._build_cache_key(
            self.dataset, self.spec, uid_perm_marker=self.user_a.id, tz='UTC')
        self.assertNotEqual(k1, k2, "tz має входити у ключ кешу (AC-23).")

    def test_ac23_key_includes_company_ids(self):
        """AC-23: різний набір company_ids -> різний ключ (мультикомпанія не змішується)."""
        k1 = self.cache._build_cache_key(
            self.dataset, self.spec, uid_perm_marker=self.user_a.id, company_ids=[1])
        k2 = self.cache._build_cache_key(
            self.dataset, self.spec, uid_perm_marker=self.user_a.id, company_ids=[1, 2])
        self.assertNotEqual(k1, k2, "company_ids має входити у ключ кешу (AC-23).")

    def test_ac23_key_includes_dataset_version(self):
        """AC-23/AC-65: bump version датасету змінює ключ -> застарілий кеш інвалідовано."""
        k_before = self.cache._build_cache_key(
            self.dataset, self.spec, uid_perm_marker=self.user_a.id)
        # Bump версії (елемент ключа кешу).
        self.dataset.validate_integrity()
        self.dataset.invalidate_recordset(['version'])
        k_after = self.cache._build_cache_key(
            self.dataset, self.spec, uid_perm_marker=self.user_a.id)
        self.assertNotEqual(k_before, k_after,
                            "Зміна version датасету має змінювати ключ кешу (інвалідація).")

    def test_ac23_warm_run_query_serves_cache_without_recompiling(self):
        """AC-23: теплий другий run_query повертає кешований payload і НЕ викликає
        компілятор повторно. Доводить, що серверний кеш справді читається і пишеться —
        аліаси _get/_set делегують у get_cached/store (інакше hasattr-guard у run_query
        мовчки вимикав кеш і кожен виклик перекомпільовувався)."""
        spec = {'groupby': [], 'aggregates': ['__count']}
        sentinel = {'rows': [{'__count': 42}], 'groupby': [], 'measures': [], 'domain': []}
        compiler_cls = type(self.env['td.bi.query.compiler'])
        dataset = self.dataset.with_user(self.user_a)
        # Кеш увімкнено політикою датасету (cache_ttl за замовчуванням > 0).
        self.assertTrue(dataset.cache_ttl and dataset.cache_ttl > 0)
        with patch.object(compiler_cls, 'route_query',
                          return_value=dict(sentinel)) as mock_route:
            first = dataset.run_query(dict(spec))   # промах -> компіляція + запис у кеш
            second = dataset.run_query(dict(spec))  # влучання -> з кешу, без компіляції
        self.assertEqual(mock_route.call_count, 1,
                         "Теплий другий run_query має брати результат з кешу, а не перекомпільовувати.")
        self.assertEqual(first, sentinel)
        self.assertEqual(second, sentinel,
                         "Кешований payload має збігатися з початковим результатом.")
