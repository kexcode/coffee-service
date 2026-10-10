import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, update

from app.config import get_settings
from app.database import async_session_factory
from app.models import User, Donation, Expense, Setting
from app.bot.instance import notify_admins_cash_donation

logger = logging.getLogger(__name__)
settings = get_settings()
router = Router()


class AddExpenseState(StatesGroup):
    waiting_for_category = State()
    waiting_for_amount = State()
    waiting_for_description = State()
    waiting_for_receipt = State()


EXPENSE_CATEGORIES = [
    ("☕ Coffee Beans", "beans"),
    ("📄 Paper & Filters", "filters"),
    ("🧼 Cleaning & Descaling", "cleaning"),
    ("🔧 Maintenance & Repair", "maintenance_repair"),
    ("🏦 Equipment Reserve", "depreciation_reserve"),
]


def get_category_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"exp_cat:{code}")]
        for name, code in EXPENSE_CATEGORIES
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(CommandStart())
async def handle_start(message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username

    # Ensure user is recorded in database
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.tg_id == user_id))
        user = result.scalar_one_or_none()

        role = "admin" if settings.is_admin(user_id) else "user"

        if not user:
            user = User(
                tg_id=user_id,
                first_name=first_name,
                username=username,
                role=role,
                pledge_amount=0.0,
                pledge_active=False,
            )
            session.add(user)
            await session.commit()
        else:
            if settings.is_admin(user_id) and user.role != "admin":
                user.role = "admin"
                await session.commit()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="☕ Open Coffee Dashboard",
                    web_app=WebAppInfo(url=settings.WEBAPP_URL),
                )
            ]
        ]
    )

    welcome_text = (
        f"☕ <b>Welcome to the Office Coffee Community, {first_name}!</b>\n\n"
        f"We share the coffee station together with full transparency:\n"
        f"• <b>Live Treasury:</b> Track current coffee pot funds & expenses\n"
        f"• <b>Monthly Pledges:</b> Soft reminders to keep beans stocked\n"
        f"• <b>Easy Contributions:</b> Support via PayPal or cash jar\n\n"
        f"Tap the button below to launch the Mini App dashboard."
    )

    await message.answer(welcome_text, reply_markup=keyboard)


# =========================================================================
# Cash Approval Callbacks
# =========================================================================

@router.callback_query(F.data.startswith("approve_cash:"))
async def handle_approve_cash(callback: CallbackQuery):
    admin_id = callback.from_user.id
    if not settings.is_admin(admin_id):
        await callback.answer("⚠️ Only coffee admins can confirm cash payments.", show_alert=True)
        return

    donation_id_str = callback.data.split(":")[1]
    if not donation_id_str.isdigit():
        await callback.answer("Invalid donation ID", show_alert=True)
        return
    donation_id = int(donation_id_str)

    async with async_session_factory() as session:
        result = await session.execute(
            select(Donation, User).join(User, Donation.user_id == User.id).where(Donation.id == donation_id)
        )
        row = result.first()
        if not row:
            await callback.answer("Donation not found.", show_alert=True)
            return

        donation, user = row
        if donation.status == "confirmed":
            await callback.answer("Already confirmed!", show_alert=True)
            return

        donation.status = "confirmed"
        await session.commit()

        donor_tg_id = user.tg_id
        amount = donation.amount
        donor_name = user.first_name

    # Edit message to reflect approval
    await callback.message.edit_text(
        f"✅ <b>Cash payment #{donation_id} confirmed!</b>\n\n"
        f"👤 <b>Donor:</b> {donor_name}\n"
        f"💰 <b>Amount:</b> €{amount:.2f}\n"
        f"👑 <b>Confirmed by:</b> {callback.from_user.first_name}",
        reply_markup=None,
    )
    await callback.answer("Payment confirmed!")

    # Try to notify donor
    try:
        if callback.bot and donor_tg_id:
            await callback.bot.send_message(
                chat_id=donor_tg_id,
                text=f"☕ <b>Cash Contribution Confirmed!</b>\n\nYour cash payment of <b>€{amount:.2f}</b> has been received and added to our coffee fund. Thank you!"
            )
    except Exception as e:
        logger.warning(f"Could not notify donor {donor_tg_id}: {e}")


@router.callback_query(F.data.startswith("reject_cash:"))
async def handle_reject_cash(callback: CallbackQuery):
    admin_id = callback.from_user.id
    if not settings.is_admin(admin_id):
        await callback.answer("⚠️ Only coffee admins can reject cash payments.", show_alert=True)
        return

    donation_id_str = callback.data.split(":")[1]
    if not donation_id_str.isdigit():
        await callback.answer("Invalid donation ID", show_alert=True)
        return
    donation_id = int(donation_id_str)

    async with async_session_factory() as session:
        result = await session.execute(
            select(Donation, User).join(User, Donation.user_id == User.id).where(Donation.id == donation_id)
        )
        row = result.first()
        if not row:
            await callback.answer("Donation not found.", show_alert=True)
            return

        donation, user = row
        donation.status = "rejected"
        await session.commit()
        donor_name = user.first_name
        amount = donation.amount

    await callback.message.edit_text(
        f"❌ <b>Cash payment #{donation_id} rejected.</b>\n\n"
        f"👤 <b>Donor:</b> {donor_name}\n"
        f"💰 <b>Amount:</b> €{amount:.2f}\n"
        f"👑 <b>Rejected by:</b> {callback.from_user.first_name}",
        reply_markup=None,
    )
    await callback.answer("Payment rejected.")


# =========================================================================
# Pledge Reminder Actions
# =========================================================================

