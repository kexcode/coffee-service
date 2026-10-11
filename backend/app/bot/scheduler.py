import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select

from app.config import get_settings
from app.database import async_session_factory
from app.models import User, Setting
from app.bot.instance import bot

logger = logging.getLogger(__name__)
settings = get_settings()

scheduler = AsyncIOScheduler()


async def get_paypal_url() -> str:
    async with async_session_factory() as session:
        res = await session.execute(select(Setting).where(Setting.key == "paypal_me_url"))
        item = res.scalar_one_or_none()
        if item and item.value:
            return item.value
    return settings.PAYPAL_ME_URL


async def send_monthly_pledge_reminders():
    """
    Cron job triggered on the 1st of every month at 10:00 AM.
    Sends friendly reminder to all active pledgers.
    """
    logger.info("Executing monthly coffee pledge reminder cron job...")
    if not bot:
        logger.warning("Bot is not initialized, skipping reminder dispatch.")
        return

    paypal_url = await get_paypal_url()

    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.pledge_active == True, User.pledge_amount > 0)
        )
        active_users = result.scalars().all()

    logger.info(f"Found {len(active_users)} active coffee pledgers.")

    for user in active_users:
        amount = user.pledge_amount
        user_paypal_url = paypal_url

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="💳 Pay via PayPal", url=user_paypal_url),
                ],
                [
                    InlineKeyboardButton(text="💵 Paid in Cash", callback_data=f"cash_pledge:{amount}"),
                    InlineKeyboardButton(text="⏭ Skip this month", callback_data="skip_month"),
                ],
            ]
        )

        message_text = (
            f"☕ <b>New month, fresh coffee!</b>\n\n"
            f"Hey {user.first_name}! Your active monthly pledge is <b>€{amount:.2f}</b>.\n"
            f"Ready to support our shared coffee pot for this month?"
        )

        try:
            await bot.send_message(
                chat_id=user.tg_id,
                text=message_text,
                reply_markup=keyboard,
            )
            logger.info(f"Sent monthly reminder to {user.first_name} (tg_id: {user.tg_id})")
        except Exception as e:
            logger.error(f"Failed to send monthly reminder to {user.first_name} ({user.tg_id}): {e}")


def setup_scheduler():
    """
    Configures cron job for the 1st of every month at 10:00 AM.
    """
    scheduler.add_job(
        send_monthly_pledge_reminders,
        CronTrigger(day=1, hour=10, minute=0),
        id="monthly_coffee_pledge_reminder",
        replace_existing=True,
    )
    return scheduler
