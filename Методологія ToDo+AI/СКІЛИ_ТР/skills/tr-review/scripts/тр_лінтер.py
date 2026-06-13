#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ТР-лінтер — детермінований pre-check ТР_*.md ПЕРЕД ручним tr-review.

Ловить механічні розриви, які виявив корпусний аналіз 90 реальних ТР
(див. Аналіз_корпусу_ТР/_корпус_ТР_інсайти.md). НЕ замінює tr-review —
доповнює його: знімає рутинні 🔴 детерміновано, щоб людина/LLM зосередились
на змістовній консистентності.

Використання:
    python3 тр_лінтер.py ТР_[назва].md [ще_файли.md ...]
Код виходу: 1 якщо є 🔴, інакше 0.
"""
import re, sys, pathlib

RED = "🔴"; WARN = "⚠️"

# Відомі одруки / невірні написання стандартних імен Odoo (із корпусу) → правильне
TYPOS = {
    r"\bparther_id\b": "partner_id",
    r"\bparnter_id\b": "partner_id",
    r"\bsignateru_date\b": "signature_date",
    r"\bjornal_id\b": "journal_id",
    r"\btock\.quant\b": "stock.quant",
    r"\bsrm\.lead\b": "crm.lead",
    r"\bmrp\.boom\b": "mrp.bom",
    r"\bread\.only\b": "readonly",
    r"\bts_listing\b": "td.listing",
}
# Застарілий синтаксис (< v17) → актуальний v19
LEGACY = {
    r"<tree\b": "<list>",
    r"\battrs\s*=": "прямі invisible/readonly/required з Python-виразом",
    r"\bstates\s*=": "invisible/readonly",
    r"\bt-raw\b": "t-out (для HTML — markupsafe.Markup)",
    r"\bgroup_operator\b": "aggregator",
    r"\bxmlrpc\b": "зовнішній API /json/2 + Bearer",
    r"\bjsonrpc\b": "зовнішній API /json/2 + Bearer",
}


def lint(path):
    p = pathlib.Path(path)
    text = p.read_text(encoding="utf-8")
    lines = text.splitlines()
    issues = []  # (severity, message)
    add = lambda sev, msg: issues.append((sev, msg))

    # 1. Одруки стандартних імен (🔴)
    for pat, fix in TYPOS.items():
        for i, l in enumerate(lines, 1):
            if re.search(pat, l):
                add(RED, f"р.{i}: одрук імені → має бути `{fix}`  «{l.strip()[:70]}»")

    # 2. Застарілий синтаксис (🔴)
    for pat, fix in LEGACY.items():
        for i, l in enumerate(lines, 1):
            if re.search(pat, l):
                add(RED, f"р.{i}: застарілий синтаксис → {fix}  «{l.strip()[:70]}»")

    # 3. HTTP-403 як механізм блокування (🔴)
    for i, l in enumerate(lines, 1):
        if re.search(r"\b403\b", l) and re.search(r"(?i)forbidden|блок|доступ|помилк|відмов", l):
            add(RED, f"р.{i}: HTTP-403 як механізм → AccessError/UserError  «{l.strip()[:70]}»")

    # 4. product.product як таблиця залишків (⚠️)
    for i, l in enumerate(lines, 1):
        if "product.product" in l and re.search(r"(?i)залишк|наявн|на склад|\bqty", l):
            add(WARN, f"р.{i}: product.product для залишків? → stock.quant  «{l.strip()[:70]}»")

    # 5. Формат AC — лише канонічний AC-NN (🔴 на legacy)
    ac_canon = re.findall(r"\bAC-\d{2,}\b", text)
    ac_legacy = re.findall(r"(?m)(?<![\w-])AC\s?\d+(?:\.\d+)?(?![\w-])", text)  # AC1, AC 1.1 (не AC-01)
    scen = re.findall(r"(?im)\bscenario\s*\d+\b", text)
    if ac_legacy:
        uniq = sorted({x.strip() for x in ac_legacy})[:6]
        add(RED, f"не-канонічні AC ({len(ac_legacy)}): {', '.join(uniq)} → перенумеруй у AC-NN")
    if scen:
        add(RED, f"`Scenario N` як критерії ({len(scen)}) → перенумеруй у AC-NN")
    if not ac_canon and re.search(r"(?i)критері|acceptance|приймання", text):
        add(WARN, "згадано критерії приймання, але немає жодного `AC-NN` — введи канонічні AC")

    # 6. Незаповнені плейсхолдери (⚠️)
    for i, l in enumerate(lines, 1):
        if any(t in l for t in ("<!-- TODO:", "[⚠️ ІНСТРУКЦІЯ", "‹заповнити›", "‹уточнити›")):
            add(WARN, f"р.{i}: незаповнений плейсхолдер  «{l.strip()[:70]}»")

    # 7. Версія Odoo (⚠️)
    if not re.search(r"(?i)odoo\s*1[789]|платформа\s*[:·].*odoo", text):
        add(WARN, "не знайдено версію Odoo (18/19) — вкажи з картки проєкту")

    # 8. Технічні імена td_/td. (⚠️, груба евристика)
    if "td_" not in text and "td." not in text and re.search(r"(?i)\bполе\b|\bмодел|many2one|selection|computed", text):
        add(WARN, "є згадки полів/моделей, але жодного техімені `td_`/`td.` — додай технічні імена (розрив №1 корпусу)")

    # 9. Назва файлу vs заголовок ТР (⚠️, евристика розсинхрону)
    title_m = re.search(r"(?im)^#{0,3}\s*технічне рішення\s*[:—\-]\s*(.+?)\s*$", text)
    if title_m:
        title = title_m.group(1).strip().lower()
        base = re.sub(r"^тр[_\s]*", "", p.stem.lower())
        bt = set(re.findall(r"[\w']{4,}", base))
        tt = set(re.findall(r"[\w']{4,}", title))
        if bt and tt and not (bt & tt):
            add(WARN, f"назва файлу не перетинається із заголовком ТР («{title[:38]}») — можливий розсинхрон")

    return issues


def main():
    if len(sys.argv) < 2:
        print("Використання: python3 тр_лінтер.py ТР_[назва].md [...]")
        sys.exit(2)
    total = red = 0
    for path in sys.argv[1:]:
        try:
            issues = lint(path)
        except FileNotFoundError:
            print(f"\n=== {path} ===\n  ✗ файл не знайдено"); continue
        print(f"\n=== {path} ===")
        if not issues:
            print("  ✓ механічних розривів не знайдено"); continue
        nred = sum(1 for s, _ in issues if s == RED)
        for sev, msg in issues:
            print(f"  {sev} {msg}")
        print(f"  — разом: {len(issues)} (🔴 {nred})")
        total += len(issues); red += nred
    print(f"\nПІДСУМОК: {total} зауважень, {red} критичних 🔴")
    print("Примітка: лінтер — детермінований pre-check; змістовну консистентність (вимога→AC→реалізація) перевіряє tr-review.")
    sys.exit(1 if red else 0)


if __name__ == "__main__":
    main()
