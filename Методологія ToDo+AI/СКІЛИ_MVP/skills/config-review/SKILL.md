---
name: config-review
description: >
  Review a configured Odoo instance against CONFIG.md before UAT — Track 2's gate, the analog
  of pr-review for code. Verifies the BA's setup (per config-log + exported artifacts) matches
  the approved config spec, every config AC is covered, and nothing relies on an invented Odoo
  19 setting. Outputs APPROVE / REQUEST CHANGES / BLOCK per AC. Triggers on: "config review",
  "перевір конфігурацію", "рев'ю налаштувань", "config gate", "перевір налаштування перед
  UAT". Requires CONFIG.md + filled config-log.
---

# Odoo Config-Review — gate before UAT

Structured review that enforces **config-spec compliance** for Track 2, the way
`pr-review` enforces it for code. Outputs a verdict
(APPROVE / REQUEST CHANGES / BLOCK) with specific, per-`AC-NN` findings.

## ToDo — еталон і межі
- `CONFIG.md` is the projection of the **approved ТР/SPEC**; "config compliance" =
  the live Odoo state matches `CONFIG.md`. If `CONFIG.md` and ТР disagree, the ТР
  wins — flag the drift.
- **Розведення з `pr-review`:** `pr-review` checks **code** before merge;
  this skill checks **configuration** before UAT. Same SDD gate rule, different track.
- Configuration has no `git diff` — the evidence is the **config-log + exported
  artifacts** (`base.automation` / `mail.template` / server-action / cron XML,
  `ir.config_parameter` values). Review against artifacts, not memory.
- AC ids are canonical `AC-01`.

## Inputs required
- `CONFIG.md` (approved) and `ALLOCATION.md` (config AC list).
- Filled `config-log.md` + exported artifacts / screenshots.
- Target Odoo version + edition.
- (If hybrid) confirmation the dependent `td.*` module is deployed.

## Review dimensions

Run all five. Each produces a verdict and a list of findings.

---

### Dimension 1 — Config-spec compliance (BLOCK if failed)

The most important check. The live configuration must not deviate from `CONFIG.md`.

**For each `CONFIG.md` item:**
- [ ] The setting/rule/template/view exists with the value `CONFIG.md` specifies
- [ ] The config-log records it as applied (status ✅), with the actual value
- [ ] Any deviation in the log is reflected by an **approved** `CONFIG.md` update — not a silent change

**If any check fails → BLOCK. Do not approve until `CONFIG.md` is updated & re-approved, or the config is corrected.**

```
CONFIG VIOLATION [AC-XX]: {discrepancy}
CONFIG says: {exact CONFIG.md item + value}
Instance does: {what the config-log / export shows}
Fix: re-configure to match, or update CONFIG.md and get approval.
```

---

### Dimension 2 — AC coverage (REQUEST CHANGES if failed)
- [ ] Every config / hybrid-config AC in `ALLOCATION.md` has at least one applied step
- [ ] No config AC is left unconfigured (log status ✅ or a justified ⏭️ skip)
- [ ] No applied configuration exists that maps to **no** AC (scope creep)

---

### Dimension 3 — Odoo 19 validity (BLOCK if invented; else REQUEST CHANGES)
- [ ] Every item uses a **real** Odoo 19 capability in the target edition (path resolves)
- [ ] Each `CONFIG.md` item still carries its Odoo 19 source; the path matches the live menu
- [ ] No setting was "approximated" onto a different menu because the specified one does not exist

**An invented / non-existent setting → BLOCK** (it cannot pass UAT). Edition mismatch
(Studio item on Community) → REQUEST CHANGES with a re-route note to `build-allocator`.

---

### Dimension 4 — Evidence & config-log (REQUEST CHANGES if failed)
- [ ] `config-log.md` is complete — every runbook step has a status + actual value
- [ ] Exportable items (automation, server actions, templates, cron, `ir.config_parameter`)
      have an export reference attached, not just a screenshot
- [ ] Deviations section filled (or explicitly "none")
- [ ] BA sign-off present

---

### Dimension 5 — Boundary & hybrid (REQUEST CHANGES if failed)
- [ ] No master-data records (products/partners/CoA) configured here — that is `t-masterdata`
- [ ] For each hybrid AC: the code slice's `td.*` module is deployed, and the config
      references it correctly (field/model/method names match SPEC)
- [ ] Nothing that genuinely needs code was forced into config (if found → re-route to allocator)

---

## Review output format

```markdown
## Config Review: {module} ({environment})
Reviewing against: CONFIG.md v{version}, AC: {config AC list}
Odoo version / edition: {19 / Community|Enterprise}
Reviewer: AI (config-review skill)

---

### Verdict: {APPROVE | REQUEST CHANGES | BLOCK}

---

### Config-spec compliance
{PASS | BLOCK} — {findings, or "No deviations found."}

### AC coverage
{PASS | REQUEST CHANGES} — {findings}

### Odoo 19 validity
{PASS | BLOCK | REQUEST CHANGES} — {findings}

### Evidence & config-log
{PASS | REQUEST CHANGES} — {findings}

### Boundary & hybrid
{PASS | REQUEST CHANGES} — {findings}

---

### Summary
{2–4 sentences: overall readiness for UAT and what must be fixed first.}
```

## Verdict rules

| Condition | Verdict |
|-----------|---------|
| Any config-spec violation, or any invented/non-existent setting | BLOCK |
| Zero violations, some coverage / evidence / boundary issues | REQUEST CHANGES |
| All checks pass | APPROVE |

A BLOCK means the MVP cannot enter UAT until `CONFIG.md` is updated & re-approved
or the configuration is corrected. APPROVE = config track ready for UAT; on the
registry «Перелік технічних рішень» it contributes to «Виконано» (together with
Track 1 `pr-review` APPROVE).

## Finding severity levels

| Prefix | Meaning | Required before UAT? |
|--------|---------|----------------------|
| `CONFIG VIOLATION` | Live config diverges from approved CONFIG.md | Yes — BLOCK |
| `INVALID` | Invented / non-existent Odoo 19 setting | Yes — BLOCK |
| `REQUIRED` | Coverage / evidence / boundary issue | Yes — REQUEST CHANGES |
| `WARNING` | Fragile config, not a violation | Recommended |
| `SUGGESTION` | Improvement idea | Optional |

## UAT loop (gw-reason)
When UAT returns a **configuration** error (BPMN gateway «Причина відмови?» →
config errors → BA), the BA re-configures and re-runs this skill against the same
`CONFIG.md` until APPROVE. (Code bugs go to Track 1 / `pr-review`, not here.)

## DO / DO NOT
**DO**
- Verify against the config-log + exported artifacts; BLOCK on any divergence from approved CONFIG.md.
- Confirm every config item resolves to a real Odoo 19 menu in the target edition.
- Keep `AC-NN` ids; report findings per AC.

**DO NOT**
- Approve around a deviation — require a CONFIG.md update + re-approval instead.
- Self-approve, or re-open the ТР/CONFIG approval here.
- Review code here (that is `pr-review`) or master-data (that is `t-masterdata`).
