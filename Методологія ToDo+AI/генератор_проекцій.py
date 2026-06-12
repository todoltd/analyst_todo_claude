#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""генератор_проекцій.py — P4: проекції з джерела істини (СПЕЦ_P4_генератор-проекцій.md).

Генератор НІЧОГО не авторить — лише рендерить проекції з артефактів і plugin.json.
stdlib-only (json, re, pathlib, sys).

Підкоманди:
  status              — оновити P4:VER-якорі BPMN з plugin.json кожного пакета
                        + згенерувати дашборд СТАТУС_методології.html. Запускати при зміні версій.
  rtm <project_dir>   — матриця трасування вимог: AC ТР → SPEC → код (# TODO/докстрінг) →
                        тести (test_acNN) → статус реєстру. Результат RTM_<project>.md.

Запуск:  python3 генератор_проекцій.py status
         python3 генератор_проекцій.py rtm /шлях/до/проекту
"""
import sys, re, json, pathlib

BASE = pathlib.Path(__file__).resolve().parent
BPMN = BASE / "bpmn_odoo19_discovery_СТАТУС-скілів.html"
STATUS_JSON = BASE / "СТАТУС_методології.json"
DASHBOARD = BASE / "СТАТУС_методології.html"

CANON_STATUSES = {"чернетка", "на розгляді", "погоджено", "виконано", "застаріле"}
STATUS_COLOR = {"чернетка": "#adb5bd", "на розгляді": "#f59f00", "погоджено": "#4263eb",
                "виконано": "#2f9e44", "застаріле": "#868e96"}


def plugin_version(src):
    pj = BASE / src / ".claude-plugin" / "plugin.json"
    if not pj.exists():
        return None
    return json.loads(pj.read_text(encoding="utf-8")).get("version")


# ───────────────────────── P4a · статуси/версії ─────────────────────────
def cmd_status():
    data = json.loads(STATUS_JSON.read_text(encoding="utf-8"))
    stages = data["stages"]
    problems = []

    for st in stages:
        st["version"] = plugin_version(st["src"])
        if st["version"] is None:
            problems.append(f"немає plugin.json для пакета {st['src']}")
        if st["status"] not in CANON_STATUSES:
            problems.append(f"{st['id']}: статус «{st['status']}» поза каноном контракту")

    html = BPMN.read_text(encoding="utf-8")
    bpmn_keys = set(re.findall(r"<!--P4:VER:([a-z]+)-->", html))
    json_keys = {st["anchor"] for st in stages}

    for st in stages:
        if st["version"] is None:
            continue
        pat = re.compile(rf"(<!--P4:VER:{re.escape(st['anchor'])}-->).*?(<!--/P4-->)")
        if not pat.search(html):
            problems.append(f"якоря P4:VER:{st['anchor']} немає в BPMN (додати разово)")
            continue
        html = pat.sub(rf"\g<1>{st['version']}\g<2>", html)

    for k in bpmn_keys - json_keys:
        problems.append(f"якір P4:VER:{k} у BPMN не описаний у СТАТУС_методології.json")

    BPMN.write_text(html, encoding="utf-8")

    # інваріант: кожен бейдж == версія plugin.json
    for st in stages:
        if st["version"] is None:
            continue
        for found in re.findall(rf"<!--P4:VER:{re.escape(st['anchor'])}-->([^<]*)<!--/P4-->", html):
            if found != st["version"]:
                problems.append(f"P4:VER:{st['anchor']}={found} ≠ plugin {st['version']}")

    DASHBOARD.write_text(render_dashboard(stages), encoding="utf-8")

    print("Стадії методології:")
    for st in stages:
        print(f"  {st['title']:30s} {st['package']:30s} v{st['version']}  [{st['status']}]  {st['skills']} скілів")
    print(f"\nBPMN-якорі оновлено ({len(json_keys)} пакетів) · дашборд → {DASHBOARD.name}")
    if problems:
        print("\n⚠️ ПРОБЛЕМИ:")
        for p in problems:
            print("  🔴", p)
        sys.exit(1)
    print("✅ Інваріанти пройдені: версії бейджів BPMN == plugin.json кожного пакета.")


def render_dashboard(stages):
    rows = ""
    for i, st in enumerate(stages, 1):
        c = STATUS_COLOR.get(st["status"], "#868e96")
        rows += (f'<tr><td>{i}</td><td><b>{st["title"]}</b></td>'
                 f'<td><code>{st["package"]}</code></td>'
                 f'<td style="text-align:center">{st["skills"]}</td>'
                 f'<td style="text-align:center">v{st["version"]}</td>'
                 f'<td><span style="background:{c};color:#fff;padding:2px 10px;'
                 f'border-radius:10px;font-size:13px">{st["status"]}</span></td></tr>')
    total = sum(st["skills"] for st in stages)
    return f"""<!DOCTYPE html><html lang="uk"><head><meta charset="utf-8">
<title>Статус методології ToDo+AI</title>
<style>body{{font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;max-width:920px;
margin:30px auto;color:#212529}}h1{{font-size:22px;margin-bottom:4px}}.sub{{color:#868e96;margin-bottom:18px}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #dee2e6;padding:8px 12px;text-align:left}}
th{{background:#f8f9fa}}code{{font-size:13px}}.foot{{color:#868e96;font-size:12px;margin-top:14px}}</style></head><body>
<h1>Методологія ToDo+AI — статус впровадження Odoo 19</h1>
<div class="sub">Наскрізний процес: ІНІЦІАЦІЯ → ДИСКАВЕРІ → ЗАВЕРШЕННЯ → ТР → MVP · {len(stages)} пакетів · {total} скілів</div>
<table><thead><tr><th>#</th><th>Стадія</th><th>Пакет</th><th>Скілів</th><th>Версія</th><th>Статус</th></tr></thead>
<tbody>{rows}</tbody></table>
<div class="foot">Згенеровано <code>генератор_проекцій.py status</code> з <code>СТАТУС_методології.json</code>
+ <code>plugin.json</code> кожного пакета. Проекція — не редагувати руками.</div>
</body></html>"""


# ───────────────────────── P4b · RTM (per-project) ─────────────────────────
AC_RE = re.compile(r"\bAC-(\d{1,3})\b")
ORIGIN_RE = re.compile(r"origin:\s*([^\n)\]]+)", re.I)
TODO_AC_RE = re.compile(r"#\s*TODO:\s*AC-(\d{1,3})")
TEST_AC_RE = re.compile(r"def\s+test_ac(\d{1,3})")


def _read(p):
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def cmd_rtm(proj: pathlib.Path):
    if not proj.exists():
        print(f"🔴 Немає теки проекту: {proj}")
        sys.exit(2)
    ac = {}  # n -> dict(origin, in_tr, in_spec, impl, tests, reg)

    def slot(n):
        return ac.setdefault(n, {"origin": "", "in_tr": False, "in_spec": False,
                                 "impl": [], "tests": [], "reg": ""})

    # ТР
    for f in list(proj.glob("ТР_*.md")) + list(proj.glob("**/ТР_*.md")):
        t = _read(f)
        for ln in t.splitlines():
            ids = AC_RE.findall(ln)
            if ids:
                o = ORIGIN_RE.search(ln)
                for n in ids:
                    s = slot(n); s["in_tr"] = True
                    if o and not s["origin"]:
                        s["origin"] = o.group(1).strip()
    # SPEC
    for f in list(proj.glob("**/SPEC.md")):
        for n in set(AC_RE.findall(_read(f))):
            slot(n)["in_spec"] = True
    # код
    for f in proj.glob("**/*.py"):
        if "test" in f.name:
            continue
        t = _read(f)
        for n in set(TODO_AC_RE.findall(t)) | set(AC_RE.findall(t)):
            slot(n)["impl"].append(f.name)
    # тести
    for f in proj.glob("**/*.py"):
        if "test" not in f.name:
            continue
        for n in set(TEST_AC_RE.findall(_read(f))):
            slot(n)["tests"].append(f.name)
    # реєстр (опційний експорт)
    for f in list(proj.glob("**/*реєстр*.*")) + list(proj.glob("**/registry*.*")):
        t = _read(f)
        for st in ("Виконано", "Погодження клієнта", "Аналіз та підготовка", "Скасовано"):
            if st in t:
                for n in ac:
                    if not ac[n]["reg"]:
                        ac[n]["reg"] = st
                break

    rows, warns = [], []
    for n in sorted(ac, key=int):
        s = ac[n]
        cov = "✓" if s["impl"] and s["tests"] else "⚠️"
        if not s["origin"]:
            warns.append(f"AC-{n}: немає origin (обрив трасування вгору)")
        if not s["tests"]:
            warns.append(f"AC-{n}: немає тесту")
        if (s["impl"] or s["tests"]) and not s["in_tr"]:
            warns.append(f"🔴 AC-{n}: є в коді/тесті, але немає в ТР (drift)")
        rows.append(f"| AC-{n} | {s['origin'] or '—'} | {'✓' if s['in_tr'] else '—'} | "
                    f"{'✓' if s['in_spec'] else '—'} | {', '.join(sorted(set(s['impl']))) or '—'} | "
                    f"{', '.join(sorted(set(s['tests']))) or '—'} | {s['reg'] or '—'} | {cov} |")

    out = proj / f"RTM_{proj.name}.md"
    body = (f"# RTM — матриця трасування вимог · {proj.name}\n\n"
            f"Згенеровано `генератор_проекцій.py rtm`. Рядок = один AC; джерело — артефакти проекту.\n\n"
            "| AC | origin | у ТР | у SPEC | реалізація (файл) | тест(и) | реєстр | покриття |\n"
            "|----|--------|------|--------|-------------------|---------|--------|----------|\n"
            + ("\n".join(rows) if rows else "| — | — | — | — | — | — | — | — |") + "\n")
    if warns:
        body += "\n## Зауваження трасування\n" + "\n".join(f"- {w}" for w in warns) + "\n"
    out.write_text(body, encoding="utf-8")
    print(f"AC знайдено: {len(ac)} · покрито (impl+test): {sum(1 for s in ac.values() if s['impl'] and s['tests'])}")
    print(f"Зауважень: {len(warns)} · RTM → {out}")
    if not ac:
        print("ℹ️ Жодного AC не розпарсено — перевір, що в теці є ТР_*.md/SPEC.md з форматом AC-NN.")


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "status":
        cmd_status()
    elif len(sys.argv) >= 3 and sys.argv[1] == "rtm":
        cmd_rtm(pathlib.Path(sys.argv[2]))
    else:
        print("Використання:\n  генератор_проекцій.py status\n  генератор_проекцій.py rtm <project_dir>")
        sys.exit(2)


if __name__ == "__main__":
    main()
