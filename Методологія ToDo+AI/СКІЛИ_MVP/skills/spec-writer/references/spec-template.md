# Module: td_{name}

## Status
<!-- draft | review | approved | superseded -->
draft

## Version history
| Date | Author | Change |
|------|--------|--------|
| YYYY-MM-DD | | Initial spec |

## Odoo version
<!-- 16 / 17 / 18 / 19 -->

## Category
<!-- Technical / Sales / Accounting / Inventory / HR / Project / Website / Other -->

## Business purpose
<!--
2–4 sentences.
What real-world business problem does this module solve?
Who benefits and how?
-->

## User stories

| ID | As a... | I want to... | So that... |
|----|---------|--------------|------------|
| US-01 | | | |

## Acceptance criteria

<!--
Format: AC-XX [US-XX]: Given {precondition}, when {action}, then {result}.
Each criterion must be binary (pass/fail) and independently testable.
-->

- **AC-01** [US-01]: Given ..., when ..., then ...

## Models

### {ModelName} (`td.{module}.{entity}`)
Inherits: `mail.thread`, `mail.activity.mixin`
Since: `{odoo_version}.{odoo_subversion}.1.0.0`

**Fields:**
| Field | Type | Required | Default | Since | Description |
|-------|------|----------|---------|-------|-------------|
| name | Char | Yes | — | {odoo_version}.{odoo_subversion}.1.0.0 | Record name |
| state | Selection | Yes | draft | {odoo_version}.{odoo_subversion}.1.0.0 | Status: draft / confirmed / done / cancelled |

**Selection values for `state`:**
- `draft` — Draft
- `confirmed` — Confirmed
- `done` — Done
- `cancelled` — Cancelled

**Computed fields:**
| Field | Depends on | Stored | Since | Description |
|-------|-----------|--------|-------|-------------|

**SQL constraints:**
```python
_sql_constraints = [
    ('name_uniq', 'unique(name, company_id)', 'Name must be unique per company.'),
]
```

**Key methods:**
| Method | Trigger | Since | Description |
|--------|---------|-------|-------------|
| `action_confirm` | Button | {odoo_version}.{odoo_subversion}.1.0.0 | Transitions state → confirmed |

## Views & menus

| Menu path | View types | Access group | Since |
|-----------|-----------|--------------|-------|
| {App} / {Section} / {Item} | form, list | base.group_user | {odoo_version}.{odoo_subversion}.1.0.0 |

## Business logic

### State machine: {ModelName}
```
draft → confirmed → done
  ↓
cancelled
```

Transitions:
- `draft → confirmed`: `action_confirm()` — validates required fields
- `confirmed → done`: `action_done()` — creates accounting entries
- `any → cancelled`: `action_cancel()` — requires `Inventory / Manager`

### Automation rules
<!-- base.automation records -->
None

### Scheduled actions
<!-- ir.cron records -->
None

## External integrations
<!-- APIs, webhooks, email routes -->
None

## Configuration
<!-- ir.config_parameter keys the module reads or writes -->
None

## Security

| Model | Group | Read | Write | Create | Delete | Since |
|-------|-------|------|-------|--------|--------|-------|
| `td.{module}.{entity}` | `base.group_user` | ✓ | ✗ | ✗ | ✗ | {odoo_version}.{odoo_subversion}.1.0.0 |
| `td.{module}.{entity}` | `{module}.group_manager` | ✓ | ✓ | ✓ | ✓ | {odoo_version}.{odoo_subversion}.1.0.0 |

**Custom groups defined by this module:**
- `{module}.group_manager` — Can create, edit, delete records

## Reports
<!-- QWeb reports -->
None

## Data & demo
<!-- Config records installed by default; demo data -->
None

## Out of scope
<!--
Explicit exclusions. Required to prevent scope creep.
Anything not listed here is assumed in scope.
-->
- 

## Open questions
<!--
Unresolved decisions that block architecture.
Must be empty before status moves to `approved`.
-->
- 

## Dependencies
<!--
Odoo modules this module depends on (beyond base).
-->
```python
'depends': ['base', 'mail'],
```
