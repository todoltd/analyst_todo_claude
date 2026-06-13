# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
# Stage-1 DSL-компілятор: AC-09, AC-10, AC-11, AC-13.
# Виконується на живій Odoo 19:  odoo-bin -i td_bi_dashboard --test-enable
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'td_bi', 'td_bi_dsl')
class TestDslCompiler(TransactionCase):
    """Перевіряє контракт DSL (§2.4): whitelist AST, агр./неагр. мікс, невідоме поле,
    ділення на нуль. Валідація йде через td.bi.query.compiler._compile_formula та через
    серверні @api.constrains на збереженні td.bi.measure / td.bi.dataset.field."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.compiler = cls.env['td.bi.query.compiler']
        # Демо-датасет на res.partner (стабільно доступна модель у будь-якій збірці).
        cls.partner_model = cls.env['ir.model']._get('res.partner')
        cls.dataset = cls.env['td.bi.dataset'].create({
            'name': 'DSL test dataset',
            'mode': 'model',
            'model_id': cls.partner_model.id,
        })
        # Поля датасету — псевдоніми, доступні у формулах (джерело істини для AC-10).
        cls.env['td.bi.dataset.field'].create([
            {
                'dataset_id': cls.dataset.id,
                'name': 'price_subtotal',
                'path': 'credit_limit',
                'field_type': 'float',
                'role': 'measure',
            },
            {
                'dataset_id': cls.dataset.id,
                'name': 'qty',
                'path': 'id',
                'field_type': 'integer',
                'role': 'measure',
            },
        ])

    def _make_measure(self, expression):
        """Створює міру з DSL-виразом; повертає recordset (тригерить @api.constrains)."""
        return self.env['td.bi.measure'].create({
            'dataset_id': self.dataset.id,
            'name': 'm_%s' % abs(hash(expression)),
            'expression': expression,
        })

    def test_ac09_mixed_aggregated_and_non_aggregated_raises(self):
        """AC-09: SUM([price_subtotal]) / [qty] — мікс агрегованого і неагрегованого
        операндів -> ValidationError; міра не зберігається."""
        with self.assertRaises(ValidationError):
            self._make_measure('SUM([price_subtotal]) / [qty]')
        # Прямий виклик компілятора також відхиляє (єдиний адаптер валідації).
        field = self.env['td.bi.dataset.field'].new({
            'dataset_id': self.dataset.id,
            'is_formula': True,
            'formula': 'SUM([price_subtotal]) / [qty]',
        })
        with self.assertRaises(ValidationError):
            self.compiler._compile_formula(field)

    def test_ac10_unknown_field_raises_with_suggestion(self):
        """AC-10: невідоме поле [pric] -> ValidationError «невідоме поле» з підказкою
        найближчого імені (price_subtotal); міра не зберігається."""
        with self.assertRaises(ValidationError) as ctx:
            self._make_measure('SUM([pric])')
        message = str(ctx.exception)
        self.assertIn('price_subtotal', message,
                      "Повідомлення про невідоме поле має містити підказку найближчого імені.")

    def test_ac13_dunder_and_import_rejected(self):
        """AC-13: формула з __import__ / будь-яким dunder-іменем -> ValidationError
        (whitelist AST); інцидент логується у td.bi.audit.log; міра не зберігається."""
        for malicious in ("__import__('os')", "SUM([price_subtotal].__class__)",
                          "SUM([__builtins__])"):
            with self.subTest(formula=malicious):
                with self.assertRaises(ValidationError):
                    self._make_measure(malicious)

    def test_ac11_division_compiles_to_nullif(self):
        """AC-11: ділення компілюється у NULLIF(знаменник, 0), тож ділення на нуль дає NULL,
        а не помилку. Перевіряємо скомпільований SQL-вираз ratio-міри."""
        compiled = self.compiler._compile_formula(self.env['td.bi.measure'].new({
            'dataset_id': self.dataset.id,
            'name': 'ratio',
            'expression': 'SUM([price_subtotal]) / SUM([qty])',
        }))
        self.assertTrue(compiled, "Валідна ratio-формула має скомпілюватись.")
        self.assertIn('NULLIF', compiled.upper(),
                      "Ділення має використовувати NULLIF(знаменник, 0) для безпеки від /0.")

    def test_ac09_valid_aggregate_ratio_saves(self):
        """AC-08/AC-09 (позитив): SUM/SUM — обидва операнди агреговані, міра зберігається."""
        measure = self._make_measure('SUM([price_subtotal]) / SUM([qty])')
        self.assertTrue(measure.id, "Коректна агрегатна ratio-міра має зберігатись.")
