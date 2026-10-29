#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/home/ubuntu/cloudflared-coffee.log"
ENV_FILE="$PROJECT_ROOT/.env"
DATA_DIR="$PROJECT_ROOT/data"
URL_FILE="$DATA_DIR/webapp_url.txt"

mkdir -p "$DATA_DIR"

echo "⏳ Waiting for Cloudflare Quick Tunnel URL in $LOG_FILE..."
TUNNEL_URL=""
for i in $(seq 1 30); do
  if [ -f "$LOG_FILE" ]; then
    TUNNEL_URL=$(grep -o 'https://[-a-z0-9.]*trycloudflare.com' "$LOG_FILE" | tail -n 1 || true)
    if [ -n "$TUNNEL_URL" ]; then
      break
    fi
  fi
  sleep 1
done

if [ -z "$TUNNEL_URL" ]; then
  echo "⚠️ Could not detect Cloudflare Tunnel URL within 30s."
  exit 0
fi

echo "✅ Detected Live HTTPS Tunnel URL: $TUNNEL_URL"

# 1. Write to shared volume file so coffee_backend sees it immediately without restart
echo "$TUNNEL_URL" > "$URL_FILE"
chmod 644 "$URL_FILE" || true

# 2. Update WEBAPP_URL in .env
if [ -f "$ENV_FILE" ]; then
  if grep -q "^WEBAPP_URL=" "$ENV_FILE"; then
    sed -i "s|^WEBAPP_URL=.*|WEBAPP_URL=$TUNNEL_URL|g" "$ENV_FILE"
  else
    echo "WEBAPP_URL=$TUNNEL_URL" >> "$ENV_FILE"
  fi
fi

# 3. Update Telegram Bot Menu Button via Telegram API
if [ -f "$ENV_FILE" ]; then
  BOT_TOKEN=$(grep "^BOT_TOKEN=" "$ENV_FILE" | cut -d '=' -f2- | tr -d '\r"' || true)
  if [ -n "$BOT_TOKEN" ]; then
    echo "🤖 Syncing Telegram Menu Button to $TUNNEL_URL..."
    curl -sS -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setChatMenuButton" \
      -H "Content-Type: application/json" \
      -d "{\"menu_button\":{\"type\":\"web_app\",\"text\":\"☕ Coffee Pot\",\"web_app\":{\"url\":\"${TUNNEL_URL}\"}}}" > /dev/null || true
    echo "✅ Telegram Menu Button synced."
  fi
fi
