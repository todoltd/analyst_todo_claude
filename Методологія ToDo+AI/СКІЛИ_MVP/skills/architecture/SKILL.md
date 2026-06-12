---
name: architecture
description: >
  Generate or update ARCHITECTURE.md for an Odoo module from an approved
  SPEC.md. Use this skill when SPEC.md status is `approved` and the team
  is ready to define the technical blueprint before scaffolding. Triggers on:
  "generate architecture", "create ARCHITECTURE.md", "technical design",
  "file structure for module", "plan the implementation", "before scaffolding".
  Never run this skill if SPEC.md status is not `approved` — send the developer
  back to spec-writer first.
---

# Odoo Architecture Skill

Translates an approved SPEC.md into a concrete ARCHITECTURE.md that Claude Code
and Cursor can use directly for scaffolding and development.

## Pre-flight check

Before writing anything:
1. Confirm SPEC.md status is `approved` (check the Status field)
2. Confirm Odoo version — load the correct version section from
   `references/odoo-version-notes.md`
3. Confirm no Open questions remain in SPEC.md

If any check fails → stop and tell the developer what needs to be resolved first.

## ToDo conventions (обов'язково)

- **Models:** `td.*` (e.g. `td.{area}.{entity}`) — stay `td.*` even when the module is project-specific.
- **Module name:** `<project>_<area>` (e.g. `olimpius_delivery`), NOT `td_{name}`. Read `{module}` in every tree/template below as `<project>_<area>`.
- **Name mask:** human-facing record names follow `<Проект>: …`.
- **Versions:** Odoo series and 5-segment module version come from the **project card** / SPEC.md — never hardcode.
- **Author:** ToDo / todo.ltd.

## Odoo 19 — обов'язкова звірка з документацією (по кожному пункту дизайну)

Before writing any class/field/view/security design, verify the mechanism against the
official Odoo 19 reference — the same discipline as `tr-odoo-tech-design`:

1. First `references/odoo-version-notes.md` (curated v19 notes).
2. If the point touches a specific standard model/field/method not covered there → open the
   official docs live: `https://www.odoo.com/documentation/19.0/` (developer → reference);
   if the page is JS-rendered, use the `.rst` source
   `https://raw.githubusercontent.com/odoo/documentation/19.0/content/developer/reference/<topic>.rst`.
3. **Cite the source next to the design point**: `(Odoo 19: notes §N)` or `(Odoo 19 docs: <URL>)`.
4. v19 syntax only: `<list>` (not `<tree>`); `invisible/required/readonly` (not `attrs`/`states`);
   `t-out` (not `t-raw`); `aggregator` (not `group_operator`); external API `/json/2` + Bearer.

No access to sources → mark the point "потребує звірки з Odoo 19"; do not pass it off as final.

## Process

### 1. Derive the file structure

From models in SPEC.md, generate the exact directory tree:

```
{module}/                          # <project>_<area>, напр. olimpius_delivery
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── {model_file}.py          # one file per model class
├── views/
│   ├── {model}_views.xml        # form + list per model
│   ├── {model}_menus.xml        # menus and actions
│   └── res_config_settings_views.xml  # if config fields
├── security/
│   ├── ir.model.access.csv
│   └── {module}_security.xml   # groups and record rules
├── data/
│   └── {module}_data.xml       # config records (if any)
├── demo/
│   └── {module}_demo.xml       # demo records (if any)
├── wizard/                      # only if transient models in spec
│   ├── __init__.py
│   └── {wizard_name}.py
├── report/                      # only if reports in spec
│   ├── {report}_report.py
│   └── {report}_report_templates.xml
├── controllers/                 # only if HTTP routes in spec
│   ├── __init__.py
│   └── main.py
└── static/
    └── description/
        └── icon.png
```

Rules:
- One Python file per model class (not one giant `models.py`)
- Views split: one file for views, one for menus/actions
- Never put menus in the same file as views
- Wizard files only created if transient models are in spec

