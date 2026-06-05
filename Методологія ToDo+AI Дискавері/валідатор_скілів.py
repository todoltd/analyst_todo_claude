#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Валідатор інваріантів методології ІНІЦІАЦІЯ (Odoo 19).

Запуск:
    python3 валідатор_скілів.py "<шлях до теки 1. ІНІЦІАЦІЯ>" ["<шлях до розпакованого плагіна>"]

Якщо шляхи не передані — бере значення за замовчуванням нижче.
Перевіряє те, що grep-«наявність рядка» пропускає: цілісність вмісту, а не лише присутність.
Код виходу 0 = усі перевірки пройдені, 1 = є помилки.
"""
import os, re, sys, glob, hashlib

DEFAULT_SRC = "Методологія ToDo+AI/Скіли для Дискавері + MVP · Odoo 19/1. ІНІЦІАЦІЯ"

ALLOWED_KICKOFF = {"kickoff-agenda-finalizer", "kickoff-transcript-analyzer", "t-kickoff"}
SKILL_SUFFIXES = ("analyzer", "builder", "mapper", "researcher", "briefing", "finalizer", "writer")
FORBIDDEN = ["кік-оф", "кик-оф", "kickoff_prep", "[клієнт]"]

def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()

def strip_fences(t):
    return t.replace("```", "")

def check_source(src):
    errors, warns = [], []
    skills = sorted(glob.glob(os.path.join(src, "*", "*", "SKILL.md")))
    instr = sorted(glob.glob(os.path.join(src, "*", "ІНСТРУКЦІЯ.md"))) + \
            [p for p in [os.path.join(src, "ІНСТРУКЦІЯ.md")] if os.path.exists(p)]
    if len(skills) != 10:
        errors.append(f"очікувалось 10 скілів, знайдено {len(skills)}")
    skill_names = {os.path.basename(os.path.dirname(s)) for s in skills}

    for f in skills + instr:
        t = open(f, encoding="utf-8").read()
        rel = os.path.relpath(f, src)

        # 1. заборонені рядки
        for bad in FORBIDDEN:
            if bad in t:
                errors.append(f"{rel}: знайдено заборонене '{bad}'")

        # 2. латинський kickoff лише в дозволених ідентифікаторах
        for m in re.finditer(r"kickoff[\w-]*", t):
            tok = m.group(0)
            if tok == "kickoff_prep" or tok in ALLOWED_KICKOFF:
                continue
            if tok.startswith("kickoff-") and tok in ALLOWED_KICKOFF:
                continue
            # дозволяємо kickoff-agenda-finalizer / kickoff-transcript-analyzer
            if tok in ("kickoff",) and re.search(r"t-kickoff", t):
                continue
            if tok not in ALLOWED_KICKOFF and tok not in ("kickoff-agenda-finalizer", "kickoff-transcript-analyzer"):
                warns.append(f"{rel}: латинський '{tok}' (перевір, чи це дозволений ідентифікатор)")

        # 3. парність code-fence
        if t.count("```") % 2:
            errors.append(f"{rel}: непарна кількість code-fence ```")

        # 4. з'їдені імена: тире + 2+ пробіли + продовження
        if re.search(r"(Далі|Опційно|після неї|чи|або)\s*—?\s{2,}(для|\(|\.|чи|або)", t):
            errors.append(f"{rel}: підозра на з'їдене ім'я (тире + подвійний пробіл)")
        # порожні inline-backticks поза code-fence
        if "``" in strip_fences(t).replace("``", "<<EMPTY>>") and "<<EMPTY>>" in strip_fences(t).replace("``", "<<EMPTY>>"):
            # точніше: дві backtick підряд поза потрійними
            if re.search(r"(?<!`)``(?!`)", strip_fences(t)):
                warns.append(f"{rel}: порожні inline-backticks `` (перевір вручну)")

        # 5. крос-посилання на скіли існують
        for ref in re.findall(r"`([a-z]+(?:-[a-z]+)+)`", t):
            if ref.endswith(SKILL_SUFFIXES) and ref not in skill_names:
                errors.append(f"{rel}: посилання на неіснуючий скіл `{ref}`")

    # 6. кожен скіл: frontmatter + верифікація + наступний крок
    for s in skills:
        t = open(s, encoding="utf-8").read()
        nm = os.path.basename(os.path.dirname(s))
        if not (t.startswith("---") and re.search(r"^name:", t, re.M) and re.search(r"^description:", t, re.M)):
            errors.append(f"{nm}: некоректний frontmatter")
        if not re.search(r"Перевір.*перед збереженням|Pre-save", t):
            errors.append(f"{nm}: немає кроку верифікації перед збереженням")
        if not re.search(r"наступний крок|Установча Зустріч", t):
            warns.append(f"{nm}: немає підказки 'наступний крок'")

    return skills, skill_names, errors, warns

def check_plugin(plugin, src, skill_names):
    errors = []
    pj = os.path.join(plugin, ".claude-plugin", "plugin.json")
    if not os.path.exists(pj):
        errors.append("плагін: немає .claude-plugin/plugin.json")
        return errors
    import json
    try:
        m = json.load(open(pj))
        assert re.fullmatch(r"[a-z0-9-]+", m["name"])
    except Exception as e:
        errors.append(f"плагін: невалідний manifest ({e})")
    for nm in skill_names:
        ps = os.path.join(plugin, "skills", nm, "SKILL.md")
        ss = glob.glob(os.path.join(src, "*", nm, "SKILL.md"))
        if not os.path.exists(ps):
            errors.append(f"плагін: бракує скіла {nm}")
        elif ss and md5(ps) != md5(ss[0]):
            errors.append(f"плагін: {nm} відрізняється від джерела")
    return errors

def main():
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC
    plugin = sys.argv[2] if len(sys.argv) > 2 else None
    if not os.path.isdir(src):
        print(f"❌ Тека не знайдена: {src}")
        sys.exit(2)
    skills, names, errors, warns = check_source(src)
    if plugin:
        errors += check_plugin(plugin, src, names)

    print(f"Скілів перевірено: {len(skills)}")
    for w in warns:
        print(f"  ⚠️  {w}")
    if errors:
        print(f"\n❌ ПОМИЛКИ ({len(errors)}):")
        for e in errors:
            print(f"  • {e}")
        sys.exit(1)
    print("\n✅ Усі інваріанти пройдені.")
    sys.exit(0)

if __name__ == "__main__":
    main()
