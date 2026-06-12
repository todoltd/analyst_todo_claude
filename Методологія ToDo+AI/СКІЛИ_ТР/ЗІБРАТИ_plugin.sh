#!/usr/bin/env bash
# Збірка плагіна odoo19-tr-authoring. Версія береться з .claude-plugin/plugin.json.
# Запуск з macOS:  cd "СКІЛИ_ТР" && bash ЗІБРАТИ_plugin.sh
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
VER="$(python3 -c "import json;print(json.load(open('$HERE/.claude-plugin/plugin.json'))['version'])")"
OUT="$HERE/../odoo19-tr-authoring-$VER.plugin"
cd "$HERE"
find . -name ".DS_Store" -delete 2>/dev/null || true
rm -f "$OUT"
zip -r -X "$OUT" skills .claude-plugin README.md -x "*.DS_Store"
echo "Готово: $OUT"
echo "Скілів у архіві: $(unzip -l "$OUT" | grep -c SKILL.md)"
echo "Нагадування: інсталяційну картку дає .plugin, доставлений через папку outputs сесії Cowork."