### 2. Design the class structure

For each model in SPEC.md, write the full class skeleton:

```python
class {ClassName}(models.Model):
    _name = '{technical_name}'
    _description = '{description from spec}'
    _inherit = ['{mixins}']
    _order = '{order_field} desc'

    # ── Fields ────────────────────────────────────────────────────
    # [list field names, types, and spec AC references]

    # ── Constraints ───────────────────────────────────────────────
    # [SQL constraints from spec]

    # ── Compute methods ───────────────────────────────────────────
    # [one entry per computed field]

    # ── Action methods ────────────────────────────────────────────
    # [one entry per state transition or button action]

    # ── Override methods ──────────────────────────────────────────
    # [create, write, unlink overrides if needed]
```

### 3. Map acceptance criteria to methods

Every AC from SPEC.md must map to at least one of:
- A model method (business logic)
- A view element (UI constraint)
- A security rule (access control)
- A test case (in testing phase)

Create a traceability table in ARCHITECTURE.md:

| AC | Implementation location | Type |
|----|------------------------|------|
| AC-01 | `TdModel.action_confirm()` | method |
| AC-02 | `views/td_model_views.xml` — `required="1"` on field | view |
| AC-03 | `security/td_module_security.xml` — record rule | security |

### 4. Define data flows

For each workflow in SPEC.md, write the sequence:

```
User clicks [Confirm] button
  → action_confirm() called
    → _check_required_fields() — raises UserError if invalid
    → state = 'confirmed'
    → _send_confirmation_email() — mail template
    → log chatter message
  → view reloads
```

### 5. List all Odoo dependencies

Be explicit about what goes in `depends`:

```python
# Required (always):
'base', 'mail'

# Add based on spec:
# 'sale'        — if using sale.order
# 'account'     — if creating journal entries
# 'stock'       — if using stock.move
# 'purchase'    — if using purchase.order
# 'hr'          — if using hr.employee
# 'project'     — if using project.task
# 'website'     — if HTTP routes in spec
```

Do not add dependencies not justified by the spec.

### 6. Plan migrations (existing module only)

If this is an update to an existing module:

```markdown
## Migration: {old_version} → {new_version}

### Schema changes
| Table | Change | SQL |
|-------|--------|-----|
| td_{model} | ADD COLUMN | `ALTER TABLE td_{model} ADD COLUMN {field} {type}` |

### Data migrations
- [ ] Backfill `{field}` from `{source}`
- [ ] Set default state for existing records

### Migration script location
`migrations/{new_version}/pre-migration.py`
`migrations/{new_version}/post-migration.py`
```

### 7. Odoo.sh considerations

```markdown
## Odoo.sh deployment

### Branch strategy
- Feature branch: `{feature-branch-name}`
- Staging: merge to `staging` branch for integration test
- Production: merge to `main` after staging sign-off

### Build hooks
- No special build hooks required (or: list if needed)

### Required config params
| Key | Description | Default |
|-----|-------------|---------|
| td.{module}.{param} | {description} | {default} |

### Required external config
- {env variable or system parameter if integration present}
```

## Output file template

Write to `{module_dir}/ARCHITECTURE.md`. Structure:

```markdown
# Architecture: {module}   (module = <project>_<area>, models td.*)
Generated from SPEC.md v{version} — {date}

## File structure
{tree}

## Class design
{class skeletons}

## AC traceability
{table}

## Data flows
{sequence descriptions}

## Dependencies
{justified depends list}

## Migration plan (if applicable)
{migration details}

## Odoo.sh considerations
{deployment notes}

## Open technical decisions
{anything not determined by spec — must be resolved before scaffolding}
```

## Version-specific notes
See **«Odoo 19 — обов'язкова звірка»** above: every design point must be verified against
the official Odoo 19 reference and cite its source. Apply the relevant section of
`references/odoo-version-notes.md` before writing class designs.
