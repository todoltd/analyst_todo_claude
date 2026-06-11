---
name: odoo-pr-review
description: >
  Review an Odoo module pull request against SPEC.md for spec compliance,
  Odoo conventions, and code quality. Use this skill when a developer
  submits a PR, asks for a code review, or wants to self-review before
  pushing. Triggers on: "review this PR", "review my code", "check this
  against spec", "code review", "is this spec-compliant", "review before
  merge", "check my implementation". Produces a structured review with
  spec-compliance verdict, convention violations, and actionable fixes.
---

# Odoo PR Review Skill

Structured code review that enforces SDD spec compliance and Odoo conventions.
Outputs a verdict (APPROVE / REQUEST CHANGES / BLOCK) with specific issues.

## ToDo — еталон і межі
- `SPEC.md` is the projection of the **approved ТР**; "spec compliance" = compliance
  with the approved ТР (its AC + «Опис технічної реалізації»). If SPEC and ТР disagree,
  the ТР wins — flag the SPEC drift.
- **Розведення з `tr-review`:** `tr-review` checks the ТР *document* before client
  sign-off; this skill checks the *code* before merge. Different stages, both required.
- AC ids are canonical `AC-01`.

## Inputs required
- Diff or changed files
- `SPEC.md` (to check compliance)
- Target AC number(s) this PR claims to implement
- Target Odoo version

## Review dimensions

Run all five dimensions. Each produces a verdict and a list of findings.

---

### Dimension 1 — Spec compliance (BLOCK if failed)

The most important check. Code must not deviate from the approved spec.

**Check for each changed model file:**
- [ ] No new fields that are not in SPEC.md
- [ ] No removed fields that are in SPEC.md
- [ ] Field types match SPEC.md (e.g. `Char` not `Text` if spec says `Char`)
- [ ] `_name` matches SPEC.md technical name exactly
- [ ] State machine transitions match SPEC.md state machine exactly
- [ ] Business rules match AC text — not an approximation

**If any check fails → BLOCK. Do not approve until SPEC.md is updated first.**

Wording for BLOCK finding:
```
SPEC VIOLATION [AC-XX]: {describe discrepancy}
SPEC says: {exact spec text}
Code does: {what the code actually does}
Fix: Either revert the code change or update SPEC.md and get approval.
```

---

### Dimension 2 — AC coverage (REQUEST CHANGES if failed)

- [ ] Every AC listed in the PR description has at least one implementation
- [ ] Every `# TODO: AC-XX` for the targeted ACs has been removed
- [ ] No new `# TODO:` markers were introduced without a corresponding AC

---

### Dimension 3 — Odoo conventions (REQUEST CHANGES if failed)

**Model conventions:**
- [ ] `_description` present and non-empty
- [ ] `active` field included (unless intentionally excluded — must be noted in spec)
- [ ] `company_id` field included for multi-company modules
- [ ] `@api.model_create_multi` on `create` override (Odoo 17+)
- [ ] No `@api.multi` or `@api.one` (removed in v14)
- [ ] `self.env.ref()` not called inside compute methods or loops
- [ ] `search()` inside loops uses a limit or is replaced with `read_group`

**View conventions:**
- [ ] `invisible=` used instead of `attrs=` (Odoo 17+)
- [ ] `domain=` used directly instead of `attrs=` (Odoo 17+)
- [ ] Status bar uses `statusbar_visible` for multi-state models
- [ ] Chatter block present on form view for `mail.thread` models
- [ ] All user-visible strings are wrapped in `_('')`

**Security:**
- [ ] Every new model has a row in `ir.model.access.csv`
- [ ] Multi-company record rule exists for models with `company_id`
- [ ] No `sudo()` calls without an explanatory comment

**Code quality:**
- [ ] No hardcoded company IDs or user IDs
- [ ] Error messages use `_()` for translation
- [ ] `ValidationError` used for data constraint violations
- [ ] `UserError` used for business rule violations
- [ ] No bare `except:` clauses
- [ ] No `print()` statements

---

### Dimension 4 — Test coverage (REQUEST CHANGES if failed)

- [ ] At least one test per AC implemented in this PR
- [ ] Test methods are named `test_ac{nn}_{description}`
- [ ] Tests use `with_user()` to verify access control ACs
- [ ] Negative cases (exceptions) use `with self.assertRaises(...)`
- [ ] Tests are tagged with `@tagged('td_{module}', 'post_install', '-at_install')`
- [ ] `common.py` base class used (not duplicated setup)

---

### Dimension 5 — Manifest & dependencies (REQUEST CHANGES if failed)

- [ ] Version bumped appropriately (patch/minor/major per SPEC.md rules)
- [ ] `depends` only contains modules justified by SPEC.md
- [ ] All new XML files listed in `data` in `__manifest__.py`
- [ ] XML files listed in correct dependency order (security before views)

---

## Review output format

```markdown
## PR Review: {branch-name}
Reviewing against: SPEC.md v{version}, AC-{nn}
Odoo version: {16/17/18/19}
Reviewer: AI (odoo-pr-review skill)

---

### Verdict: {APPROVE | REQUEST CHANGES | BLOCK}

---

### Spec compliance
{PASS | BLOCK}
{findings list — or "No violations found."}

### AC coverage
{PASS | REQUEST CHANGES}
{findings list}

### Odoo conventions
{PASS | REQUEST CHANGES}
{findings list, each with file:line reference and suggested fix}

### Test coverage
{PASS | REQUEST CHANGES}
{findings list}

### Manifest & dependencies
{PASS | REQUEST CHANGES}
{findings list}

---

### Summary

{2–4 sentence summary of overall quality and what must be fixed before merge.}
```

## Verdict rules

| Condition | Verdict |
|-----------|---------|
| Any spec violation | BLOCK |
| Zero spec violations, some convention/test issues | REQUEST CHANGES |
| All checks pass | APPROVE |

A BLOCK means the PR cannot merge until `SPEC.md` is updated and re-approved
or the code is reverted. This is the hardest rule in the SDD workflow.

## Finding severity levels

| Prefix | Meaning | Required to fix before merge? |
|--------|---------|-------------------------------|
| `SPEC VIOLATION` | Code diverges from approved spec | Yes — BLOCK |
| `REQUIRED` | Convention or coverage issue | Yes — REQUEST CHANGES |
| `WARNING` | Code smell, not a violation | Recommended |
| `SUGGESTION` | Improvement idea | Optional |

## Version-specific checks

### Odoo 17+
- Flag any `attrs=` usage — deprecated
- Flag missing `@api.model_create_multi` on `create`

### Odoo 18+
- Flag missing `sanitize=True` on `fields.Html`
- Flag any legacy JS (non-OWL) components

### Odoo 19+
- Flag missing company record rules
- Flag `mail` dependency where `discuss` is needed
