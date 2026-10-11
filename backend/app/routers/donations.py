import time
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import User, Donation
from app.schemas import CashDonationCreate, DonationOut, PledgeUpdate, UserOut
from app.bot.instance import notify_admins_cash_donation

router = APIRouter(prefix="/api", tags=["Donations & Pledges"])

# In-memory sliding window rate limits per user
_cash_donation_history = defaultdict(list)
_pledge_history = defaultdict(list)


def _check_rate_limit(history_dict: dict, key: int, max_requests: int = 5, window_seconds: int = 60) -> bool:
    now = time.time()
    history_dict[key] = [t for t in history_dict[key] if now - t < window_seconds]
    if len(history_dict[key]) >= max_requests:
        return False
    history_dict[key].append(now)
    return True


@router.post("/donations/cash", response_model=DonationOut, status_code=status.HTTP_201_CREATED)
async def create_cash_donation(
    payload: CashDonationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Rate limit: max 5 cash donations per minute per user
    if not _check_rate_limit(_cash_donation_history, current_user.id, max_requests=5, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many donation requests. Please wait a moment before submitting again."
        )

    target_user_id = current_user.id
    target_user_name = current_user.first_name
    target_username = current_user.username

    if payload.is_anonymous:
        from sqlalchemy import select
        anon_res = await db.execute(select(User).where(User.tg_id == 0))
        anon_user = anon_res.scalar_one_or_none()
        if not anon_user:
            anon_user = User(
                tg_id=0,
                username="anonymous",
                first_name="Anonymous",
                role="user",
                is_verified=True,
                pledge_amount=0.0,
                pledge_active=False,
            )
            db.add(anon_user)
            await db.flush()

        target_user_id = anon_user.id
        target_user_name = "Anonymous"
        target_username = None

    donation = Donation(
        user_id=target_user_id,
        amount=round(payload.amount, 2),
        payment_method="cash",
        status="pending",
    )
    db.add(donation)
    await db.commit()
    await db.refresh(donation)

    # Notify admins asynchronously via bot
    await notify_admins_cash_donation(
        donation_id=donation.id,
        user_first_name=target_user_name,
        amount=donation.amount,
    )

    return DonationOut(
        id=donation.id,
        user_id=donation.user_id,
        amount=donation.amount,
        payment_method=donation.payment_method,
        status=donation.status,
        created_at=donation.created_at,
        user_first_name=target_user_name,
        user_username=target_username,
    )


@router.post("/pledge", response_model=UserOut)
async def update_pledge(
    payload: PledgeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Rate limit: max 10 pledge updates per minute per user
    if not _check_rate_limit(_pledge_history, current_user.id, max_requests=10, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many pledge update requests. Please wait a moment before trying again."
        )

    current_user.pledge_amount = round(payload.pledge_amount, 2)
    current_user.pledge_active = payload.pledge_active

    await db.commit()
    await db.refresh(current_user)
    return current_user
