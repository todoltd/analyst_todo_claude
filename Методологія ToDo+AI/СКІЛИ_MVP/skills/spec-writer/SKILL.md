---
name: spec-writer
description: >
  Build SPEC.md for the MVP build chain by converting an APPROVED ТР (Технічне Рішення,
  `ТР_[назва].md`) into the machine-parseable SPEC.md the chain consumes. Variant A: the ТР is
  the single source of truth — this skill projects requirements, it does not author them, and
  preserves AC-01 ids verbatim. Triggers on: "ТР → SPEC", "збери SPEC з ТР", "build SPEC.md",
  "convert ТР to spec", "підготуй SPEC для білду". Requires ТР status «Погодження клієнта» /
  approved; if there is no ТР, route back to the tr-* chain.
---

# Odoo Spec-Writer — ТР → SPEC.md converter (Variant A)

Projects an **approved ТР** into the normalized, machine-parseable `SPEC.md`
that the rest of the build chain keys off. The ТР stays the human/client source
of truth (Ukrainian prose + tables); `SPEC.md` is its structured projection with
stable `AC-01` ids so traceability survives all the way to tests and PR review.

> **Position in the chain:** runs once the ТР reaches «Погодження клієнта»
> (registry: «Перелік технічних рішень»). Output feeds `architecture`.

## Inputs required
- Approved `ТР_[назва].md` (status «Погодження клієнта» / approved).
- Odoo version — from the **project card** (18 / 19), not hardcoded.
- Module technical name — `<project>_<area>` (e.g. `olimpius_delivery`); models stay `td.*`.
- Existing `SPEC.md` if this is a change/patch (ТР Format C) — to append, not overwrite.

## Pre-flight check (stop if any fails)
- [ ] ТР status is «Погодження клієнта» / approved. If not → stop, route to `tr-review`.
- [ ] ТР «Open questions» / unresolved items are empty.
- [ ] Acceptance criteria in the ТР use the **canonical `AC-01` format**.
      If the ТР still uses legacy ids (`AC1`, `AC 1.1`, `Scenario N`,
      `УМОВА/КОЛИ/ТОДІ` без `AC-NN`) → **stop**. Standardization is upstream:
      ask the BA to re-emit AC as `AC-01` in `tr-usecases-acceptance`
      (see README_інтеграція.md). Do not renumber silently here.

## Process — extract, do not invent

Everything in `SPEC.md` must trace back to a line in the ТР. If the ТР is
missing something the template needs, write it under **Open questions** — never
guess. Keep all human-readable text (user stories, AC bodies) in the **ТР's
language (Ukrainian)**; keep structure/keywords as in the template.

### 1. Header & meta
Fill the `references/spec-template.md` header from the ТР «Загальна інформація»:
- `Status`: **approved** (inherited from the approved ТР — see §6, no AI self-approval).
- `Odoo version`: from project card.
- `Version`: 5-segment `{odoo_version}.{odoo_subversion}.{major}.{minor}.{bugfix}`
  (from the module manifest / project card). Carry `Since` values from the ТР.
- `Version history`: add a row — `{today} | spec-writer AI | SPEC built from approved ТР «{назва}»`.

### 2. User stories
From the ТР «Use Cases / USER STORY» section. Format `US-01`, `US-02`…
- One story per interaction type; **keep the Ukrainian wording** of the ТР.
- Map each role to a real Odoo group — use `references/odoo-groups.md`
  (e.g. `sales_team.group_sale_manager`, or a custom `{module}.group_{module}_manager`).
- Never introduce a story the ТР does not contain.

### 3. Acceptance criteria — preserve AC-01 ids verbatim
Copy every AC from the ТР into the SPEC `Acceptance criteria` section.
- **Keep the exact id** (`AC-01`, `AC-02`, …). Do not renumber, merge, or split.
  These ids are the spine: `# TODO: AC-01` (scaffolding) → docstring (code-dev)
  → `test_ac01_…` (testing) → pr-review checklist.
- Keep the body as written in the ТР (Given/When/Then **or** УМОВА/КОЛИ/ТОДІ).
- Keep the `[US-XX]` link.
- Carry over the ТР's "нещасливі шляхи" ACs (no data / error / rights / constraints).

### 4. Models — from «Опис технічної реалізації»
Project the ТР technical-design section into the SPEC `Models` blocks:
- Model header: `### {ModelName} (`td.{module}.{entity}`)`, `Inherits:`, `Since:`.
- **Fields table** → `| Field | Type | Required | Default | Since | Description |`
  (map the ТР columns «Назва поля / Тип / Звідки тягнути / Примітка»; keep
  `domain` / `required` / `readonly` / `store` notes; `monetary` → currency UAH).
- Selection reference values (довідники) and their UI path.
- Computed fields (depends/stored), SQL constraints, key methods (`action_*`, `_compute_*`).
- **Views & menus** table; **Security** matrix (User / Manager) using `odoo-groups.md`.
- Preserve ToDo conventions: `td.*`, field prefix `td_*`, name mask `<Проект>: …`.
- Anything the architect must still decide (DB-level structure the ТР left in the
  empty «АРХІТЕКТУРА» section) → leave for `architecture`, note under Open questions.

### 5. Scope & open questions
- `Out of scope`: copy the ТР scope boundaries (що винесено в наступне ТЗ).
- `Open questions`: must be **empty** to proceed. Any gap found while projecting
  goes here and blocks architecture until resolved in the ТР.

### 6. Approval gate (inherited, not re-issued)
- SPEC `Status` = **approved** because the **ТР** was approved by the client.
  AI does not self-approve and does not re-open approval here.
- Confirm before hand-off:
  - [ ] Every ТР requirement/AC is represented in SPEC.
  - [ ] Every AC id is `AC-01` form and unchanged from the ТР.
  - [ ] `Out of scope` populated; `Open questions` empty.

### 7. Change/patch mode (ТР Format C)
If the ТР is a change doc (Format C): **append** a `## Change: {title} (v{new_version})`
block to the existing SPEC (do not rewrite prior content). Only new/changed rows
get the new `Since`; existing rows keep theirs. Use the change-block layout from
`references/spec-template.md`.

## Hand-off
> SPEC.md built from approved ТР. Next: `architecture` (fills the technical
> blueprint + AC traceability table the ТР left for the architect).

## DO / DO NOT
**DO**
- Treat the ТР as the source of truth; mirror it faithfully into SPEC structure.
- Keep AC ids and Ukrainian wording intact.
- Reference real Odoo groups (`references/odoo-groups.md`).

**DO NOT**
- Author new requirements, user stories, or ACs (that is the upstream tr-* chain).
- Renumber or reformat AC ids.
- Invent fields/models/integrations not present in the ТР — flag as Open questions.
- Re-issue or self-approve the spec.

## Templates reference
- `references/spec-template.md` — canonical SPEC.md structure.
- `references/odoo-groups.md` — standard Odoo group ids + ToDo module-group convention.
