# Oracle Cloud Free Tier Deployment Guide (Ubuntu 24.04 LTS)

This guide walks you through deploying the Office Coffee Fund platform on an **Oracle Cloud Always Free VM** (Compute instance) using native Docker Compose and HTTPS.

---

## 1. Create your Free VM on Oracle Cloud

1. Log into your **Oracle Cloud Console**.
2. Navigate to **Compute** -> **Instances** -> **Create Instance**.
3. Configure the VM:
   - **Image**: **Canonical Ubuntu 24.04** (Minimal or standard).
   - **Shape**:
     - *Option A (Best)*: **Ampere ARM (VM.Standard.A1.Flex)** — choose 2 to 4 OCPUs and 12 to 24 GB RAM (100% free under the 3,000 OCPU hours / 18,000 GB-hours monthly allowance).
     - *Option B*: **AMD (VM.Standard.E2.1.Micro)** — 1 OCPU, 1 GB RAM (Always Free).
   - **Networking**: Assign a Public IPv4 address.
   - **SSH Keys**: Download your private key (`.key` or `.pem`).
4. Click **Create** and wait 1–2 minutes for the instance status to turn **Running**.

---

## 2. Connect to the Server

Open PowerShell or terminal and SSH into your VM:
```bash
ssh -i /path/to/your-key.key ubuntu@<YOUR_VM_PUBLIC_IP>
```

---

## 3. Clone the Repo & Run Setup

```bash
git clone https://github.com/kexcode/coffee-service.git
cd coffee-service
sudo bash deploy/setup-ubuntu.sh
```

The script automatically:
* Installs the latest Docker Engine and Docker Compose plugin.
* Configures firewall rules.
* Creates the persistent `./data` SQLite database directory.
* Registers a systemd unit (`coffee-service.service`) so your containers auto-start on server reboot.

---

## 4. Configure Environment Variables

Edit `.env`:
```bash
nano .env
```
Ensure your credentials are set:
```ini
BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ
ADMIN_USERNAMES=your_telegram_username
PAYPAL_ME_URL=https://paypal.me/your_paypal_username
MONTHLY_TARGET=150.00
ENVIRONMENT=production
```

---

## 5. Choose your HTTPS Strategy

Telegram Mini Apps strictly require a valid public **HTTPS** URL. You have two options:

### Option A: Cloudflare Named Tunnel (Recommended — No Ports or Domain Needed)
* **Zero Firewall Setup**: You do **not** need to open ports 80/443 in Oracle Cloud Security Lists.
* **Steps**:
  1. Go to your free [Cloudflare Dashboard](https://dash.cloudflare.com) -> **Zero Trust** -> **Networks** -> **Tunnels**.
  2. Click **Create a Tunnel** (e.g. `coffee-server`).
  3. Select **Cloudflared** and copy the tunnel token.
  4. In Cloudflare Public Hostname, route:
     - Subdomain: `coffee` (e.g. `coffee.yourdomain.com`)
     - Service: `HTTP` -> `frontend:80`
  5. Put the token in `.env`:
     ```ini
     TUNNEL_TOKEN=eyJhIjoi...your_token_here...
     WEBAPP_URL=https://coffee.yourdomain.com
     ```
  6. Start the stack:
     ```bash
     docker compose --profile tunnel up -d
     ```

### Option B: Cloudflare Quick Tunnel (Zero Cloudflare Account Required)
If you don't have a Cloudflare account yet:
Leave `TUNNEL_TOKEN` blank in `.env` and run:
```bash
docker compose --profile tunnel up -d
docker compose logs -f tunnel
```
Look for the generated `https://<random>.trycloudflare.com` URL, set it in `.env` as `WEBAPP_URL`, and update your Telegram Menu Button via BotFather or the API.

### Option C: Caddy with Direct Domain (No Tunnel)
If you own a domain (e.g. `coffee.mydomain.com`) pointing directly to your Oracle VM public IP:
1. In Oracle Cloud Console -> Virtual Cloud Network -> Security Lists -> **Add Ingress Rule**:
   - Source: `0.0.0.0/0`, Destination Port: `80,443` (TCP).
2. In `.env`:
   ```ini
   DOMAIN=coffee.mydomain.com
   WEBAPP_URL=https://coffee.mydomain.com
   ACME_EMAIL=your-email@example.com
   ```
3. Start Caddy:
   ```bash
   docker compose --profile caddy up -d
   ```
Caddy will automatically provision and renew a free Let's Encrypt SSL certificate!

---

## 6. Update Telegram Menu Button

To update the Telegram bot's menu button to your new HTTPS URL:
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setChatMenuButton" \
     -H "Content-Type: application/json" \
     -d '{"menu_button": {"type": "web_app", "text": "☕ Coffee Fund", "web_app": {"url": "https://YOUR_NEW_HTTPS_URL"}}}'
```

---

## 7. Useful Commands on the Server

```bash
# View live container logs
docker compose logs -f

# Check status of containers
docker compose ps

# Restart the stack
docker compose restart

# Pull new updates from git
git pull
docker compose build
docker compose up -d
```
