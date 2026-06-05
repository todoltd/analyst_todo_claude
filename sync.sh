#!/usr/bin/env bash
# Синхронізація Projects → GitHub
# Запуск: bash sync.sh "опис змін"
cd "$(dirname "$0")"

MESSAGE="${1:-update: $(date '+%Y-%m-%d %H:%M')}"

echo "📦 Збираємо зміни..."
git add -A

CHANGED=$(git diff --cached --name-only | wc -l | tr -d ' ')
if [ "$CHANGED" = "0" ]; then
  echo "✅ Немає змін для push"
  exit 0
fi

echo "📝 Змінено файлів: $CHANGED"
git diff --cached --name-only | head -10

git commit -m "$MESSAGE" 2>/dev/null || true

echo "🚀 Пушимо..."
git push 2>&1 | grep -v "warning:"
echo "✅ Готово"
