---
name: odoo-scaffolding
description: >
  Generate the complete Odoo module file skeleton from SPEC.md and
  ARCHITECTURE.md. Use this skill when both documents exist and are approved,
  and the developer is ready to generate all module files before writing
  business logic. Triggers on: "scaffold the module", "generate module files",
  "create the skeleton", "build the module structure", "generate boilerplate",
  "create module from spec". Always requires both SPEC.md and ARCHITECTURE.md
  to be present and approved before running.
---

# Odoo Scaffolding Skill

Generates every file of the module skeleton. Output is production-ready
boilerplate with `# TODO: AC-XX` markers where business logic will go.
No logic is implemented here — that is the code-dev skill's job.

## Pre-flight check

Required before generating any file:
- [ ] `SPEC.md` exists and status = `approved`
- [ ] `ARCHITECTURE.md` exists
- [ ] No open technical decisions in ARCHITECTURE.md
- [ ] Odoo version confirmed

## ToDo conventions (обов'язково)

- **Module name:** `<project>_<area>` (e.g. `olimpius_delivery`). Read `{module}` below as this name.
- **Models:** `td.*` (`td.{area}.{entity}`); field prefix `td_*`; human record-name mask `<Проект>: …`.
- **Version:** take the Odoo series + module version from the **project card** / SPEC.md — do NOT hardcode. 5-segment `{series}.{major}.{minor}.{bugfix}` (e.g. `19.0.1.0.0`).
- **AC markers:** use the canonical `AC-01` id exactly as in SPEC.md.

## File generation order

Generate files in this exact order (dependencies first):

1. `__manifest__.py`
2. `security/ir.model.access.csv`
3. `security/{module}_security.xml` (groups + record rules)
4. `models/__init__.py`
5. `models/{model}.py` (one per model, fields only)
6. `__init__.py` (imports models)
7. `views/{model}_views.xml` (one per model)
8. `views/{model}_menus.xml`
9. `data/{module}_data.xml` (if needed)
10. `wizard/` files (if in spec)
11. `controllers/` files (if in spec)
12. `report/` files (if in spec)

## Templates per file type

### `__manifest__.py`
```python
# -*- coding: utf-8 -*-
{
    'name': '{Human Readable Name}',
    'version': '{version}',  # 5-сегментна з SPEC.md / картки проекту (напр. 19.0.1.0.0) — НЕ хардкодити
    'category': '{Category}',
    'summary': '{One-line description from SPEC.md business purpose}',
    'description': """
{Business purpose from SPEC.md — first paragraph}
    """,
    'author': 'ToDo',
    'website': 'https://todo.ltd',
    'license': 'LGPL-3',
    'depends': [
        # From ARCHITECTURE.md dependencies section
    ],
    'data': [
        'security/{module}_security.xml',
        'security/ir.model.access.csv',
        'views/{model}_views.xml',
        'views/{model}_menus.xml',
        # data/ files before views/ if they define referenced records
    ],
    'demo': [
        'demo/{module}_demo.xml',
    ],
    'installable': True,
    'application': {True if top-level app, False otherwise},
    'auto_install': False,
}
```

### `models/{model}.py`
```python
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class {ClassName}(models.Model):
    _name = '{technical_name}'
    _description = '{_description from SPEC.md}'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    # ── Identity ──────────────────────────────────────────────────
    name = fields.Char(
        string='Name',
        required=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)

    # ── State ─────────────────────────────────────────────────────
    state = fields.Selection([
        # From SPEC.md state machine
    ], string='Status', default='draft', required=True, tracking=True)

    # ── Fields from SPEC.md ───────────────────────────────────────
    # {Generate one field per entry in the SPEC.md model table}

    # ── SQL constraints ───────────────────────────────────────────
    _sql_constraints = [
        # From SPEC.md constraints
    ]

    # ── Compute methods ───────────────────────────────────────────
    # TODO: AC-XX — implement {computed_field_name}
    # @api.depends('{dependency}')
    # def _compute_{field}(self):
    #     pass

    # ── Action methods ────────────────────────────────────────────
    def action_confirm(self):
        """Confirm the record. AC-XX"""
        # TODO: AC-XX — implement confirmation logic
        self.write({'state': 'confirmed'})

    # ── CRUD overrides ────────────────────────────────────────────
    # Only include if ARCHITECTURE.md specifies override is needed
    # @api.model_create_multi  # Required for Odoo 17+
    # def create(self, vals_list):
    #     # TODO: AC-XX
    #     return super().create(vals_list)
```