@router.callback_query(F.data.startswith("cash_pledge:"))
async def handle_cash_pledge(callback: CallbackQuery):
    amount_str = callback.data.split(":")[1]
    try:
        amount = float(amount_str)
    except ValueError:
        amount = 5.0

    user_tg_id = callback.from_user.id
    first_name = callback.from_user.first_name

    async with async_session_factory() as session:
        res = await session.execute(select(User).where(User.tg_id == user_tg_id))
        user = res.scalar_one_or_none()
        if not user:
            user = User(
                tg_id=user_tg_id,
                first_name=first_name,
                username=callback.from_user.username,
                role="user",
                pledge_amount=amount,
                pledge_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        donation = Donation(
            user_id=user.id,
            amount=amount,
            payment_method="cash",
            status="pending",
        )
        session.add(donation)
        await session.commit()
        await session.refresh(donation)
        donation_id = donation.id

    # Notify admins
    await notify_admins_cash_donation(donation_id, first_name, amount)

    await callback.message.edit_text(
        f"☕ <b>Thank you, {first_name}!</b>\n\n"
        f"Your cash payment of <b>€{amount:.2f}</b> has been logged as pending.\n"
        f"Please drop the cash into the coffee jar. An admin has been notified to confirm it!"
    )
    await callback.answer()


@router.callback_query(F.data == "skip_month")
async def handle_skip_month(callback: CallbackQuery):
    await callback.message.edit_text(
        "👍 <b>No worries!</b> You've skipped this month's reminder.\n"
        "Your pledge remains active for next month. Enjoy your coffee! ☕"
    )
    await callback.answer()


# =========================================================================
# Admin FSM: /add_expense
# =========================================================================

@router.message(Command("add_expense"))
async def cmd_add_expense(message: Message, state: FSMContext):
    if not settings.is_admin(message.from_user.id):
        await message.answer("⚠️ You must be a registered coffee admin to use /add_expense.")
        return

    await state.set_state(AddExpenseState.waiting_for_category)
    await message.answer(
        "📝 <b>Record Coffee Station Expense</b>\n\n"
        "Please select the expense category:",
        reply_markup=get_category_keyboard(),
    )


@router.callback_query(AddExpenseState.waiting_for_category, F.data.startswith("exp_cat:"))
async def expense_category_chosen(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":")[1]
    await state.update_data(category=category)
    await state.set_state(AddExpenseState.waiting_for_amount)

    category_label = next((name for name, code in EXPENSE_CATEGORIES if code == category), category)
    await callback.message.edit_text(
        f"Category: <b>{category_label}</b>\n\n"
        f"Now enter the <b>amount in EUR</b> (e.g., <code>18.50</code>):"
    )
    await callback.answer()


@router.message(AddExpenseState.waiting_for_amount)
async def expense_amount_entered(message: Message, state: FSMContext):
    text = message.text.replace(",", ".").strip()
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("⚠️ Please enter a valid positive number for the amount (e.g. <code>15.00</code>):")
        return

    await state.update_data(amount=amount)
    await state.set_state(AddExpenseState.waiting_for_description)
    await message.answer(
        f"Amount: <b>€{amount:.2f}</b>\n\n"
        f"Please enter a short description (e.g., <code>2kg Espresso Beans from Local Roastery</code>):"
    )


@router.message(AddExpenseState.waiting_for_description)
async def expense_description_entered(message: Message, state: FSMContext):
    description = message.text.strip()
    if not description:
        await message.answer("⚠️ Description cannot be empty. Please enter a brief note:")
        return

    await state.update_data(description=description)
    await state.set_state(AddExpenseState.waiting_for_receipt)

    skip_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Skip Receipt", callback_data="skip_receipt")]]
    )
    await message.answer(
        f"Description: <b>{description}</b>\n\n"
        f"Optionally send a receipt URL or tap 'Skip Receipt':",
        reply_markup=skip_keyboard,
    )


@router.callback_query(AddExpenseState.waiting_for_receipt, F.data == "skip_receipt")
async def expense_receipt_skipped(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await save_and_confirm_expense(callback.message, state, data, receipt_url=None, admin_id=callback.from_user.id)
    await callback.answer()


@router.message(AddExpenseState.waiting_for_receipt)
async def expense_receipt_entered(message: Message, state: FSMContext):
    receipt_url = message.text.strip() if message.text else None
    data = await state.get_data()
    await save_and_confirm_expense(message, state, data, receipt_url=receipt_url, admin_id=message.from_user.id)


async def save_and_confirm_expense(
    target_msg: Message,
    state: FSMContext,
    data: dict,
    receipt_url: str | None,
    admin_id: int,
):
    category = data["category"]
    amount = data["amount"]
    description = data["description"]

    async with async_session_factory() as session:
        expense = Expense(
            category=category,
            amount=amount,
            description=description,
            receipt_url=receipt_url,
            created_by=admin_id,
        )
        session.add(expense)
        await session.commit()
        await session.refresh(expense)
        expense_id = expense.id

    await state.clear()

    category_label = next((name for name, code in EXPENSE_CATEGORIES if code == category), category)
    text = (
        f"✅ <b>Expense #{expense_id} Recorded!</b>\n\n"
        f"📂 <b>Category:</b> {category_label}\n"
        f"💶 <b>Amount:</b> €{amount:.2f}\n"
        f"📝 <b>Description:</b> {description}\n"
    )
    if receipt_url:
        text += f"🧾 <b>Receipt:</b> {receipt_url}\n"

    await target_msg.answer(text)
