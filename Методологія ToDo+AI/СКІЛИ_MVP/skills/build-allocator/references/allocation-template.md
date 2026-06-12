# Build Allocation — {module} ({project})

Source: SPEC.md v{version} (approved) · Odoo {version} · {today}
Author: build-allocator AI

<!--
One row per AC. Track ∈ {config | code | hybrid}.
Same AC-NN id everywhere — never renumber. Hybrid = one config slice + one code slice.
Prefer config; route to code only when standard Odoo cannot do it faithfully.
-->

## Allocation table

| AC | Track | Realization summary | Odoo 19 source (config only) | Notes / hybrid split |
|----|-------|----------------------|------------------------------|----------------------|
| AC-01 | | | | |
| AC-02 | | | | |

## Track 1 (code) — AC list
<!-- comma-separated AC ids routed to code; for hybrid add "(code slice)" -->
-

## Track 2 (config) — AC list
<!-- comma-separated AC ids routed to config; for hybrid add "(config slice)" -->
-

## Coverage check (must all pass before hand-off)
- [ ] Every AC in SPEC.md appears in the table exactly once
- [ ] Every custom `td.*` model / field in SPEC «Models» is claimed by a code or hybrid AC
- [ ] Every `config` / hybrid-config row cites a real Odoo 19 source (`довідник §N` / URL)
- [ ] No AC is routed to two tracks except as an explicit hybrid split

## Open questions
<!-- Anything blocking a clean route — resolve before architecture / config-spec start -->
-