### `views/{model}_views.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <!-- Form view -->
    <record id="view_{model}_form" model="ir.ui.view">
        <field name="name">{module}.{model}.form</field>
        <field name="model">{technical_name}</field>
        <field name="arch" type="xml">
            <form>
                <header>
                    <!-- State buttons from SPEC.md state machine -->
                    <button name="action_confirm"
                            string="Confirm"
                            type="object"
                            class="oe_highlight"
                            invisible="state != 'draft'"/>
                    <field name="state" widget="statusbar"
                           statusbar_visible="draft,confirmed,done"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <h1>
                            <field name="name" placeholder="Name..."/>
                        </h1>
                    </div>
                    <group>
                        <group>
                            <!-- Fields from SPEC.md -->
                        </group>
                        <group>
                            <!-- Fields from SPEC.md -->
                        </group>
                    </group>
                    <notebook>
                        <page string="Notes">
                            <field name="note" placeholder="Internal notes..."/>
                        </page>
                    </notebook>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_follower_ids"/>
                    <field name="activity_ids"/>
                    <field name="message_ids"/>
                </div>
            </form>
        </field>
    </record>

    <!-- List view -->
    <record id="view_{model}_list" model="ir.ui.view">
        <field name="name">{module}.{model}.list</field>
        <field name="model">{technical_name}</field>
        <field name="arch" type="xml">
            <list>
                <field name="name"/>
                <!-- Key fields from SPEC.md -->
                <field name="state" widget="badge"
                       decoration-success="state == 'done'"
                       decoration-warning="state == 'confirmed'"
                       decoration-muted="state == 'cancelled'"/>
            </list>
        </field>
    </record>

    <!-- Search view -->
    <record id="view_{model}_search" model="ir.ui.view">
        <field name="name">{module}.{model}.search</field>
        <field name="model">{technical_name}</field>
        <field name="arch" type="xml">
            <search>
                <field name="name"/>
                <filter string="Active" name="active" domain="[('active', '=', True)]"/>
                <group expand="0" string="Group By">
                    <filter string="Status" name="group_state"
                            context="{'group_by': 'state'}"/>
                </group>
            </search>
        </field>
    </record>

    <!-- Action -->
    <record id="action_{model}" model="ir.actions.act_window">
        <field name="name">{Human Name}</field>
        <field name="res_model">{technical_name}</field>
        <field name="view_mode">list,form</field>
        <field name="search_view_id" ref="view_{model}_search"/>
        <field name="context">{}</field>
        <field name="help" type="html">
            <p class="o_view_nocontent_smiling_face">
                Create your first {human name}
            </p>
        </field>
    </record>

</odoo>
```

### `security/ir.model.access.csv`
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_{model}_user,{module}.{model} user,model_{model_underscore},base.group_user,1,0,0,0
access_{model}_manager,{module}.{model} manager,model_{model_underscore},{module}.group_{module}_manager,1,1,1,1
```

### `security/{module}_security.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data>

        <!-- Security groups -->
        <record id="module_category_{module}" model="ir.module.category">
            <field name="name">{Human Module Name}</field>
            <field name="sequence">100</field>
        </record>

        <record id="group_{module}_user" model="res.groups">
            <field name="name">User</field>
            <field name="category_id" ref="module_category_{module}"/>
            <field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
        </record>

        <record id="group_{module}_manager" model="res.groups">
            <field name="name">Manager</field>
            <field name="category_id" ref="module_category_{module}"/>
            <field name="implied_ids" eval="[(4, ref('group_{module}_user'))]"/>
        </record>

        <!-- Record rules (multi-company) -->
        <record id="rule_{model}_company" model="ir.rule">
            <field name="name">{ModelName}: company rule</field>
            <field name="model_id" ref="model_{model_underscore}"/>
            <field name="domain_force">
                ['|', ('company_id', '=', False),
                      ('company_id', 'in', company_ids)]
            </field>
        </record>

    </data>
</odoo>
```

## TODO marker format

Every unimplemented method must have a marker linking to the acceptance criterion,
using the **exact AC id from SPEC.md** (canonical `AC-01` form):

```python
# TODO: AC-03 — validate that partner_id has a valid email before confirming
# TODO: AC-07 — create stock.move when state → done
```

This allows the code-dev skill to find and implement each criterion by AC number.

## Post-scaffold checklist

After generating all files:
- [ ] All models from SPEC.md have a corresponding `.py` file
- [ ] All models have an entry in `ir.model.access.csv`
- [ ] `__manifest__.py` `data` list includes all generated XML files in dependency order
- [ ] Every acceptance criterion from SPEC.md has at least one `# TODO: AC-XX` marker
- [ ] No business logic implemented (only field definitions and stubs)
- [ ] Module installs without error on target Odoo version (developer to verify)

## Version-specific scaffold adjustments

### Odoo 17+
- Add `@api.model_create_multi` decorator on every `create` override
- Use `invisible=` attribute syntax (not `attrs=` which is deprecated)
- Use `domain=` attribute directly (not inside `attrs=`)

### Odoo 18+
- All JS components must be OWL — do not generate legacy JS
- `fields.Html` — add `sanitize=True` explicitly

### Odoo 19+
- Multi-company enforcement is stricter — always generate company record rule
- Check `discuss` vs `mail` dependency carefully per spec

Read `references/odoo-version-notes.md` for the full version diff.
