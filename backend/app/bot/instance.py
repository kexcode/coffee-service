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

    admin_ids = settings.admin_id_list
    if not admin_ids:
        logger.warning("No admin Telegram IDs configured in ADMIN_TG_IDS to notify.")
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
