#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "=================================================================="
echo "🚀 Office Coffee Fund — One-Command CI/CD Deployment Pipeline"
echo "📅 Timestamp: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "📂 Directory: $PROJECT_ROOT"
echo "=================================================================="

# ------------------------------------------------------------------
# 1. Database Backup
# ------------------------------------------------------------------
echo ""
echo "💾 [1/6] Backing up SQLite database..."
mkdir -p "$PROJECT_ROOT/data/backups"
if [ -f "$PROJECT_ROOT/data/coffee.db" ]; then
  BACKUP_FILE="$PROJECT_ROOT/data/backups/coffee_$(date -u '+%Y%m%d_%H%M%S').db"
  cp -f "$PROJECT_ROOT/data/coffee.db" "$BACKUP_FILE"
  # Retain last 10 backups
  ls -1t "$PROJECT_ROOT/data/backups"/coffee_*.db 2>/dev/null | tail -n +11 | xargs -r rm -f
  echo "✅ Database backed up to: $BACKUP_FILE"
else
  echo "ℹ️ No existing coffee.db found; a fresh database will be initialized."
fi

# ------------------------------------------------------------------
# 2. Git Code Synchronization
# ------------------------------------------------------------------
echo ""
echo "📥 [2/6] Pulling latest code from GitHub (origin/main)..."
git fetch origin main
LOCAL_SHA=$(git rev-parse --short HEAD)
REMOTE_SHA=$(git rev-parse --short origin/main)
git reset --hard origin/main
sed -i 's/\r$//' "$PROJECT_ROOT"/deploy/*.sh 2>/dev/null || true
chmod +x "$PROJECT_ROOT"/deploy/*.sh 2>/dev/null || true
echo "✅ Repository synced ($LOCAL_SHA -> $REMOTE_SHA)"

# ------------------------------------------------------------------
# 3. Cloudflare Tunnel & WebApp URL Sync
# ------------------------------------------------------------------
echo ""
echo "🌐 [3/6] Verifying Cloudflare HTTPS Tunnel & syncing WebApp URL..."
if systemctl list-unit-files | grep -q "^coffee-tunnel.service"; then
  if ! systemctl is-active --quiet coffee-tunnel.service; then
    echo "🔄 Starting coffee-tunnel.service..."
    sudo systemctl start coffee-tunnel.service
  fi
fi
bash "$PROJECT_ROOT/deploy/tunnel-sync.sh"

# ------------------------------------------------------------------
# 4. Build & Recreate Docker Containers
# ------------------------------------------------------------------
echo ""
echo "🐳 [4/6] Building and deploying Docker containers..."
docker compose build
docker compose up -d --force-recreate --remove-orphans

echo "⏳ Waiting for coffee_backend to become healthy..."
for i in $(seq 1 30); do
  STATUS=$(docker inspect --format='{{.State.Health.Status}}' coffee_backend 2>/dev/null || echo "starting")
  if [ "$STATUS" = "healthy" ]; then
    echo "✅ coffee_backend is healthy!"
    break
  fi
  sleep 2
done

# ------------------------------------------------------------------
# 5. Automated CI Test Suite (pytest inside container)
# ------------------------------------------------------------------
echo ""
echo "🧪 [5/6] Running automated backend test suite (pytest)..."
docker exec coffee_backend python -m pytest tests/ -v

# ------------------------------------------------------------------
# 6. End-to-End Smoke Verification
# ------------------------------------------------------------------
echo ""
echo "🔍 [6/6] Running End-to-End Smoke Checks..."

BACKEND_HEALTH=$(curl -sf http://127.0.0.1:8001/api/health)
echo "  ✔ Backend API (127.0.0.1:8001):  $BACKEND_HEALTH"

FRONTEND_HEALTH=$(curl -sf http://127.0.0.1:3000/api/health)
echo "  ✔ Frontend Proxy (127.0.0.1:3000): $FRONTEND_HEALTH"

FRONTEND_HTTP=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3000/)
echo "  ✔ Frontend SPA HTTP Status:       $FRONTEND_HTTP"

TUNNEL_URL=""
if [ -f "$PROJECT_ROOT/data/webapp_url.txt" ]; then
  TUNNEL_URL=$(cat "$PROJECT_ROOT/data/webapp_url.txt" | tr -d '\r\n')
fi

if [ -n "$TUNNEL_URL" ]; then
  PUBLIC_HEALTH=$(curl -sf "$TUNNEL_URL/api/health" || echo "UNREACHABLE")
  PUBLIC_HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$TUNNEL_URL/" || echo "000")
  echo "  ✔ Public Tunnel ($TUNNEL_URL):"
  echo "      - SPA HTTP Status: $PUBLIC_HTTP"
  echo "      - /api/health:     $PUBLIC_HEALTH"
fi

if [ -f "$PROJECT_ROOT/.env" ]; then
  BOT_TOKEN=$(grep "^BOT_TOKEN=" "$PROJECT_ROOT/.env" | cut -d '=' -f2- | tr -d '\r"' || true)
  if [ -n "$BOT_TOKEN" ]; then
    BOT_ME=$(curl -sf "https://api.telegram.org/bot${BOT_TOKEN}/getMe" || echo "{}")
    MENU_BTN=$(curl -sf "https://api.telegram.org/bot${BOT_TOKEN}/getChatMenuButton" || echo "{}")
    echo "  ✔ Telegram Bot API:"
    echo "      - getMe:           $BOT_ME"
    echo "      - MenuButton:      $MENU_BTN"
  fi
fi

echo ""
echo "=================================================================="
echo "🎉 CI/CD Deployment Complete! Commit: $(git rev-parse --short HEAD)"
echo "🔗 Public WebApp URL: ${TUNNEL_URL:-N/A}"
echo "=================================================================="
