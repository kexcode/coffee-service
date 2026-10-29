import logging
from typing import Optional
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

bot: Optional[Bot] = None
dp: Optional[Dispatcher] = None

if settings.BOT_TOKEN:
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
else:
    logger.warning("BOT_TOKEN is not configured. Telegram bot features will be inactive.")


def get_admin_approval_keyboard(donation_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Confirm", callback_data=f"approve_cash:{donation_id}"),
                InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_cash:{donation_id}"),
            ]
        ]
    )


async def notify_admins_cash_donation(donation_id: int, user_first_name: str, amount: float):
    """
    Sends notification to all configured admins when a cash donation is logged.
    """
    if not bot:
        logger.info(f"Mock Notification: Admin alert for cash payment #{donation_id}: {user_first_name} paid €{amount:.2f}")
        return

    admin_ids = set(settings.admin_id_list)
    try:
        from app.database import async_session_factory
        from app.models import User
        from sqlalchemy import select
        async with async_session_factory() as session:
            res = await session.execute(select(User.tg_id).where(User.role == "admin"))
            for uid in res.scalars().all():
                admin_ids.add(uid)
    except Exception as e:
        logger.error(f"Error fetching admin IDs from DB: {e}")

    if not admin_ids:
        logger.warning("No admin Telegram IDs found to notify.")
        return

    text = (
        f"💵 <b>Cash payment logged</b>\n\n"
        f"👤 <b>Contributor:</b> {user_first_name}\n"
        f"💰 <b>Amount:</b> €{amount:.2f}\n"
        f"🆔 <b>Donation ID:</b> #{donation_id}\n\n"
        f"Please confirm if you received the money in the cash jar."
    )
    keyboard = get_admin_approval_keyboard(donation_id)

    for admin_id in admin_ids:
        try:
            await bot.send_message(chat_id=admin_id, text=text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Failed to send admin notification to {admin_id}: {e}")


async def notify_user_verified(tg_id: int):
    """
    Sends a congratulatory notification to a user when their membership is verified by an admin.
    """
    if not bot or not tg_id:
        return
    try:
        from aiogram.types import WebAppInfo
        webapp_url = settings.live_webapp_url
        keyboard = None
        if webapp_url.startswith("https://"):
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="☕ Open Coffee Dashboard",
                            web_app=WebAppInfo(url=webapp_url),
                        )
                    ]
                ]
            )
        text = (
            "🎉 <b>You are verified!</b>\n\n"
            "An administrator has verified your office coffee community membership.\n"
            "You now have full access to view the live treasury pot, spending breakdown, and audit feed."
        )
        await bot.send_message(chat_id=tg_id, text=text, reply_markup=keyboard)
    except Exception as e:
        logger.warning(f"Could not send verification notification to tg_id {tg_id}: {e}")
