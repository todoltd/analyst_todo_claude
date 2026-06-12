---
name: testing
description: >
  Generate Odoo unit and integration tests from SPEC.md acceptance criteria.
  Use this skill when a developer needs to write tests for a module, verify
  that an AC is covered by tests, or create a full test suite before
  deployment. Triggers on: "write tests", "generate test cases", "test this
  module", "create unit tests", "test AC-XX", "test coverage", "write test
  suite", "generate tests from spec". Can also be used to audit existing
  tests against SPEC.md acceptance criteria.
---

# Odoo Testing Skill

Generates tests that are directly traceable to SPEC.md acceptance criteria.
One test method per AC. Tests are the final verification gate before deployment.

## Зв'язок із ТР (ToDo)
These automated tests are the code realization of the ТР's «Тестовий сценарій» /
«Протокол тестування». One test per **canonical `AC-01`** id (method `test_ac01_…`),
so the AC spine stays intact ТР → SPEC → code → tests. The «AC coverage audit»
table below is the acceptance checkpoint for the build.

## Test file location

```
td_{module}/
└── tests/
    ├── __init__.py
    ├── common.py          # shared setup, base class
    ├── test_{model}.py    # one file per model being tested
    └── test_{workflow}.py # one file per major workflow
```

## Base test class (`tests/common.py`)

Always create a shared base class to avoid setup duplication:

```python
# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('td_{module}', 'post_install', '-at_install')
class Td{Module}Common(TransactionCase):
    """
    Shared setup for td_{module} tests.
    Creates minimal records required by multiple test classes.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Company
        cls.company = cls.env.ref('base.main_company')

        # Users — one per access group in SPEC.md
        cls.user_manager = cls.env['res.users'].create({
            'name': 'Test Manager',
            'login': 'test_manager_{module}',
            'groups_id': [(4, cls.env.ref('td_{module}.group_{module}_manager').id)],
        })
        cls.user_basic = cls.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user_{module}',
            'groups_id': [(4, cls.env.ref('base.group_user').id)],
        })

        # Partner
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
            'company_id': cls.company.id,
        })

        # Minimal record in default state
        cls.record = cls.env['td.{module}.{model}'].create({
            'name': 'Test Record',
            'partner_id': cls.partner.id,
            'company_id': cls.company.id,
        })
```

## Test method pattern (one per AC)

```python
# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from .common import Td{Module}Common


@tagged('td_{module}', 'post_install', '-at_install')
class TestTd{Model}(Td{Module}Common):
    """Tests for td.{module}.{model} — covers AC-01 through AC-0N."""

    # ── AC-01 ─────────────────────────────────────────────────────

    def test_ac01_confirm_sets_state(self):
        """
        AC-01 [US-01]: Given a draft record with a valid partner,
        when the user clicks Confirm,
        then state → confirmed.
        """
        self.assertEqual(self.record.state, 'draft')
        self.record.with_user(self.user_manager).action_confirm()
        self.assertEqual(self.record.state, 'confirmed')

    def test_ac01_confirm_posts_chatter(self):
        """
        AC-01 (chatter): Confirming a record posts a message to the chatter.
        """
        self.record.with_user(self.user_manager).action_confirm()
        last_msg = self.record.message_ids[0]
        self.assertIn('confirmed', last_msg.body.lower())

    # ── AC-02 ─────────────────────────────────────────────────────

    def test_ac02_confirm_without_partner_raises(self):
        """
        AC-02 [US-01]: Given a draft record WITHOUT a partner,
        when the user clicks Confirm,
        then a UserError is raised.
        """
        record_no_partner = self.env['td.{module}.{model}'].create({
            'name': 'No Partner',
            'company_id': self.company.id,
        })
        with self.assertRaises(UserError):
            record_no_partner.with_user(self.user_manager).action_confirm()

    # ── AC-03 (validation) ────────────────────────────────────────

    def test_ac03_end_date_before_start_raises(self):
        """
        AC-03 [US-02]: Given date_end < date_start, a ValidationError is raised.
        """
        from datetime import date
        with self.assertRaises(ValidationError):
            self.record.write({
                'date_start': date(2025, 6, 1),
                'date_end': date(2025, 1, 1),
            })

    # ── AC-04 (compute) ───────────────────────────────────────────

    def test_ac04_amount_total_computed_from_lines(self):
        """
        AC-04 [US-03]: Total amount equals sum of line subtotals.
        """
        self.env['td.{module}.{model}.line'].create([
            {'order_id': self.record.id, 'price_subtotal': 100.0},
            {'order_id': self.record.id, 'price_subtotal': 50.0},
        ])
        self.assertAlmostEqual(self.record.amount_total, 150.0)

    # ── AC-05 (access control) ────────────────────────────────────

    def test_ac05_basic_user_cannot_confirm(self):
        """
        AC-05 [US-01]: A user without Manager group cannot confirm.
        """
        from odoo.exceptions import AccessError
        with self.assertRaises(AccessError):
            self.record.with_user(self.user_basic).action_confirm()
```

