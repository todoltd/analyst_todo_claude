#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""валідатор_скілів_дискавері.py — інваріанти вмісту скілів пакета odoo19-discovery-sessions.

Адаптація валідатора ІНІЦІАЦІЇ (Архів/валідатор_скілів.py):
- крос-посилання на скіли плагіна odoo19-discovery-initiation — легітимні (два пакети працюють у парі);
- allowlist «kickoff» розширено актуальними іменами (kickoff-question-builder з v0.3.0);
- решта інваріантів без змін: frontmatter, заборонені терміни, парність ```, зʼїдені імена,
  крок верифікації, підказка «наступний крок».

Запуск:  python3 валідатор_скілів_дискавері.py <шлях до skills/> [<шлях до skills/ ІНІЦІАЦІЇ — регресія>]
"""
import sys, re, pathlib

SKILLS_DIR = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "skills")
EXTRA_DIR = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else None

INITIATION_SKILLS = {
    "sales-handover-analyzer", "client-web-researcher", "competitor-mapper", "industry-briefing",
    "discovery-context-builder", "kickoff-agenda-finalizer", "kickoff-question-builder",
    "facilitation-guide-builder", "discovery-charter-writer", "kickoff-transcript-analyzer",
    "meeting-protocol-builder", "discovery-plan-builder",
}
SESSION_SKILLS = {"session-question-builder", "session-client-prep-builder"}

KICKOFF_OK = re.compile(
    r"kickoff[- ](agenda[- ]finalizer|transcript[- ]analyzer|question[- ]builder|survey[- ]protocol)", re.I)
FORBIDDEN = [r"кік-?оф", r"kickoff_prep", r"клієнт"]  # «клієнт» заборонено в методології — вживати «замовник»
VERIF_RE = re.compile(r"верифікац|перед збереженн|самоперевірк|чеклист перед|перевір[ -].{0,40}перед", re.I)
HINT_RE = re.compile(r"наступний крок", re.I)
EMPTY_CODE = re.compile(r"(?<!`)``(?!`)")
SKILL_TOK = re.compile(r"`([a-z][a-z0-9]+(?:-[a-z0-9]+){1,4})`")
SUFFIXES = ("-analyzer", "-builder", "-researcher", "-mapper", "-writer", "-finalizer", "-briefing")


def lint(name, text, valid_names):
    issues = []
    if not text.lstrip().startswith("---"):
        issues.append(("🔴", "немає frontmatter (---)"))
    mn = re.search(r"^name:\s*(\S+)", text, re.M)
    if not mn:
        issues.append(("🔴", "немає поля name у frontmatter"))
    elif mn.group(1).strip() != name:
        issues.append(("🟡", f"name='{mn.group(1).strip()}' не збігається з текою '{name}'"))
    if not re.search(r"^description:", text, re.M):
        issues.append(("🟡", "немає поля description"))
    for pat in FORBIDDEN:
        for m in re.finditer(pat, text, re.I):
            issues.append(("🔴", f"заборонений термін «{m.group(0)}»"))
            break
    scrub = KICKOFF_OK.sub("", text)
    if re.search(r"kickoff", scrub, re.I):
        issues.append(("🟡", "латинський 'kickoff' поза дозволеними іменами/назвами скілів"))
    if text.count("```") % 2 != 0:
        issues.append(("🔴", "непарні потрійні code-fence ```"))
    if EMPTY_CODE.search(text):
        issues.append(("🔴", "порожній inline-код `` — ознака зʼїдених імен"))
    if not VERIF_RE.search(text):
        issues.append(("🟡", "немає кроку верифікації перед збереженням"))
    if not HINT_RE.search(text):
        issues.append(("🟡", "немає секції 'наступний крок'"))
    for tok in sorted(set(SKILL_TOK.findall(text))):
        if tok.endswith(SUFFIXES) and tok not in valid_names:
            issues.append(("🔴", f"биле крос-посилання на скіл `{tok}`"))
    return issues


def check_dir(skills_dir, valid):
    total = reds = yellows = 0
    dirs = sorted([d for d in skills_dir.iterdir() if d.is_dir()])
    print(f"\n— {len(dirs)} скілів у «{skills_dir}»")
    for d in dirs:
        f = d / "SKILL.md"
        if not f.exists():
            print(f"🔴 {d.name}: немає SKILL.md"); reds += 1; total += 1; continue
        issues = lint(d.name, f.read_text(encoding="utf-8"), valid)
        r = sum(1 for s, _ in issues if s == "🔴")
        y = sum(1 for s, _ in issues if s == "🟡")
        reds += r; yellows += y; total += len(issues)
        if issues:
            print(f"■ {d.name}  (🔴{r} 🟡{y})")
            for s, msg in issues:
                print(f"    {s} {msg}")
        else:
            print(f"✅ {d.name}")
    return total, reds, yellows


def main():
    valid = INITIATION_SKILLS | SESSION_SKILLS
    valid |= {d.name for d in SKILLS_DIR.iterdir() if d.is_dir()}
    if EXTRA_DIR:
        valid |= {d.name for d in EXTRA_DIR.iterdir() if d.is_dir()}
    total = reds = yellows = 0
    for sd in [SKILLS_DIR] + ([EXTRA_DIR] if EXTRA_DIR else []):
        t, r, y = check_dir(sd, valid)
        total += t; reds += r; yellows += y
    print(f"\nПідсумок: {total} зауважень — 🔴 {reds} критичних, 🟡 {yellows} попереджень.")
    print("✅ Усі інваріанти пройдені" if reds == 0 else "🔴 Є критичні порушення")
    sys.exit(1 if reds else 0)


if __name__ == "__main__":
    main()
