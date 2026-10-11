from datetime import datetime, timezone
from typing import List, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.auth import get_current_user
from app.config import get_settings, Settings
from app.database import get_db
from app.models import User, Donation, Expense, Setting
from app.schemas import DashboardOut, FeedItem, UserOut

router = APIRouter(prefix="/api", tags=["Dashboard & Feed"])

ALL_CATEGORIES = ["beans", "sweets", "filters", "cleaning", "maintenance_repair", "depreciation_reserve"]



@router.get("/user/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/dashboard", response_model=DashboardOut)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    # PayPal link setting
    paypal_res = await db.execute(select(Setting).where(Setting.key == "paypal_me_url"))
    paypal_setting = paypal_res.scalar_one_or_none()
    paypal_me_url = paypal_setting.value if paypal_setting else settings.PAYPAL_ME_URL

    is_verified_member = bool(current_user.is_verified or current_user.role == "admin")

    # If user is not verified, return restricted dashboard with donation capabilities intact
    if not is_verified_member:
        return DashboardOut(
            is_verified=False,
            total_balance=0.0,
            monthly_target=0.0,
            monthly_collected=0.0,
            monthly_expenses=0.0,
            total_donations=0.0,
            total_expenses=0.0,
            active_pledgers_count=0,
            total_pledged_monthly=0.0,
            category_breakdown={cat: 0.0 for cat in ALL_CATEGORIES},
            paypal_me_url=paypal_me_url,
        )

    # Total confirmed donations
    donations_total_res = await db.execute(
        select(func.coalesce(func.sum(Donation.amount), 0.0)).where(Donation.status == "confirmed")
    )
    total_donations = float(donations_total_res.scalar() or 0.0)

    # Total expenses
    expenses_total_res = await db.execute(
        select(func.coalesce(func.sum(Expense.amount), 0.0))
    )
    total_expenses = float(expenses_total_res.scalar() or 0.0)

    total_balance = total_donations - total_expenses

    # Current month start datetime (UTC)
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    # Monthly collected (confirmed)
    month_donations_res = await db.execute(
        select(func.coalesce(func.sum(Donation.amount), 0.0)).where(
            and_(
                Donation.status == "confirmed",
                Donation.created_at >= month_start,
            )
        )
    )
    monthly_collected = float(month_donations_res.scalar() or 0.0)

    # Monthly expenses
    month_expenses_res = await db.execute(
        select(func.coalesce(func.sum(Expense.amount), 0.0)).where(
            Expense.created_at >= month_start
        )
    )
    monthly_expenses = float(month_expenses_res.scalar() or 0.0)

    # Monthly target setting
    target_res = await db.execute(select(Setting).where(Setting.key == "monthly_target"))
    target_setting = target_res.scalar_one_or_none()
    monthly_target = float(target_setting.value) if target_setting else settings.MONTHLY_TARGET

    # Active pledgers count and total pledged monthly
    pledgers_res = await db.execute(
        select(
            func.count(User.id),
            func.coalesce(func.sum(User.pledge_amount), 0.0),
        ).where(and_(User.pledge_active == True, User.pledge_amount > 0))
    )
    active_pledgers_count, total_pledged_monthly = pledgers_res.first() or (0, 0.0)

    # Expense category breakdown
    cat_res = await db.execute(
        select(Expense.category, func.coalesce(func.sum(Expense.amount), 0.0)).group_by(Expense.category)
    )
    category_map: Dict[str, float] = {cat: 0.0 for cat in ALL_CATEGORIES}
    for cat, amt in cat_res.all():
        category_map[cat] = round(float(amt), 2)

    return DashboardOut(
        is_verified=True,
        total_balance=round(total_balance, 2),
        monthly_target=round(monthly_target, 2),
        monthly_collected=round(monthly_collected, 2),
        monthly_expenses=round(monthly_expenses, 2),
        total_donations=round(total_donations, 2),
        total_expenses=round(total_expenses, 2),
        active_pledgers_count=int(active_pledgers_count),
        total_pledged_monthly=round(float(total_pledged_monthly), 2),
        category_breakdown=category_map,
        paypal_me_url=paypal_me_url,
    )


@router.get("/feed", response_model=List[FeedItem])
async def get_feed(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Restrict transparency logs to verified members
    if not (current_user.is_verified or current_user.role == "admin"):
        return []

    # Fetch latest confirmed donations
    donations_res = await db.execute(
        select(Donation, User)
        .join(User, Donation.user_id == User.id)
        .where(Donation.status == "confirmed")
        .order_by(Donation.created_at.desc())
        .limit(40)
    )
    donation_rows = donations_res.all()

    # Fetch latest expenses
    expenses_res = await db.execute(
        select(Expense).order_by(Expense.created_at.desc()).limit(40)
    )
    expenses = expenses_res.scalars().all()

    items: List[FeedItem] = []

    for donation, user in donation_rows:
        method_label = "Cash Jar" if donation.payment_method == "cash" else donation.payment_method.capitalize()
        items.append(
            FeedItem(
                id=donation.id,
                type="donation",
                amount=donation.amount,
                description=f"Contribution via {method_label}",
                payment_method=donation.payment_method,
                status=donation.status,
                user_id=donation.user_id,
                actor_name="Anonymous" if user.tg_id == 0 else user.first_name,
                actor_username=None if user.tg_id == 0 else user.username,
                created_at=donation.created_at,
            )
        )

    for exp in expenses:
        items.append(
            FeedItem(
                id=exp.id,
                type="expense",
                amount=exp.amount,
                description=exp.description,
                category=exp.category,
                user_id=None,
                actor_name="Coffee Team",
                receipt_url=exp.receipt_url,
                created_at=exp.created_at,
            )
        )

    # Sort combined feed chronologically descending
    items.sort(key=lambda x: x.created_at, reverse=True)
    return items[:50]