## Test patterns by AC type

### State transition AC
```python
def test_ac_state_transition(self):
    self.assertEqual(self.record.state, 'draft')
    self.record.action_{transition}()
    self.assertEqual(self.record.state, '{expected_state}')
```

### Validation / constraint AC
```python
def test_ac_constraint_raises(self):
    with self.assertRaises((UserError, ValidationError)):
        self.record.write({'{field}': {invalid_value}})
```

### Compute field AC
```python
def test_ac_compute(self):
    # Set dependencies
    self.record.write({'{dep_field}': {value}})
    # Assert computed result
    self.assertAlmostEqual(self.record.{computed_field}, {expected})
```

### Access control AC
```python
def test_ac_access_denied(self):
    from odoo.exceptions import AccessError
    with self.assertRaises(AccessError):
        self.record.with_user(self.user_basic).{restricted_action}()
```

### Create/sequence AC
```python
def test_ac_sequence_generated(self):
    new_record = self.env['td.{module}.{model}'].create({'name': 'New', ...})
    self.assertNotEqual(new_record.name, 'New')
    self.assertTrue(new_record.name.startswith('{prefix}'))
```

### Multi-company record rule AC
```python
def test_ac_multicompany_rule(self):
    company2 = self.env['res.company'].create({'name': 'Company 2'})
    user_c2 = self.env['res.users'].create({
        'name': 'C2 User', 'login': 'c2_user',
        'company_id': company2.id,
        'company_ids': [(4, company2.id)],
    })
    # Record belongs to company 1 — should not be visible to company 2 user
    records = self.env['td.{module}.{model}'].with_user(user_c2).search([])
    self.assertNotIn(self.record, records)
```

## Running tests

```bash
# Run all tests for the module
./odoo-bin -i td_{module} --test-enable --stop-after-init -d {db}

# Run a specific tag
./odoo-bin --test-tags td_{module} --stop-after-init -d {db}

# Run a specific class
./odoo-bin --test-tags /td_{module}:TestTd{Model} --stop-after-init -d {db}
```

## AC coverage audit

After writing tests, verify every AC is covered:

```markdown
## Test coverage audit

| AC | Test method | Status |
|----|-------------|--------|
| AC-01 | test_ac01_confirm_sets_state | ✓ |
| AC-01 | test_ac01_confirm_posts_chatter | ✓ |
| AC-02 | test_ac02_confirm_without_partner_raises | ✓ |
| AC-03 | test_ac03_end_date_before_start_raises | ✓ |
| AC-04 | test_ac04_amount_total_computed_from_lines | ✓ |
| AC-05 | test_ac05_basic_user_cannot_confirm | ✓ |
```

Every AC must have at least one test. ACs that test a negative case
(error raised) should also have a positive case (happy path).

## Odoo.sh test execution

Odoo.sh runs tests automatically on staging branch push if:
- `--test-enable` is set in the branch config
- The module is listed in `--init` or `--update`

Tag all tests with `post_install` to run after full module installation.
Avoid `at_install` tests for modules with complex dependencies.
