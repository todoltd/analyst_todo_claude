#!/usr/bin/env bash
# =============================================================
# ToDo Team Setup — автосинхронізація з GitHub
# Запуск один раз: bash team_setup.sh
# =============================================================

REPO_URL="https://github.com/todoltd/analyst_todo_claude.git"
LOCAL_DIR="$HOME/Documents/ToDo Projects"
PLIST_NAME="com.todo.git-sync"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"
PULL_SCRIPT="$LOCAL_DIR/.auto_pull.sh"

echo "=============================="
echo " ToDo Projects — Auto Sync"
echo "=============================="
echo ""

# 1. Клонуємо репо або оновлюємо якщо вже є
if [ -d "$LOCAL_DIR/.git" ]; then
  echo "📁 Папка вже існує — оновлюємо..."
  git -C "$LOCAL_DIR" pull
else
  echo "📥 Клонуємо репо в: $LOCAL_DIR"
  git clone "$REPO_URL" "$LOCAL_DIR"
fi

echo ""
echo "⚙️  Налаштовуємо автосинхронізацію кожні 30 хвилин..."

# 2. Створюємо скрипт для pull
cat > "$PULL_SCRIPT" << 'EOF'
#!/bin/bash
LOCAL_DIR="$HOME/Documents/ToDo Projects"
LOG="$LOCAL_DIR/.sync.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Pulling..." >> "$LOG"
git -C "$LOCAL_DIR" pull --ff-only >> "$LOG" 2>&1
# Тримаємо лише останні 100 рядків логу
tail -100 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
EOF
chmod +x "$PULL_SCRIPT"

# 3. Встановлюємо LaunchAgent (macOS планувальник)
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$PLIST_NAME</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$PULL_SCRIPT</string>
  </array>
  <key>StartInterval</key>
  <integer>1800</integer>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$LOCAL_DIR/.sync.log</string>
  <key>StandardErrorPath</key>
  <string>$LOCAL_DIR/.sync.log</string>
</dict>
</plist>
EOF

# 4. Активуємо (вивантажуємо старий якщо є, завантажуємо новий)
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo ""
echo "✅ Готово!"
echo ""
echo "   📁 Папка з файлами: $LOCAL_DIR"
echo "   🔄 Автооновлення: кожні 30 хвилин"
echo "   📋 Лог синхронізації: $LOCAL_DIR/.sync.log"
echo ""
echo "Щоб перевірити лог:"
echo "   cat \"$LOCAL_DIR/.sync.log\""
echo ""
echo "Щоб зупинити автосинхронізацію:"
echo "   launchctl unload ~/Library/LaunchAgents/$PLIST_NAME.plist"
