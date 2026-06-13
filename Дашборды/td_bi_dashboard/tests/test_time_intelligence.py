# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
# Stage-2 часовий інтелект: порівняння періодів у межах серії (AC-42/AC-44/AC-11/AC-23).
# Виконується на живій Odoo 19:  odoo-bin -u td_bi_dashboard --test-enable
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'td_bi', 'td_bi_ti')
class TestTimeIntelligence(TransactionCase):
    """Порівняння періодів (prev_year/prev_period/custom_shift) як зсув у межах серії за
    виміром-датою: на кожен рядок додаються колонки <value_key>__prior/__delta/__delta_pct.
    Жодного sudo — запит виконується звичайним run_query (формат AC-42)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env['ir.model']._get('res.partner')
        cls.dataset = cls.env['td.bi.dataset'].create({
            'name': 'TI test dataset',
            'mode': 'model',
            'model_id': cls.partner_model.id,
            'visibility': 'global',
            'date_field_default': 'create_date',
        })
        # Вимір-дата (потрібен для часового інтелекту, AC-44) + міра-count за id.
        cls.f_date = cls.env['td.bi.dataset.field'].create({
            'dataset_id': cls.dataset.id, 'name': 'created', 'path': 'create_date',
            'field_type': 'datetime', 'role': 'dimension', 'sequence': 5,
        })
        cls.f_cnt = cls.env['td.bi.dataset.field'].create({
            'dataset_id': cls.dataset.id, 'name': 'cnt', 'path': 'id',
            'field_type': 'integer', 'role': 'measure', 'aggregator': 'count', 'sequence': 10,
        })
        cls.m_yoy = cls.env['td.bi.measure'].create({
            'dataset_id': cls.dataset.id, 'name': 'Contacts YoY',
            'field_id': cls.f_cnt.id, 'aggregator': 'count', 'comparison': 'prev_year',
        })
        cls.m_pop = cls.env['td.bi.measure'].create({
            'dataset_id': cls.dataset.id, 'name': 'Contacts PoP',
            'field_id': cls.f_cnt.id, 'aggregator': 'count', 'comparison': 'prev_period',
        })
        # Детермінований набір контактів із керованим create_date (через SQL — create_date
        # фреймворк проставляє на create; для тесту backdate-имо точно).
        Partner = cls.env['res.partner']
        groups = [
            ('2024-06-15 10:00:00', 2),  # 2024-06: 2
            ('2025-05-15 10:00:00', 3),  # 2025-05: 3
            ('2025-06-15 10:00:00', 5),  # 2025-06: 5  (2025 разом = 8)
        ]
        ids = []
        for when, n in groups:
            recs = Partner.create([{'name': 'TI %s #%d' % (when[:7], i)} for i in range(n)])
            cls.env.cr.execute(
                "UPDATE res_partner SET create_date = %s WHERE id IN %s",
                (when, tuple(recs.ids)),
            )
            ids.extend(recs.ids)
        Partner.browse(ids).invalidate_recordset(['create_date'])
        cls.partner_ids = ids
        # Звузити датасет рівно до тестових контактів -> детерміновані лічильники.
        cls.dataset.domain = repr([('id', 'in', ids)])

    def _rows_by_year(self, measure_name):
        res = self.dataset.run_query({
            'groupby': ['create_date:year'], 'measures': [measure_name], 'preview': True,
        })
        out = {}
        for row in res['rows']:
            gv = row.get('create_date:year')
            year = (gv[1] if isinstance(gv, (list, tuple)) else str(gv)) or ''
            out[str(year)] = row
        return out

    # --- AC-42: prev_year додає колонки prior/delta/delta_pct і рахує дельту правильно ---
    def test_ti_prev_year_adds_prior_and_delta_columns(self):
        rows = self._rows_by_year('Contacts YoY')
        self.assertIn('2024', rows)
        self.assertIn('2025', rows)
        r2025 = rows['2025']
        # value_key простої count-міри за полем id -> 'id:count'.
        self.assertEqual(r2025.get('id:count'), 8, "2025 має 8 контактів (3+5).")
        self.assertEqual(r2025.get('id:count__prior'), 2, "Попередній рік (2024) = 2.")
        self.assertEqual(r2025.get('id:count__delta'), 6, "Дельта = 8 - 2.")
        self.assertAlmostEqual(r2025.get('id:count__delta_pct'), 3.0,
                               msg="(8-2)/2 = 3.0")

    # --- AC-11 родинне: найстаріший період не має попереднього -> None, не помилка ---
    def test_ti_oldest_period_has_null_prior_and_delta(self):
        rows = self._rows_by_year('Contacts YoY')
        r2024 = rows['2024']
        self.assertIsNone(r2024.get('id:count__prior'),
                          "2024 не має 2023 у серії -> prior None.")
        self.assertIsNone(r2024.get('id:count__delta'))
        self.assertIsNone(r2024.get('id:count__delta_pct'),
                          "Без попереднього періоду delta_pct -> None (без ділення).")

    # --- AC-42: prev_period зсуває на 1 одиницю ГРАНУЛЯРНОСТІ (місяць), не на рік ---
    def test_ti_prev_period_shift_uses_granularity_month(self):
        res = self.dataset.run_query({
            'groupby': ['create_date:month'], 'measures': ['Contacts PoP'], 'preview': True,
        })
        by_month = {}
        for row in res['rows']:
            gv = row.get('create_date:month')
            key = gv[0] if isinstance(gv, (list, tuple)) else gv  # iso-початок
            by_month[key] = row
        jun = by_month.get('2025-06-01 00:00:00')
        self.assertIsNotNone(jun, "Має бути група 2025-06.")
        self.assertEqual(jun.get('id:count'), 5, "2025-06 = 5.")
        self.assertEqual(jun.get('id:count__prior'), 3,
                         "Попередній МІСЯЦЬ (2025-05) = 3 (доводить зсув по гранулярності).")
        self.assertEqual(jun.get('id:count__delta'), 2)

    # --- AC-44: часовий інтелект без виміру-дати у датасеті -> ValidationError ---
    def test_ac44_time_intelligence_without_date_dimension_blocked(self):
        ds = self.env['td.bi.dataset'].create({
            'name': 'No-date dataset', 'mode': 'model',
            'model_id': self.partner_model.id, 'visibility': 'global',
        })
        f = self.env['td.bi.dataset.field'].create({
            'dataset_id': ds.id, 'name': 'c', 'path': 'id',
            'field_type': 'integer', 'role': 'measure', 'aggregator': 'count',
        })
        with self.assertRaises(ValidationError):
            self.env['td.bi.measure'].create({
                'dataset_id': ds.id, 'name': 'Bad YoY', 'field_id': f.id,
                'aggregator': 'count', 'comparison': 'prev_year',
            })

    # --- custom_shift без rolling_n невизначений -> ValidationError ---
    def test_custom_shift_requires_rolling_n(self):
        with self.assertRaises(ValidationError):
            self.env['td.bi.measure'].create({
                'dataset_id': self.dataset.id, 'name': 'Bad shift',
                'field_id': self.f_cnt.id, 'aggregator': 'count',
                'comparison': 'custom_shift',  # rolling_n не задано
            })

    # --- Допоміжне: окремий кумулятивний датасет + контакти з керованим create_date ---
    def _cum_dataset(self, ti_mode, name):
        ds = self.env['td.bi.dataset'].create({
            'name': name, 'mode': 'model', 'model_id': self.partner_model.id,
            'visibility': 'global', 'date_field_default': 'create_date',
        })
        self.env['td.bi.dataset.field'].create({
            'dataset_id': ds.id, 'name': 'created', 'path': 'create_date',
            'field_type': 'datetime', 'role': 'dimension',
        })
        fc = self.env['td.bi.dataset.field'].create({
            'dataset_id': ds.id, 'name': 'cnt', 'path': 'id',
            'field_type': 'integer', 'role': 'measure', 'aggregator': 'count',
        })
        m = self.env['td.bi.measure'].create({
            'dataset_id': ds.id, 'name': 'M ' + ti_mode, 'field_id': fc.id,
            'aggregator': 'count', 'time_intelligence': ti_mode,
        })
        return ds, m

    def _partners_dated(self, dated):
        Partner = self.env['res.partner']
        ids = []
        for iso, n in dated:
            recs = Partner.create([{'name': 'C %s #%d' % (iso, i)} for i in range(n)])
            self.env.cr.execute(
                "UPDATE res_partner SET create_date = %s WHERE id IN %s", (iso, tuple(recs.ids)))
            ids.extend(recs.ids)
        Partner.browse(ids).invalidate_recordset(['create_date'])
        return ids

    # --- Кумулятив YTD: запит звужено до поточного року-до-сьогодні ---
    def test_ti_ytd_scopes_to_current_year(self):
        now = fields.Datetime.now()
        jan_this = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        jan_last = jan_this - relativedelta(years=1)
        ds, m = self._cum_dataset('ytd', 'YTD dataset')
        ids = self._partners_dated([
            (fields.Datetime.to_string(jan_this), 4),   # цьогоріч
            (fields.Datetime.to_string(jan_last), 2),   # торік -> поза YTD
        ])
        ds.domain = repr([('id', 'in', ids)])
        res = ds.run_query({'groupby': [], 'measures': [m.name], 'aggregates': ['__count']})
        self.assertEqual(res['rows'][0].get('__count'), 4,
                         "YTD рахує лише поточний рік (4), торішні (2) виключено.")

    # --- Кумулятив MTD: запит звужено до поточного місяця-до-сьогодні ---
    def test_ti_mtd_scopes_to_current_month(self):
        now = fields.Datetime.now()
        first_this = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        first_prev = first_this - relativedelta(months=1)
        ds, m = self._cum_dataset('mtd', 'MTD dataset')
        ids = self._partners_dated([
            (fields.Datetime.to_string(first_this), 2),  # цей місяць
            (fields.Datetime.to_string(first_prev), 3),  # минулий місяць -> поза MTD
        ])
        ds.domain = repr([('id', 'in', ids)])
        res = ds.run_query({'groupby': [], 'measures': [m.name], 'aggregates': ['__count']})
        self.assertEqual(res['rows'][0].get('__count'), 2,
                         "MTD рахує лише поточний місяць (2), минуломісячні (3) виключено.")

    # --- AC-23: ключ кешу враховує конфіг часового інтелекту (база != YoY тієї ж міри) ---
    def test_ac23_cache_key_differs_when_comparison_toggled(self):
        cache = self.env['td.bi.cache']
        spec = {'groupby': ['create_date:year'], 'measures': ['Contacts YoY'], 'limit': 50}
        key_yoy = cache._build_cache_key(self.dataset, dict(spec))
        # Та сама міра/запит, але порівняння вимкнено -> вихід інший -> ключ мусить відрізнятися.
        self.m_yoy.comparison = 'none'
        self.dataset.invalidate_recordset()
        key_base = cache._build_cache_key(self.dataset, dict(spec))
        self.assertNotEqual(key_yoy, key_base,
                            "ti_signature має входити у ключ кешу (база vs YoY тієї ж міри).")
