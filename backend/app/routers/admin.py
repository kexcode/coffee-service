from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth import get_current_admin
from app.database import get_db
from app.models import User, Donation, Expense, Setting
from app.schemas import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseOut,
    DonationOut,
    DonationUpdate,
    SettingUpdate,
)
from app.bot.scheduler import send_monthly_pledge_reminders
from app.config import get_settings

router = APIRouter(prefix="/api/admin", tags=["Admin Management"])


@router.post("/expenses", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
async def create_expense(
    payload: ExpenseCreate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    expense = Expense(
        category=payload.category,
        amount=round(payload.amount, 2),
        description=payload.description.strip(),
        receipt_url=payload.receipt_url.strip() if payload.receipt_url else None,
        created_by=admin.tg_id,
    )
    db.add(expense)
    await db.commit()
    await db.refresh(expense)
    return expense


@router.patch("/expenses/{expense_id}", response_model=ExpenseOut)
async def update_expense(
    expense_id: int,
    payload: ExpenseUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Expense).where(Expense.id == expense_id))
    expense = res.scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    if payload.category is not None:
        expense.category = payload.category
    if payload.amount is not None:
        expense.amount = round(payload.amount, 2)
    if payload.description is not None:
        expense.description = payload.description.strip()
    if payload.receipt_url is not None:
        cleaned_url = payload.receipt_url.strip()
        expense.receipt_url = cleaned_url if cleaned_url else None

    await db.commit()
    await db.refresh(expense)
    return expense


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Expense).where(Expense.id == expense_id))
    expense = res.scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    await db.delete(expense)
    await db.commit()


@router.get("/donations/pending", response_model=List[DonationOut])
async def get_pending_donations(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(Donation, User)
        .join(User, Donation.user_id == User.id)
        .where(Donation.status == "pending")
        .order_by(Donation.created_at.desc())
    )
    rows = res.all()
    results: List[DonationOut] = []
    for donation, user in rows:
        results.append(
            DonationOut(
                id=donation.id,
                user_id=donation.user_id,
                amount=donation.amount,
                payment_method=donation.payment_method,
                status=donation.status,
                created_at=donation.created_at,
                user_first_name=user.first_name,
                user_username=user.username,
            )
        )
    return results


@router.post("/donations/{donation_id}/confirm", response_model=DonationOut)
async def confirm_donation(
    donation_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(Donation, User)
        .join(User, Donation.user_id == User.id)
        .where(Donation.id == donation_id)
    )
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Donation not found")

    donation, user = row
    donation.status = "confirmed"
    await db.commit()
    await db.refresh(donation)

    return DonationOut(
        id=donation.id,
        user_id=donation.user_id,
        amount=donation.amount,
        payment_method=donation.payment_method,
        status=donation.status,
        created_at=donation.created_at,
        user_first_name=user.first_name,
        user_username=user.username,
    )


@router.post("/donations/{donation_id}/reject", response_model=DonationOut)
async def reject_donation(
    donation_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(Donation, User)
        .join(User, Donation.user_id == User.id)
        .where(Donation.id == donation_id)
    )
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Donation not found")

    donation, user = row
    donation.status = "rejected"
    await db.commit()
    await db.refresh(donation)

    return DonationOut(
        id=donation.id,
        user_id=donation.user_id,
        amount=donation.amount,
        payment_method=donation.payment_method,
        status=donation.status,
        created_at=donation.created_at,
        user_first_name=user.first_name,
        user_username=user.username,
    )


@router.patch("/donations/{donation_id}", response_model=DonationOut)
async def update_donation(
    donation_id: int,
    payload: DonationUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(Donation, User)
        .join(User, Donation.user_id == User.id)
        .where(Donation.id == donation_id)
    )
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Donation not found")

    donation, user = row
    if payload.amount is not None:
        donation.amount = round(payload.amount, 2)
    if payload.payment_method is not None:
        donation.payment_method = payload.payment_method
    if payload.status is not None:
        donation.status = payload.status

    await db.commit()
    await db.refresh(donation)

    return DonationOut(
        id=donation.id,
        user_id=donation.user_id,
        amount=donation.amount,
        payment_method=donation.payment_method,
        status=donation.status,
        created_at=donation.created_at,
        user_first_name=user.first_name,
        user_username=user.username,
    )


@router.delete("/donations/{donation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_donation(
    donation_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Donation).where(Donation.id == donation_id))
    donation = res.scalar_one_or_none()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")

    await db.delete(donation)
    await db.commit()


@router.get("/settings", response_model=Dict[str, str])
async def get_all_settings(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Setting))
    settings_rows = res.scalars().all()
    env_settings = get_settings()

    settings_dict = {
        "monthly_target": str(env_settings.MONTHLY_TARGET),
        "paypal_me_url": env_settings.PAYPAL_ME_URL,
    }
    for row in settings_rows:
        settings_dict[row.key] = row.value

    return settings_dict


@router.post("/settings/{key}")
async def update_setting(
    key: str,
    payload: SettingUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Setting).where(Setting.key == key))
    setting = res.scalar_one_or_none()
    if not setting:
        setting = Setting(key=key, value=payload.value)
        db.add(setting)
    else:
        setting.value = payload.value

    await db.commit()
    return {"key": key, "value": payload.value}


@router.post("/trigger-reminders")
async def trigger_reminders_manually(
    admin: User = Depends(get_current_admin),
):
    await send_monthly_pledge_reminders()
    return {"message": "Monthly pledge reminders triggered successfully."}
