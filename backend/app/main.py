import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.config import get_settings
from app.database import engine, Base, async_session_factory
from app.models import Setting, User
from app.bot.instance import bot, dp
from app.bot.handlers import router as bot_router
from app.bot.scheduler import setup_scheduler, scheduler
from app.routers import dashboard, donations, admin

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Schema migration check: ensure is_verified column exists
        columns_res = await conn.execute(text("PRAGMA table_info(users)"))
        column_names = [row[1] for row in columns_res.fetchall()]
        if "is_verified" not in column_names:
            await conn.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 0"))
            logger.info("Migrated SQLite schema: added is_verified column to users table.")

    # Pre-seed initial settings and admins if not present
    async with async_session_factory() as session:
        # monthly_target
        res = await session.execute(select(Setting).where(Setting.key == "monthly_target"))
        if not res.scalar_one_or_none():
            session.add(Setting(key="monthly_target", value=str(settings.MONTHLY_TARGET)))

        # paypal_me_url
        res = await session.execute(select(Setting).where(Setting.key == "paypal_me_url"))
        if not res.scalar_one_or_none():
            session.add(Setting(key="paypal_me_url", value=settings.PAYPAL_ME_URL))

        # Check configured admins
        for admin_id in settings.admin_id_list:
            res = await session.execute(select(User).where(User.tg_id == admin_id))
            admin_user = res.scalar_one_or_none()
            if admin_user:
                admin_user.role = "admin"
                admin_user.is_verified = True
            else:
                session.add(
                    User(
                        tg_id=admin_id,
                        first_name="Admin",
                        role="admin",
                        is_verified=True,
                        pledge_amount=0.0,
                        pledge_active=False,
                    )
                )

        # Ensure all existing admins are marked as verified
        admins_res = await session.execute(select(User).where(User.role == "admin"))
        for adm in admins_res.scalars().all():
            adm.is_verified = True

        # Ensure Anonymous system user exists (tg_id = 0)
        anon_res = await session.execute(select(User).where(User.tg_id == 0))
        anon_user = anon_res.scalar_one_or_none()
        if not anon_user:
            session.add(
                User(
                    tg_id=0,
                    first_name="Anonymous",
                    username="anonymous",
                    role="user",
                    is_verified=True,
                    pledge_amount=0.0,
                    pledge_active=False,
                )
            )

        await session.commit()
    logger.info("Database schema initialized and default settings verified.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Office Coffee Fund Backend...")
    await init_db()

    # Start APScheduler
    setup_scheduler()
    scheduler.start()
    logger.info("Monthly pledge scheduler started.")

    bot_poll_task = None
    if bot and dp:
        dp.include_router(bot_router)
        logger.info("Starting Telegram Bot polling in background...")
        # Start bot polling task
        bot_poll_task = asyncio.create_task(dp.start_polling(bot))
    else:
        logger.info("Running in web-only mode without live Telegram Bot polling.")

    yield

    logger.info("Shutting down Office Coffee Fund Backend...")
    scheduler.shutdown(wait=False)

    if bot and dp and bot_poll_task:
        await dp.stop_polling()
        await bot.session.close()
        bot_poll_task.cancel()
        try:
            await bot_poll_task
        except asyncio.CancelledError:
            pass

    await engine.dispose()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="Office Coffee Fund Tracker API",
    version="1.0.0",
    description="Community treasury, transparency feed, trust-based cash logging, and soft pledge reminders.",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(dashboard.router)
app.include_router(donations.router)
app.include_router(admin.router)


@app.get("/api/health")
async def healthcheck():
    return {
        "status": "healthy",
        "service": "coffee-service",
        "bot_active": bool(bot is not None),
        "scheduler_running": scheduler.running,
    }
