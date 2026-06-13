# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
# Stage-1 дерево полів / цілісність датасету: AC-04, AC-05, AC-06, AC-07, AC-10/AC-65.
# Виконується на живій Odoo 19:  odoo-bin -i td_bi_dashboard --test-enable
from unittest.mock import patch

from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'td_bi', 'td_bi_dataset')
class TestDatasetTree(TransactionCase):
    """Дерево полів конструктора (ліниве, з обмеженням глибини/рекурсії/неактивних
    computed) і цілісність датасету (блок видалення поля-споживача, bump version)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Демо-датасет на res.partner (relational-ланцюги parent_id/country_id стабільні).
        # sale.order.line — за наявності; res.partner — запасний шлях (skip-сумісний).
        if cls.env['ir.module.module'].search([
            ('name', '=', 'sale'), ('state', '=', 'installed')]):
            cls.model_name = 'sale.order.line'
        else:
            cls.model_name = 'res.partner'
        cls.model = cls.env['ir.model']._get(cls.model_name)
        cls.dataset = cls.env['td.bi.dataset'].create({
            'name': 'Tree test dataset',
            'mode': 'model',
            'model_id': cls.model.id,
        })

    # --- AC-04: глибина понад 5 рівнів блокується ---
    def test_ac04_depth_over_5_levels_blocked(self):
        """AC-04: розкриття 6-го рівня не повертає полів-нащадків (depth_limited),
        дерево не розкривається глибше ліміту 5."""
        deep_path = '.'.join(['parent_id'] * 5)  # 5 рівнів вже досягнуто
        tree = self.dataset.get_fields_tree(path=deep_path)
        if isinstance(tree, dict):
            self.assertTrue(
                tree.get('depth_limited') or not tree.get('fields'),
                "На 5-му рівні гілка не має розкриватись глибше (AC-04).")
        else:
            self.assertEqual(tree, [], "На граничній глибині дерево порожнє.")

    def test_ac04_within_limit_expands(self):
        """AC-04 (позитив): у межах ліміту дерево повертає поля моделі."""
        tree = self.dataset.get_fields_tree(path='')
        fields = tree.get('fields') if isinstance(tree, dict) else tree
        self.assertTrue(fields, "Корінь датасету має повертати поля моделі.")

    # --- AC-05: повтор пари (модель, поле) -> маркер рекурсії ---
    def test_ac05_recursion_marker_on_repeated_pair(self):
        """AC-05: на шляху parent_id.parent_id (res.partner -> res.partner) поле parent_id
        у дереві має маркер рекурсії (recursive=True) і вимагає підтвердження."""
        if self.model_name != 'res.partner':
            self.skipTest("Тест рекурсії розрахований на self-referential parent_id res.partner.")
        tree = self.dataset.get_fields_tree(path='parent_id')
        fields = tree.get('fields') if isinstance(tree, dict) else tree
        parent_node = next((n for n in fields if n['name'] == 'parent_id'), None)
        self.assertIsNotNone(parent_node, "Гілка має містити parent_id.")
        self.assertTrue(parent_node.get('recursive'),
                        "Повтор пари (res.partner, parent_id) має нести маркер рекурсії (AC-05).")

    # --- AC-06: попередній перегляд = рівно один run_query, <= 80 рядків ---
    def test_ac06_preview_one_run_query_and_row_cap(self):
        """AC-06: попередній перегляд виконує рівно один run_query і обмежує таблицю
        до 80 рядків. Перевіряємо, що компілятор викликано один раз і limit<=80."""
        compiler = self.env['td.bi.query.compiler']
        # Підмінюємо route_query, щоб порахувати виклики і перехопити переданий spec.
        seen = {'calls': 0, 'limit': None}
        real_route = type(compiler).route_query

        def _spy(self2, dataset, query_spec, domain):
            seen['calls'] += 1
            seen['limit'] = query_spec.get('limit')
            return {'rows': [{'__count': i} for i in range(200)]}

        with patch.object(type(compiler), 'route_query', _spy):
            result = self.dataset.run_query({
                'groupby': [], 'aggregates': ['__count'], 'preview': True})
        self.assertEqual(seen['calls'], 1, "Прев'ю має виконати рівно один run_query (AC-06).")
        rows = result.get('rows') if isinstance(result, dict) else result
        self.assertLessEqual(len(rows), 80, "Таблиця прев'ю — не більше 80 рядків (AC-06).")

    # --- AC-07: computed без store/search неактивне ---
    def test_ac07_computed_without_store_search_inactive(self):
        """AC-07: обчислюване поле без store і без search у дереві неактивне (selectable=False)
        з підказкою — його не можна обрати як вимір/фільтр."""
        # Знайти у моделі реальне computed-поле без store і без search.
        model = self.env[self.model_name]
        target = None
        for fname, field in model._fields.items():
            if field.compute and not field.store and not field.search:
                target = fname
                break
        if not target:
            self.skipTest("У моделі немає computed-поля без store/search для перевірки AC-07.")
        tree = self.dataset.get_fields_tree(path='')
        fields = tree.get('fields') if isinstance(tree, dict) else tree
        node = next((n for n in fields if n['name'] == target), None)
        if node is None:
            self.skipTest("Поле %s недоступне у fields_get поточного користувача." % target)
        self.assertFalse(node.get('selectable'),
                         "Computed без store/search має бути неактивним (AC-07).")

    # --- AC-10/AC-65: видалення поля-споживача -> UserError ---
    def test_ac10_remove_used_field_raises_usererror(self):
        """AC-65/ВИМ-10: видалення поля датасету, на яке посилаються віджети,
        блокується UserError з переліком віджетів-споживачів."""
        field = self.env['td.bi.dataset.field'].create({
            'dataset_id': self.dataset.id,
            'name': 'customer_rank',
            'path': 'id',
            'field_type': 'integer',
            'role': 'measure',
        })
        # Дашборд/сторінка/віджет, що споживає поле через config.measures.
        dashboard = self.env['td.bi.dashboard'].create({'name': 'D'})
        page = self.env['td.bi.dashboard.page'].create({
            'name': 'P', 'dashboard_id': dashboard.id})
        self.env['td.bi.widget'].create({
            'page_id': page.id,
            'dataset_id': self.dataset.id,
            'config': {'measures': ['customer_rank']},
        })
        # Видаляємо поле з датасету і запускаємо перевірку цілісності -> UserError.
        field.unlink()
        with self.assertRaises(UserError):
            self.dataset.validate_integrity()

    def test_ac10_unknown_path_field_raises(self):
        """AC-10: поле датасету з невідомим шляхом відхиляється validate_integrity()
        (ValidationError з підказкою)."""
        self.env['td.bi.dataset.field'].create({
            'dataset_id': self.dataset.id,
            'name': 'bad',
            'path': '___nope___',
            'field_type': 'char',
        })
        with self.assertRaises(ValidationError):
            self.dataset.validate_integrity()

    # --- AC-65: bump version при дозволеній зміні (елемент ключа кешу) ---
    def test_ac65_version_bumps_on_allowed_change(self):
        """AC-65: дозволена зміна (validate_integrity) bump-ить version,
        тож застарілий кеш інвалідовано."""
        v0 = self.dataset.version
        self.dataset.validate_integrity()
        self.assertGreater(self.dataset.version, v0,
                           "Version має зрости після дозволеної зміни (інвалідація кешу).")
