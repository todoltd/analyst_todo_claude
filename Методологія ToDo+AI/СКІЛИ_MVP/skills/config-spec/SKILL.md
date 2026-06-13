---
name: config-spec
description: >
  Build CONFIG.md — the configuration spec (DOC-2) the BA executes in the Odoo UI for Track 2.
  Projects the config-allocated AC-01 from an approved SPEC.md into a per-area, AC-traced
  setup blueprint: modules, settings, access, automations, Studio views, reports, email,
  integrations, business rules. Track 2's analog of spec-writer + architecture; projects
  approved requirements, never authors them. Triggers on: "config spec", "специфікація
  конфігурації", "що налаштувати в Odoo", "DOC-2", "build CONFIG.md". Requires SPEC.md
  approved + ALLOCATION.md; each item cites an Odoo 19 source.
---

# Odoo Config-Spec — SPEC.md → CONFIG.md (DOC-2)

Projects the **config-allocated** acceptance criteria into `CONFIG.md`: a
deterministic, area-by-area description of how to set the MVP up in standard
Odoo 19 through the UI. It is the configuration counterpart of `SPEC.md` +
`ARCHITECTURE.md` — the BA configures *from it*, and `config-review` checks
*against it*. Without it, Track 2 has no traceable, verifiable target.

> **Position in the chain:** runs after `build-allocator`, on the ACs routed
> to **config** / **hybrid (config slice)**. Output `CONFIG.md` feeds
> `config-runbook` (BA execution) and `config-review` (gate).

**Knowledge Base connector (optional, when the KB MCP connector is available):**
- Tools: `list_projects` · `find_documents` · `search_knowledge_base(query, project_ids)` · `get_documents` · `get_document_parts`.
- Rules: always scope with `project_ids`; never copy sensitive data from other clients' scopes (client names, amounts, rates) into deliverables; prefer the freshest version (`modified_at`); connector unavailable / no hits → proceed without it (enhancement, not dependency); the KB holds documents and transcripts only — NO code; KB gives patterns and calibration — content is always authored for the current project.

## Inputs required
- Approved `SPEC.md` (AC-01 + Models / business logic).
- `ALLOCATION.md` (from `build-allocator`) — which ACs are config / hybrid.
- Odoo version + edition (Community / Enterprise) — from the **project card**.

## Pre-flight check (stop if any fails)
- [ ] `SPEC.md` status is `approved`. If not → stop, route to `spec-writer`.
- [ ] `ALLOCATION.md` exists and lists the config ACs. If not → stop, run `build-allocator`.
- [ ] AC ids are canonical `AC-01`. Do not renumber.

## Hard rule — project, do not invent

Everything in `CONFIG.md` must trace to a **config-allocated AC** and to a **real
Odoo 19 capability**. Two non-negotiables:

1. **AC trace.** Every config item carries the `AC-NN` id(s) it satisfies — the
   Track 2 mirror of `# TODO: AC-01` in code. One namespace, no renumbering.
2. **Odoo 19 discipline (Крок 1).** Every item cites the official Odoo 19 source
   (`довідник §N` / URL) that confirms the menu/setting/feature exists in the target
   edition. An invented setting path is the main failure mode of configuration —
   if you cannot cite it, do not write it: send it back to `build-allocator`
   as a possible **code** AC, or list it under Open questions.

Keep all human-readable text **Ukrainian** (the BA executes it); keep `AC-NN`,
technical names, and Odoo menu paths exact.

> 🔎 **KB (#95):** `search_knowledge_base("[setting] меню шлях Odoo 19", project_ids=[analogs])` — verify menu/setting paths against real config descriptions and training materials of Odoo 19 projects in the KB.

## Process — fill `CONFIG.md` by area

Use `references/config-template.md`. Only include areas that have config ACs;
mark empty areas `None`. For each item: **what to set → exact UI path → expected
result → `[AC-NN]` → source.**

> 🔎 **KB (#96):** `search_knowledge_base("[area] налаштування таблиця", project_ids=[analogs])` — real settings tables of similar implementations (same module mix) — a ready structure of values per area.

### 1. Header & meta
- `Status`: **approved** (inherited from the approved ТР/SPEC — §8, no AI self-approval).
- `Odoo version` + edition from the project card; `Source: SPEC.md v{version}`.

### 2. Apps & modules
Which standard apps/modules to install/activate, with dependency order. Each `[AC-NN]`.

### 3. Settings
Per app, the Settings-page toggles/values to set (e.g. Sales ▸ Settings ▸ …). Exact path + value.

### 4. Users, groups & access
Standard groups to assign, record rules available out-of-the-box, multi-company
visibility. (Custom groups defined by a `td.*` module are **code** — reference, don't redefine.)

### 5. Workflow automation (no-code)
`base.automation` automated rules, UI server actions, scheduled actions: trigger,
condition, action, `[AC-NN]`. (Logic requiring Python → code/hybrid.)

### 6. Views & forms (Studio)
List/form/kanban/search tweaks done via Studio: which view, what change, `[AC-NN]`.
Note Studio (Enterprise) vs Community limitation per item.

### 7. Reports
Standard or Studio-built reports, layout, filters, `[AC-NN]`.

### 8. Email & templates
`mail.template` records to configure, triggers, recipients, `[AC-NN]`.

### 9. Integrations (UI-level)
Standard connectors toggled/keyed in UI (payment, accounting localization, etc.),
credentials placeholders, `[AC-NN]`. (Custom API clients → code.)

### 10. Business rules (config-level)
Validations/constraints achievable via Studio constraints / required-field / domain
settings, `[AC-NN]`.

### 11. Hybrid hand-shake
For each hybrid AC: name the **code slice** this config depends on (model/field/method
from SPEC), so config-runbook sequences config after the module is deployed.

> 🔎 **KB (#97):** `search_knowledge_base("hybrid config залежність від модуля", project_ids=[analogs])` — examples of describing the config slice's dependency on the code slice in analogous projects.

### 12. Out of scope & open questions
- `Out of scope`: copy SPEC boundaries relevant to config.
- `Open questions`: any item you could not tie to a real Odoo 19 capability —
  blocks `config-review` until resolved (re-route via allocator or amend ТР).

## Approval gate (inherited, not re-issued)
- `CONFIG.md` `Status` = **approved** because the **ТР/SPEC** was approved by the client.
  AI does not self-approve.
- Confirm before hand-off:
  - [ ] Every config/hybrid-config AC from `ALLOCATION.md` is represented.
  - [ ] Every item has an exact UI path + expected result + `[AC-NN]` + Odoo 19 source.
  - [ ] `Open questions` empty.

## Hand-off
> CONFIG.md built from approved SPEC + ALLOCATION. Next: `config-runbook`
> (turn it into an ordered BA UI runbook + config-log).

## DO / DO NOT
**DO**
- Project only config-allocated ACs; mirror SPEC faithfully into UI setup.
- Cite a real Odoo 19 source for every item; keep `AC-NN` and Ukrainian wording intact.
- Name the code slice each hybrid config depends on.

**DO NOT**
- Author new requirements/ACs, or pull in ACs allocated to code.
- Invent menus/settings — if you can't cite it, route it back to the allocator.
- Re-issue or self-approve the config spec.
- Specify master-data records (products/partners) — that is the shared `t-masterdata` node.

## Templates reference
- `references/config-template.md` — canonical CONFIG.md structure.
