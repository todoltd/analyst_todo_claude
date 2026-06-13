---
name: config-runbook
description: >
  Turn CONFIG.md into an ordered, click-by-click runbook the BA follows to configure Odoo
  through the UI, plus a config-log the BA fills as the durable record of what was applied
  (configuration has no git diff, so the log is the evidence). Track 2's execution layer — the
  analog of scaffolding + code-dev. Triggers on: "config runbook", "сценарій налаштування",
  "покрокова інструкція БА", "build config runbook", "config-log". Requires CONFIG.md;
  sequences steps by dependency, each tied to an AC-NN + verification.
---

# Odoo Config-Runbook — CONFIG.md → ordered BA runbook + config-log

Expands `CONFIG.md` (the unordered, area-grouped spec) into an **execution order**
the BA can follow top-to-bottom in the Odoo UI, and a **`config-log`** the BA fills
as they go. The runbook makes configuration *reproducible*; the log makes it
*auditable* — together they give Track 2 the traceability that `git` gives code.

> **Position in the chain:** runs after `config-spec`. Output
> `CONFIG_RUNBOOK.md` + `config-log.md` feeds `config-review` (the gate).

**Knowledge Base connector (optional, when the KB MCP connector is available):**
- Tools: `list_projects` · `find_documents` · `search_knowledge_base(query, project_ids)` · `get_documents` · `get_document_parts`.
- Rules: always scope with `project_ids`; never copy sensitive data from other clients' scopes (client names, amounts, rates) into deliverables; prefer the freshest version (`modified_at`); connector unavailable / no hits → proceed without it (enhancement, not dependency); the KB holds documents and transcripts only — NO code; KB gives patterns and calibration — content is always authored for the current project.

## Inputs required
- `CONFIG.md` (from `config-spec`) — config items with UI paths + `[AC-NN]` + sources.
- For hybrid ACs: confirmation that the **code slice** (its `td.*` module) is **deployed**
  on the target environment (from Track 1 deploy). Config that depends on undeployed code waits.
- Target environment label (dev / staging / prod).

## Pre-flight check (stop if any fails)
- [ ] `CONFIG.md` `Status` = `approved`. If not → stop, route to `config-spec`.
- [ ] Every `CONFIG.md` item has a UI path + expected result + `[AC-NN]`. If gaps → back to `config-spec`.
- [ ] Hybrid dependencies identified (which steps wait for a deployed module).

## Sequencing rule

> 🔎 **KB (#98):** `search_knowledge_base("порядок кроків налаштування впровадження", project_ids=[analogs])` — the real step order from past implementations (Apps → Settings → data → automations) — dependency sequences verified in practice.

Order steps by dependency, not by CONFIG.md area order:

1. **Apps & modules** (install first — everything else depends on them)
2. **Hybrid code modules deployed** (gate: Track 1 deploy done for dependent steps)
3. **Settings** (per app)
4. **Users, groups & access**
5. **Studio views / forms** (need the models/fields present)
6. **Automation, server actions, scheduled actions**
7. **Email templates**
8. **Reports**
9. **Integrations** (credentials last; use placeholders, never real secrets in the runbook)

Within a step group, keep `CONFIG.md` order. Each step stays atomic: one setting,
one verification.

## Process

### 1. Flatten CONFIG.md into ordered steps
Walk `CONFIG.md`; emit one numbered step per config item in the sequence above.
Carry the `[AC-NN]` and Odoo 19 source onto each step.

### 2. Write each step (runbook format)
Each step has: **action** (imperative, exact UI path), **expected result**
(what the BA should see — the per-step verification), `[AC-NN]`, and a **log slot**.

> 🔎 **KB (#99):** `search_knowledge_base("покрокова інструкція налаштування", project_ids=[analogs])` — real step-by-step instructions/training materials from the KB: step wording plus the "what you should see" verification.

```markdown
### Крок {n} — {короткий заголовок}  [AC-NN]
**Дія:** {App} ▸ {Menu} ▸ {…} → {що зробити}.
**Очікуваний результат:** {що БА має побачити / стан, який підтверджує крок}.
**Джерело:** {довідник §N / URL}
**Лог:** ⬜ виконано · значення/нотатка: ________
```

### 3. Build the config-log template
Use `references/config-log-template.md`. The BA fills it during execution: per step
— done/skipped, the actual value set, date, and (where the setting supports it) an
**export reference** (e.g. exported `base.automation` / `mail.template` XML, or the
`ir.config_parameter` key=value) as hard evidence for the gate.

> 🔎 **KB (#100):** `find_documents(name_contains="журнал налаштувань", project_ids=[client, analogs])` — examples of filled config-logs/acts: what counts as sufficient evidence of applied configuration.

### 4. Coverage check
Every config/hybrid-config AC in `CONFIG.md` must appear in at least one runbook step.

## Reproducibility & evidence

- The runbook is the **reproducible script** for re-applying config on another
  environment (dev → prod). Keep steps environment-agnostic; put env-specific values
  (URLs, credentials) in a clearly marked placeholder block, never inline secrets.
- Prefer steps whose result is **exportable** (automated rules, server actions, email
  templates, scheduled actions, `ir.config_parameter`): note the export in the log so
  `config-review` can verify against an artifact, not a screenshot.
- Settings with no export → the log value + (optional) screenshot is the evidence.

## Hand-off
> CONFIG_RUNBOOK.md + config-log.md ready. The BA executes the runbook, fills the
> log, then runs `config-review` to verify against CONFIG.md before UAT.

## DO / DO NOT
**DO**
- Order by dependency; keep each step atomic with its own verification.
- Tie every step to an `AC-NN`; note exportable evidence in the log slot.
- Hold steps that depend on an undeployed hybrid module until deploy is confirmed.

**DO NOT**
- Put real credentials/secrets in the runbook — placeholders only.
- Merge several settings into one unverifiable step.
- Add configuration not present in `CONFIG.md` (no scope creep; amend CONFIG.md first).
- Include master-data import steps — that is the shared `t-masterdata` node.

## Templates reference
- `references/config-log-template.md` — the BA-filled record of applied configuration.
