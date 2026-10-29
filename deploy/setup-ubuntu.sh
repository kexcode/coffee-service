#!/usr/bin/env bash
set -euo pipefail

echo "========================================================"
echo "☕ Office Coffee Fund - Ubuntu 24.04 LTS Deploy Setup"
echo "========================================================"

# 1. Check root or sudo
if [ "$EUID" -ne 0 ]; then
  echo "⚠️ Please run as root or with sudo: sudo bash deploy/setup-ubuntu.sh"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "📂 Project root: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

# 2. Update system packages
echo "📦 Updating system packages..."
apt-get update -y
apt-get install -y ca-certificates curl gnupg git ufw

# 3. Install Docker from official repository if not present
if ! command -v docker &> /dev/null; then
  echo "🐳 Installing Docker Engine and Compose plugin..."
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc

  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null

  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
  echo "✅ Docker installed successfully."
else
  echo "✅ Docker is already installed."
fi

# 4. Configure firewall (Oracle Cloud Ubuntu iptables)
echo "🛡️ Configuring network rules for ports 80 & 443..."
if command -v iptables &> /dev/null; then
  iptables -I INPUT 1 -p tcp --dport 80 -j ACCEPT || true
  iptables -I INPUT 1 -p tcp --dport 443 -j ACCEPT || true
  # Persist iptables if iptables-persistent is installed
  if command -v netfilter-persistent &> /dev/null; then
    netfilter-persistent save || true
  fi
fi

# 5. Create persistent data directory
mkdir -p "$PROJECT_ROOT/data"
chmod 777 "$PROJECT_ROOT/data"

# 6. Check .env file
if [ ! -f "$PROJECT_ROOT/.env" ]; then
  if [ -f "$PROJECT_ROOT/.env.example" ]; then
    echo "📝 Creating .env from .env.example..."
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    echo "⚠️ Created .env file. Please review and add your BOT_TOKEN and settings."
  fi
fi

# 7. Create systemd unit for automatic reboot recovery of Docker stack
echo "⚙️ Creating systemd service coffee-service.service..."
cat << 'EOF' > /etc/systemd/system/coffee-service.service
[Unit]
Description=Office Coffee Fund Docker Stack
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/coffee-service
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down

[Install]
WantedBy=multi-user.target
EOF

# Update WorkingDirectory in unit file to match current path
sed -i "s|WorkingDirectory=/opt/coffee-service|WorkingDirectory=$PROJECT_ROOT|g" /etc/systemd/system/coffee-service.service
systemctl daemon-reload
systemctl enable coffee-service.service

# 8. Create systemd unit for Cloudflare Quick Tunnel (if cloudflared is installed on host)
if command -v cloudflared &> /dev/null; then
  echo "🌐 Creating systemd service coffee-tunnel.service for HTTPS tunnel..."
  cat << 'EOF' > /etc/systemd/system/coffee-tunnel.service
[Unit]
Description=Cloudflare Tunnel for Coffee Service
After=network.target coffee-service.service

[Service]
Type=simple
User=ubuntu
ExecStartPre=-/bin/rm -f /home/ubuntu/cloudflared-coffee.log
ExecStart=/usr/bin/cloudflared tunnel --url http://127.0.0.1:3000 --logfile /home/ubuntu/cloudflared-coffee.log
ExecStartPost=/bin/bash /opt/coffee-service/deploy/tunnel-sync.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
  sed -i "s|/opt/coffee-service|$PROJECT_ROOT|g" /etc/systemd/system/coffee-tunnel.service
  systemctl daemon-reload
  systemctl enable coffee-tunnel.service
  echo "✅ Cloudflare tunnel service created and enabled."
fi

# 9. Register global coffee-deploy command
chmod +x "$PROJECT_ROOT/deploy/deploy.sh" "$PROJECT_ROOT/deploy/tunnel-sync.sh" 2>/dev/null || true
ln -sf "$PROJECT_ROOT/deploy/deploy.sh" /usr/local/bin/coffee-deploy
echo "✅ Registered 'coffee-deploy' command in /usr/local/bin/coffee-deploy"

echo "========================================================"
echo "🎉 Setup complete!"
echo "Next steps:"
echo "1. Verify .env settings: nano .env"
echo "2. Start stack: systemctl start coffee-service.service"
echo "3. If using quick tunnel: systemctl start coffee-tunnel.service"
echo "========================================================"
