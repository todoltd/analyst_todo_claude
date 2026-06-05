#!/usr/bin/env bash
# =============================================================
# Push на GitHub — git repo вже ініціалізований і має перший коміт.
# Запускай з папки "Методологія ToDo+AI":
#   cd ~/Documents/Claude/Projects/"Методологія ToDo+AI"
#   bash setup_github.sh
# =============================================================
set -e

REMOTE_URL="https://github.com/todoltd/analyst_todo_claude.git"

echo "=== Поточний стан репо ==="
git log --oneline
echo ""

echo "Додаємо remote і пушимо..."
git remote remove origin 2>/dev/null || true
git remote add origin "$REMOTE_URL"
git push -u origin main
echo ""
echo "✅ Готово! https://github.com/todoltd/analyst_todo_claude"
