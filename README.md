# Office Coffee Fund Tracker & Donation Platform ☕

An artisanal, full-stack Office Coffee Fund Tracker & Telegram Mini App designed for office communities. Built around a **shared community treasury**, **full transparency of expenditures**, **soft monthly subscription reminders**, and **trust-based cash logging with admin confirmation**.

---

## 🌟 Key Features

1. **Shared Community Treasury Dashboard**:
   - Live fund balance readout with status alerts (healthy, low reserve, empty).
   - Monthly target progress meter (`€X of €150.00` goal).
   - Monthly collections & expense velocity.

2. **Quick Contribution Flow**:
   - Preset amounts (€5, €10, €15, €20, or custom amount).
   - Direct **PayPal.me** link integration.
   - **Trust-based Cash Jar logging**: Contributors tap *"I Dropped €X in Cash Jar"*, which records a pending payment and pings the Coffee Admins in Telegram for confirmation.

3. **Soft Monthly Subscriptions (Pledges)**:
   - Voluntary monthly commitment (e.g. €10/month).
   - **Automated APScheduler Cron Job** (runs on the 1st of every month at 10:00 AM).
   - Sends interactive Telegram reminder:
     ```text
     ☕ New month, fresh coffee! Your active monthly pledge is €10.00. Ready to support our coffee pot?
     [Pay via PayPal] | [Paid in Cash] | [Skip this month]
     ```

4. **1-Click Admin Cash Approvals**:
   - Real-time alert dispatched to all admins when cash is logged:
     ```text
     💵 Cash payment logged: Alice paid €10.00. Confirm receipt?
     [✅ Confirm] | [❌ Reject]
     ```
   - Admins can also review and confirm cash payments directly inside the Mini App Admin panel.

5. **Transparency & Audit Feed**:
   - Audit trail of all community donations and station expenses.
   - Categorized expenditures (Beans, Filters, Cleaning, Maintenance, Equipment Reserve).
   - Digital receipt links and itemized notes.

---

## 🛠 Tech Stack

- **Backend**: Python 3.11+, FastAPI, aiogram 3.x, APScheduler 3.x, SQLAlchemy 2.0 (async), Pydantic v2.
- **Database**: SQLite via `aiosqlite` (stored persistently in `./data/coffee.db`).
- **Frontend**: React 18, Vite, Tailwind CSS, Lucide-react icons, `@twa-dev/sdk`.
  - Palette: Dark espresso (`#2b1810`), warm cream (`#fbf7ee`), latte (`#b08968`), amber badges.
- **Deployment**: Docker, Multi-stage Nginx container, Docker Compose, Cloudflare Quick Tunnel.

---

## 🚀 Quick Start (Local Docker Compose)

### 1. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Fill in your details:
```env
BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ  # From @BotFather
ADMIN_TG_IDS=123456789                           # Your Telegram numeric user ID
WEBAPP_URL=http://localhost:3000                 # Or your HTTPS tunnel URL
PAYPAL_ME_URL=https://paypal.me/yourcoffee       # Your team's PayPal.me link
MONTHLY_TARGET=150.00                            # Monthly goal in EUR
ENVIRONMENT=development
```

### 2. Launch Services
Run backend and frontend containers:
```bash
docker compose up -d
```
- **Web Dashboard / Mini App**: [http://localhost:3000](http://localhost:3000)
- **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Database**: Stored in `./data/coffee.db`

### 3. (Optional) Run with Free Public HTTPS Tunnel
Telegram Mini Apps require HTTPS when opened inside the mobile Telegram app. You can generate an instant, zero-configuration Cloudflare tunnel:
```bash
docker compose --profile tunnel up
```
Check the terminal output for the public URL:
```text
https://random-subdomain.trycloudflare.com
```
Set this URL in [@BotFather](https://t.me/BotFather) under your bot's Mini App URL settings (`/newapp` or `/setmenubutton`).

---

## 🤖 Telegram Bot Commands

- `/start`: Welcomes users and opens the interactive Mini App dashboard via inline WebApp button.
- `/add_expense`: Interactive FSM wizard for admins to record new coffee bean purchases, milk, descaling kits, or repairs with category picker and receipt link.

---

## 🧪 Running Tests Locally

### Backend Unit & Integration Tests:
```bash
cd backend
pytest tests -v
```

### Frontend TypeScript Compilation & Build:
```bash
cd frontend
npm install
npm run build
```

---

## 📂 Project Architecture

```
coffee-service/
├── docker-compose.yml           # Multi-container orchestration
├── .env.example                 # Environment configuration template
├── backend/
│   ├── Dockerfile               # Python 3.11-slim container
│   ├── requirements.txt         # FastAPI, aiogram, SQLAlchemy, APScheduler
│   ├── pytest.ini               # Pytest async configuration
│   ├── app/
│   │   ├── main.py              # FastAPI app & unified lifespan
│   │   ├── config.py            # Pydantic Settings
│   │   ├── database.py          # SQLAlchemy 2.0 async engine & sessions
│   │   ├── models.py            # User, Expense, Donation, Setting models
│   │   ├── schemas.py           # Pydantic v2 schemas
│   │   ├── auth.py              # Telegram Mini App HMAC-SHA256 validator
│   │   ├── bot/
│   │   │   ├── instance.py      # Bot & Dispatcher setup + Admin alerts
│   │   │   ├── handlers.py      # /start, /add_expense FSM, cash callbacks
│   │   │   └── scheduler.py     # APScheduler monthly pledge cron job
│   │   └── routers/
│   │       ├── dashboard.py     # /api/dashboard & /api/feed
│   │       ├── donations.py     # /api/donations/cash & /api/pledge
│   │       └── admin.py         # /api/admin/* (expenses, approvals, settings)
│   └── tests/
│       ├── test_auth.py         # HMAC validation & tampering tests
│       └── test_api.py          # Dashboard balance & flow tests
└── frontend/
    ├── Dockerfile               # Multi-stage build (Node 20 -> Nginx)
    ├── nginx.conf               # SPA routing & API reverse proxy
    ├── package.json
    ├── tailwind.config.js       # Artisanal coffee palette
    └── src/
        ├── App.tsx              # Tab layout (Pot, Spend, Audit, Admin)
        ├── hooks/useTelegram.ts # @twa-dev/sdk integration & haptics
        ├── services/api.ts      # Backend API client with TMA auth headers
        └── components/
            ├── Header.tsx           # Coffee Pot header & role status
            ├── TargetProgress.tsx   # Treasury balance & monthly goal meter
            ├── QuickActions.tsx     # Direct PayPal & Contribute buttons
            ├── ContributeModal.tsx  # Preset amounts & cash jar trigger
            ├── PledgeCard.tsx       # Soft monthly pledge reminder toggle
            ├── CategoryBreakdown.tsx# Spend distribution stacked bar
            ├── TransparencyFeed.tsx # Audit log with item filters
            └── AdminPanel.tsx       # Cash approvals & expense logger
```
