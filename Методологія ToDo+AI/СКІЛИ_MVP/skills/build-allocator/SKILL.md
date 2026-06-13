---
name: build-allocator
description: >
  Split an approved SPEC.md into the two MVP build tracks by classifying every acceptance
  criterion (AC-01) as config (BA sets it up in the Odoo UI), code (a custom td.* module), or
  hybrid. The fork after spec-writer — decides who owns what before either track starts, so
  nothing is built twice or missed. Produces ALLOCATION.md. Triggers on: "розподіли AC",
  "config чи код", "build allocation", "split spec into config and code", "розподіл по
  треках". Requires SPEC.md approved; preserves AC-01 ids.
---

# Odoo Build Allocator — AC → {config | code | hybrid}

Decides, per acceptance criterion, **how** the MVP realizes it: by configuring
standard Odoo through the UI (Track 2) or by writing a custom `td.*` module
(Track 1). Both tracks key off the same `AC-01` ids; this skill is the single
place the routing is decided, so the two tracks never overlap or leave a gap.

> **Position in the chain:** runs once `SPEC.md` is `approved`, right after
> `spec-writer`. Output `ALLOCATION.md` feeds **both** `architecture`
> (Track 1, code ACs) and `config-spec` (Track 2, config ACs).

**Knowledge Base connector (optional, when the KB MCP connector is available):**
- Tools: `list_projects` · `find_documents` · `search_knowledge_base(query, project_ids)` · `get_documents` · `get_document_parts`.
- Rules: always scope with `project_ids`; never copy sensitive data from other clients' scopes (client names, amounts, rates) into deliverables; prefer the freshest version (`modified_at`); connector unavailable / no hits → proceed without it (enhancement, not dependency); the KB holds documents and transcripts only — NO code; KB gives patterns and calibration — content is always authored for the current project.

## Inputs required
- Approved `SPEC.md` (status `approved`; AC-01 ids + Models / «Опис технічної реалізації»).
- Odoo version — from the **project card** (18 / 19), not hardcoded.
- (Optional) install context: edition (Community / Enterprise), Studio availability.

## Pre-flight check (stop if any fails)
- [ ] `SPEC.md` status is `approved`. If not → stop, route to `spec-writer` / `tr-review`.
- [ ] Acceptance criteria use the canonical `AC-01` format. If legacy ids → stop, fix upstream.
- [ ] `Open questions` in SPEC are empty.

## Decision rule — the config/code boundary

Classify each AC by the **cheapest faithful** realization. Default bias: **prefer
configuration** — only route to code what configuration genuinely cannot do.

> 🔎 **KB (#92):** `search_knowledge_base("[function] налаштування чи доробка", project_ids=[analogs])` — for non-obvious ACs: precedents of how the same need was closed in similar projects — by configuration or by a `td.*` module.

| Realize as | When | Examples |
|---|---|---|
| **config** | Achievable with standard Odoo + no-code tools (UI only) | activating an app/module, settings, user groups & access, list/form/report tweaks via Studio, email templates, `base.automation` automated rules, server actions defined in UI, scheduled actions, `ir.config_parameter`, standard integrations toggled in UI |
| **code** | Needs a versioned `td.*` module: Python logic, new model/field with computed/constrained behavior, custom QWeb logic, controller routes, non-trivial onchange/compute, external API client | `_compute_*`, `@api.constrains`, `action_*` with branching logic, custom wizard, REST/XML-RPC client, complex state machine |
| **hybrid** | One AC has both a config part and a code part | a custom field (code) surfaced on a Studio-edited view (config); an automated rule (config) that calls a custom method (code) |

**Studio boundary (project default — confirm per project):** no-code Odoo Studio
customizations (fields/views/automations created through the UI) belong to **config**.
Anything that must ship as Python/XML in a versioned `td.*` module belongs to **code**.
If a Studio change must be reproducible across environments as a module, mark it **hybrid**
and note the split.

**Odoo 19 discipline (Крок 1).** Before routing an AC to **config**, confirm the
capability actually exists in the target Odoo 19 edition. Cite the source
(`довідник §N` / URL). Do not assume a setting exists — an invented config path is
the main failure mode of Track 2. If unsure it is standard → route to **code** or **hybrid**.

> 🔎 **KB (#93):** `search_knowledge_base("[feature] Odoo 19 налаштування Studio", project_ids=[analogs])` — confirm the capability really exists via ТР and config documents of Odoo 19 projects; the official docs remain the primary source — the KB is real-world evidence.

## Process

### 1. Enumerate every AC
List all `AC-01`, `AC-02`, … from `SPEC.md`. Every AC must get exactly one row —
no AC unrouted, none in two rows.

### 2. Classify each AC
Apply the decision rule. For `hybrid`, split the AC into a **config slice** and a
**code slice** in the Notes column (both keep the same `AC-NN` id — one namespace).

### 3. Cross-check against SPEC Models

> 🔎 **KB (#94):** `search_knowledge_base("гібрид config code розподіл AC", project_ids=[analogs])` — how hybrid (config + code) ACs were split in analogous projects.

Each `td.*` model / custom field in SPEC «Models» must be claimed by at least one
`code` or `hybrid` AC. A custom model with no code/hybrid AC → flag (drift between
SPEC tech-design and the ACs).

### 4. Fill `ALLOCATION.md`
Use the template in `references/allocation-template.md`.

## Output — `ALLOCATION.md`

```markdown
# Build Allocation — {module} ({project})
Source: SPEC.md v{version} (approved) · Odoo {version} · {today}

| AC | Track | Realization summary | Odoo 19 source (config) | Notes / hybrid split |
|----|-------|----------------------|-------------------------|----------------------|
| AC-01 | config | Activate Sales app + enable «Маржа» | Sales ▸ Settings (§…/URL) | — |
| AC-02 | code   | `_compute_td_margin` on `td.sale.line` | — | custom compute |
| AC-03 | hybrid | Automated rule (config) → custom `action_td_notify` (code) | base.automation (§…) | config: rule; code: method |

## Track 1 (code) — AC list
AC-02, AC-03(code slice)

## Track 2 (config) — AC list
AC-01, AC-03(config slice)

## Coverage check
- [ ] Every AC in SPEC appears exactly once
- [ ] Every custom td.* model/field in SPEC is claimed by a code/hybrid AC
- [ ] Every config AC cites an Odoo 19 source
```

## Hand-off
> ALLOCATION.md ready. Track 1 (code) → `architecture` for its ACs.
> Track 2 (config) → `config-spec` for its ACs. Hybrid ACs go to **both**,
> each owning its slice.

## DO / DO NOT
**DO**
- Route every AC exactly once; prefer config unless code is genuinely required.
- Verify each config route against real Odoo 19 capability and cite the source.
- Keep `AC-01` ids intact; split hybrids by slice, not by renumbering.

**DO NOT**
- Author new requirements or ACs (that is the upstream tr-* chain).
- Invent Odoo settings/menus to justify a config route — when unsure, route to code/hybrid.
- Leave an AC unrouted or routed to two tracks (except an explicit hybrid split).
- Decide master-data import here — that is the shared `t-masterdata` node, not an AC track.

## Templates reference
- `references/allocation-template.md` — canonical ALLOCATION.md structure.
