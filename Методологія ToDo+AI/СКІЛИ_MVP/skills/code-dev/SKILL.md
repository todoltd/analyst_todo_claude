---
name: code-dev
description: >
  Implement a specific acceptance criterion from SPEC.md in an Odoo module.
  Use this skill for any implementation task: writing model methods, business
  logic, view improvements, wizard logic, controller routes, or computed fields.
  Triggers on: "implement AC-XX", "write the logic for", "code the feature",
  "implement acceptance criterion", "write this method", "add this field logic",
  "develop the {feature} functionality". Always requires SPEC.md, ARCHITECTURE.md,
  and the scaffold to exist. Never modifies model fields without first updating
  SPEC.md.
---

# Odoo Code-Dev Skill

Implements one acceptance criterion at a time. Spec-locked: no code
outside the spec scope is written. Every change is traceable to an AC number.

## Pre-flight check

Before writing any code:
- [ ] SPEC.md status = `approved`
- [ ] Scaffolding complete (files exist)
- [ ] Target AC id provided in canonical `AC-01` form (e.g. `AC-03`)
- [ ] Current branch matches `feat/{module}-{erp_task_id}-ac{nn}` (module = `<project>_<area>`; `erp_task_id` = «Номер запиту» з ТР)

## ToDo conventions
- Models `td.*`; module `<project>_<area>`; field prefix `td_*`; human record-name mask `<Проект>: …`.
- AC ids are the canonical `AC-01` from SPEC.md — never invent or renumber them.

## Process per acceptance criterion

### 1. Read the AC and its user story

From SPEC.md, find:
- The AC text: `AC-XX [US-XX]: Given ..., when ..., then ...`
- The user story it belongs to
- Any related ACs that share state or data

### 2. Find the TODO marker

In the scaffolded files, locate `# TODO: AC-XX` — this is where the
implementation goes. If no marker exists, check ARCHITECTURE.md traceability
table for where this AC should be implemented.

### 3. Implement — Odoo conventions

#### Model methods
```python
def action_confirm(self):
    """
    Confirm the record.
    AC-03: Given a draft record with a valid partner,
           when the user clicks Confirm,
           then state → confirmed and a chatter message is posted.
    """
    for record in self:
        if not record.partner_id:
            raise UserError(_('A partner is required before confirming.'))
        record.write({'state': 'confirmed'})
        record.message_post(
            body=_('Record confirmed.'),
            subtype_xmlid='mail.mt_note',
        )
```

#### Computed fields
```python
@api.depends('line_ids.price_subtotal')
def _compute_amount_total(self):
    """
    AC-05: Total amount computed from lines.
    """
    for record in self:
        record.amount_total = sum(record.line_ids.mapped('price_subtotal'))
```

#### Constraints
```python
@api.constrains('date_start', 'date_end')
def _check_dates(self):
    """AC-06: End date must be after start date."""
    for record in self:
        if record.date_end and record.date_start:
            if record.date_end < record.date_start:
                raise ValidationError(
                    _('End date must be after start date.')
                )
```

#### `create` override (Odoo 17+)
```python
@api.model_create_multi
def create(self, vals_list):
    """AC-08: Auto-generate sequence on create."""
    for vals in vals_list:
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'td.{module}.{model}'
            ) or _('New')
    return super().create(vals_list)
```

#### `write` override
```python
def write(self, vals):
    """AC-09: Log changes to critical fields."""
    tracked_fields = {'partner_id', 'date_start', 'amount_total'}
    if tracked_fields & vals.keys():
        # tracking=True handles chatter — only add custom logic here
        pass
    return super().write(vals)
```

### 4. View updates

When the AC requires a UI change:

```xml
<!-- AC-02: Partner is required on form — show required indicator -->
<field name="partner_id" required="state == 'draft'"/>

<!-- AC-10: Show warning when deadline is overdue -->
<field name="date_end"
       decoration-danger="date_end and date_end &lt; current_date"/>
```

Odoo 17+ syntax (use `invisible=` not `attrs=`):
```xml
<!-- Odoo 17+ -->
<button name="action_confirm"
        string="Confirm"
        type="object"
        invisible="state != 'draft'"/>

<!-- NOT (deprecated in 17+) -->
<!-- <button attrs="{'invisible': [('state', '!=', 'draft')]}"/> -->
```

### 5. Naming conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Method | `snake_case`, verb first | `action_confirm`, `_compute_total` |
| Compute | prefix `_compute_` | `_compute_amount_total` |
| Inverse | prefix `_inverse_` | `_inverse_partner_name` |
| Constraint | prefix `_check_` | `_check_dates` |
| Action button | prefix `action_` | `action_print_report` |
| Private helper | prefix `_` | `_get_default_journal` |
| XML id (view) | `view_{model}_{type}` | `view_td_order_form` |
| XML id (action) | `action_{model}` | `action_td_order` |
| XML id (menu) | `menu_{module}_{item}` | `menu_td_sale_orders` |
| Sequence code | `td.{module}.{model}` | `td.crm.lead` |
| i18n key | `_('English string')` | `_('No partner selected.')` |

### 6. Error messages

Always use `_()` for translatable strings:
```python
# Good
raise UserError(_('A partner is required.'))
raise ValidationError(_('End date (%(end)s) must be after start date (%(start)s).') % {
    'end': record.date_end, 'start': record.date_start
})

# Bad — not translatable
raise UserError('A partner is required.')
```

### 7. Performance rules

Never inside a loop (`for record in self:`):
- `self.env.ref()` calls
- `search()` or `search_count()` without a domain limit
- `mapped()` calls that trigger additional queries

Use instead:
```python
# Prefetch related records before loop
partners = self.mapped('partner_id')
# or use read_group for aggregates
```

### 8. Spec discipline — hard rules

**DO:**
- Implement exactly what the AC says
- Add docstring with AC number and text
- Remove the `# TODO: AC-XX` marker after implementing

**DO NOT:**
- Add fields not in SPEC.md — update spec first, then code
- Implement multiple ACs in one commit
- Add "nice to have" logic not traceable to an AC
- Change `_name` or `_inherit` without an architecture review

### 9. Commit message format

```
feat({module}): implement AC-{nn} — {short description}   # module = <project>_<area>

AC-{nn}: {paste AC text from spec}
Task: {erp_task_id}
```

## Version-specific implementation notes

Read `references/odoo-version-notes.md` for your target version.

Key differences to check:
- `@api.model_create_multi` — required in 17+
- `invisible=` vs `attrs=` — use `invisible=` in 17+, `domain=` directly in 17+
- `fields.Html(sanitize=True)` — explicit in 18+
- `discuss` dependency — check in 19+
