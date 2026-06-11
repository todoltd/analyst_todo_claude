---
name: odoo-reverse-spec
description: >
  Reverse-engineer an existing Odoo module into a structured SPEC.md.
  Use this skill whenever the user wants to document an existing module,
  add features to a module that has no spec yet, or onboard a module into
  the SDD workflow. Triggers on phrases like "generate spec for existing
  module", "document this module", "reverse spec", "spec before adding
  features", or any request involving an existing td_ module without a
  SPEC.md. Always run this before spec-writer when the module already exists.
---

# Odoo Reverse-Spec Skill

Produces a SPEC.md for an existing Odoo module by reading all its source
files. This is always step 1R in the SDD workflow — run before writing
any new requirements.

## When to use
- Module directory exists but has no SPEC.md
- Developer wants to add a new feature to an existing module
- Onboarding a legacy module into the SDD process
- Tech debt audit or knowledge capture

## Inputs required
- Path to the module directory (must contain `__manifest__.py`)
- Target Odoo version (16 / 17 / 18 / 19) — infer from manifest if not given

## Step-by-step process

### 1. Collect all source files
Read in this order:
1. `__manifest__.py` — name, version, dependencies, category
2. `models/*.py` — all model definitions
3. `views/*.xml` — menus, views, actions
4. `data/*.xml`, `data/*.csv` — config records, demo data
5. `security/ir.model.access.csv` + `security/*.xml` — access rules
6. `controllers/*.py` — HTTP routes
7. `wizard/*.py` + wizard views — transient models
8. `report/*.py` + report templates — QWeb reports
9. `static/src/` — JS/OWL components (brief summary only)
10. Any `README.md` or `README.rst` already present

> Read the module files from the path given by the user (the connected folder in Cowork).
> If the module is large (>50 files), focus on models and views first,
> then skim the rest for patterns.

### 2. Extract facts — do not invent

For each model found:
- Class name, `_name`, `_inherit`, `_description`
- Every field: name, type, `string`, `required`, `readonly`, `compute`,
  `relation`, `domain`, `default`
- Key methods: `@api.depends`, `@api.onchange`, `@api.constrains`,
  `action_*`, `_compute_*`, `_inverse_*`
- SQL constraints

For views:
- Menu path (full, from root)
- View types present (form / list / kanban / pivot / graph / calendar)
- Inherited views (`inherit_id`)
- Access groups shown in the view

For business logic:
- Automation rules (`base.automation` records in data files)
- Scheduled actions (cron)
- Email templates, server actions
- Workflow state fields (selection fields named `state`)

For integrations:
- `requests` imports → external API calls
- IAP service calls
- Webhook listeners in controllers

### 3. Write the SPEC.md

Use the canonical template below. Fill every section honestly.
If information is missing from the code, write `# TODO: verify` — do not guess.

**Version tracking rule for reverse-spec:** Read the `version` key from `__manifest__.py`.
Set `{current_manifest_version}` to that exact value everywhere in the template. This marks
all existing objects as having been present since the version currently in the manifest.
Future spec-writer runs will set a higher version only on newly added objects.

The version follows the five-segment manifest convention:
`{odoo_version}.{odoo_subversion}.{module_major}.{module_minor}.{bugfix}` — e.g. `18.0.1.0.0`.

```markdown
# Module: {module_technical_name}

## Status
reverse-spec-draft

## Version history
| Date | Author | Change |
|------|--------|--------|
| {today} | reverse-spec AI | Initial reverse-spec from source |

## Odoo version
{16 / 17 / 18 / 19}

## Business purpose
{2–4 sentences: what real-world business problem this solves,
 inferred from model names, field names, and menu paths}

## User stories
{Inferred from views and access groups — as a [group], I can [action]}

## Models

### {ModelName} (`{_name}`)
Inherits: `{_inherit}` (if any)
Since: `{current_manifest_version}`

| Field | Type | Required | Since | Description |
|-------|------|----------|-------|-------------|
| {field_name} | {type} | {yes/no} | {current_manifest_version} | {string or inferred purpose} |

**Key computed fields:**
- `{field}` (since `{current_manifest_version}`): depends on `{deps}` — {brief description}

**Constraints:**
- {SQL or Python constraint description}

**Key methods:**
| Method | Trigger | Since | Description |
|--------|---------|-------|-------------|
| `{method_name}` | {trigger} | {current_manifest_version} | {purpose} |

---

## Views & menus

| Menu path | View type | Access group | Since |
|-----------|-----------|--------------|-------|
| {full menu path} | {type} | {group} | {current_manifest_version} |

## Business logic

### {Workflow name or state machine name}
{Description of the workflow, states, and transitions}

### Automation rules
{List of `base.automation` records found}

### Scheduled actions
{List of cron jobs with their intervals}

## External integrations
{List any HTTP calls, IAP, webhooks — or "None identified"}

## Configuration
{`ir.config_parameter` keys used, or "None identified"}

## Security
| Model | Group | Read | Write | Create | Delete | Since |
|-------|-------|------|-------|--------|--------|-------|
| {model} | {group} | {✓/✗} | {✓/✗} | {✓/✗} | {✓/✗} | {current_manifest_version} |

## Reports
{List of QWeb reports with their paper formats}

## Known limitations / tech debt
{Patterns that suggest issues: missing access rules, deprecated API usage,
 missing `_description`, hardcoded company_id, etc.}

## Open questions
{Things that could not be determined from code alone — mark these for
 human review before writing new requirements}
```

### 4. Save and confirm

- Write output to `{module_dir}/SPEC.md`
- Tell the developer: how many models were found, how many open questions
  remain, and what to review before adding new requirements
- Remind them: **do not write new requirements until a human has reviewed
  and approved this reverse-spec**

## Odoo version notes
Read `references/odoo-version-notes.md` for API differences between
versions 16 / 17 / 18 / 19 that affect how you interpret the source.

## Quality checks before saving
- [ ] Every model in `models/` is documented
- [ ] No invented fields (only what is in code)
- [ ] All `# TODO: verify` items are listed in Open questions
- [ ] Business purpose is plausible given the model/view names
- [ ] Odoo version is set correctly
- [ ] Every model has a `Since:` line set to the manifest version
- [ ] Every field, computed field, method, view row, and security row has a `Since` column populated with the manifest version
