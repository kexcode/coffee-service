from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

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
    UserOut,
    AdminUserOut,
    UserRoleUpdate,
    UserVerifyUpdate,
)
from app.bot.scheduler import send_monthly_pledge_reminders
from app.config import get_settings, Settings

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
    if payload.user_id is not None and payload.user_id != donation.user_id:
        u_res = await db.execute(select(User).where(User.id == payload.user_id))
        target_user = u_res.scalar_one_or_none()
        if not target_user:
            raise HTTPException(status_code=400, detail="Target user for contributor assignment not found")
        donation.user_id = target_user.id
        user = target_user

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


@router.get("/users", response_model=List[AdminUserOut])
async def get_all_users(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(
            User,
            func.coalesce(
                func.sum(
                    case((Donation.status == "confirmed", Donation.amount), else_=0.0)
                ),
                0.0,
            ).label("total_donated"),
        )
        .outerjoin(Donation, User.id == Donation.user_id)
        .group_by(User.id)
        .order_by(User.created_at.desc())
    )
    res = await db.execute(query)
    results: List[AdminUserOut] = []
    for user, total_donated in res.all():
        results.append(
            AdminUserOut(
                id=user.id,
                tg_id=user.tg_id,
                username=user.username,
                first_name=user.first_name,
                role=user.role,
                is_verified=user.is_verified,
                pledge_amount=user.pledge_amount,
                pledge_active=user.pledge_active,
                total_donated=round(float(total_donated), 2),
                created_at=user.created_at,
            )
        )
    return results


@router.patch("/users/{user_id}/role", response_model=UserOut)
async def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    res = await db.execute(select(User).where(User.id == user_id))
    target_user = res.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if target_user.id == admin.id and payload.role != "admin":
        raise HTTPException(status_code=400, detail="Cannot demote yourself from admin")

    if settings.is_admin(target_user.tg_id, target_user.username) and payload.role != "admin":
        raise HTTPException(status_code=400, detail="Cannot demote configured superadmin")

    target_user.role = payload.role
    if payload.role == "admin":
        target_user.is_verified = True

    await db.commit()
    await db.refresh(target_user)
    return target_user


@router.patch("/users/{user_id}/verify", response_model=UserOut)
async def update_user_verification(
    user_id: int,
    payload: UserVerifyUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    res = await db.execute(select(User).where(User.id == user_id))
    target_user = res.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if target_user.role == "admin" and not payload.is_verified:
        raise HTTPException(status_code=400, detail="Admins must remain verified")

    was_verified = target_user.is_verified
    target_user.is_verified = payload.is_verified
    await db.commit()
    await db.refresh(target_user)

    # Notify user via bot if they were just approved
    if not was_verified and payload.is_verified and target_user.tg_id:
        from app.bot.instance import notify_user_verified
        await notify_user_verified(target_user.tg_id)

    return target_user
