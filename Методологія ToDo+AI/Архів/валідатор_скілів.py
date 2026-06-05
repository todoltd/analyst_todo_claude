#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""валідатор_скілів.py — перевірка інваріантів ВМІСТУ скілів (реконструйовано).

Запуск:  python3 валідатор_скілів.py <шлях до теки skills/>
Перевіряє зміст, а не наявність рядків. Свідомо НЕ плутає `` з ```code-fence```.
"""
import sys, re, pathlib

SKILLS_DIR = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "skills")

# «kickoff» легітимний лише як ідентифікатор/назва цих двох скілів
KICKOFF_OK = re.compile(r"kickoff[- ](agenda|transcript)[- ](finalizer|analyzer)", re.I)
# [назва компанії]/[галузь]/[дата] — легітимні плейсхолдери; заборонений лише [клієнт] та старі терміни
FORBIDDEN = [r"кік-?оф", r"kickoff_prep", r"\[клієнт\]"]
VERIF_RE = re.compile(r"верифікац|перед збереженн|самоперевірк|чеклист перед|перевір[ -].{0,40}перед", re.I)
HINT_RE  = re.compile(r"наступний крок", re.I)
EMPTY_CODE = re.compile(r"(?<!`)``(?!`)")          # порожній inline-код, але НЕ ```
SKILL_TOK  = re.compile(r"`([a-z][a-z0-9]+(?:-[a-z0-9]+){1,4})`")
SUFFIXES   = ("-analyzer", "-builder", "-researcher", "-mapper", "-writer", "-finalizer", "-briefing")


def lint(name, text, valid_names):
    issues = []
    # 1. frontmatter
    if not text.lstrip().startswith("---"):
        issues.append(("🔴", "немає frontmatter (---)"))
    mn = re.search(r"^name:\s*(\S+)", text, re.M)
    if not mn:
        issues.append(("🔴", "немає поля name у frontmatter"))
    elif mn.group(1).strip() != name:
        issues.append(("🟡", f"name='{mn.group(1).strip()}' не збігається з текою '{name}'"))
    if not re.search(r"^description:", text, re.M):
        issues.append(("🟡", "немає поля description"))
    # 2. заборонені терміни
    for pat in FORBIDDEN:
        for m in re.finditer(pat, text, re.I):
            issues.append(("🔴", f"заборонений термін «{m.group(0)}»"))
            break
    # 3. латинський kickoff поза дозволеними іменами
    scrub = KICKOFF_OK.sub("", text)
    if re.search(r"kickoff", scrub, re.I):
        issues.append(("🟡", "латинський 'kickoff' поза дозволеними іменами/назвами скілів"))
    # 4. парність code-fence
    if text.count("```") % 2 != 0:
        issues.append(("🔴", "непарні потрійні code-fence ```"))
    # 5. зʼїдені імена (порожній inline-код, не плутати з fence)
    if EMPTY_CODE.search(text):
        issues.append(("🔴", "порожній inline-код `` — ознака зʼїдених імен"))
    # 6. крок верифікації + підказка
    if not VERIF_RE.search(text):
        issues.append(("🟡", "немає кроку верифікації перед збереженням"))
    if not HINT_RE.search(text):
        issues.append(("🟡", "немає секції 'наступний крок'"))
    # 7. биті крос-посилання на скіли
    for tok in sorted(set(SKILL_TOK.findall(text))):
        if tok.endswith(SUFFIXES) and tok not in valid_names:
            issues.append(("🔴", f"биле крос-посилання на скіл `{tok}`"))
    return issues


def main():
    dirs = sorted([d for d in SKILLS_DIR.iterdir() if d.is_dir()])
    valid = {d.name for d in dirs}
    total = reds = yellows = 0
    print(f"Валідатор скілів — {len(dirs)} скілів у «{SKILLS_DIR}»\n")
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
    print(f"\nПідсумок: {total} зауважень — 🔴 {reds} критичних, 🟡 {yellows} попереджень.")
    print("✅ Усі інваріанти пройдені" if reds == 0 else "🔴 Є критичні порушення")
    sys.exit(1 if reds else 0)


if __name__ == "__main__":
    main()
