import csv
import io
import re
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, status, Response
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
    CSVImportRequest,
    CSVImportItem,
    CSVImportSummary,
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
    if payload.created_at is not None:
        dt = payload.created_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        expense.created_at = dt

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
    if payload.created_at is not None:
        dt = payload.created_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        donation.created_at = dt

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


def _parse_csv_rows(csv_text: str):
    csv_text = csv_text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not csv_text:
        return []

    lines = [line.strip() for line in csv_text.split("\n") if line.strip()]
    if not lines:
        return []

    sample = lines[0]
    delimiter = ","
    if ";" in sample and sample.count(";") >= sample.count(","):
        delimiter = ";"
    elif "\t" in sample and sample.count("\t") >= sample.count(","):
        delimiter = "\t"

    reader = csv.reader(io.StringIO(csv_text), delimiter=delimiter)
    raw_rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not raw_rows:
        return []

    first_row = [cell.strip().lower() for cell in raw_rows[0]]
    has_header = any(k in first_row for k in ["date", "category", "amount", "contributor", "donor", "user", "type"])

    col_indices = {"date": 0, "category": 1, "amount": 2, "contributor": 3}

    if has_header:
        for idx, col in enumerate(first_row):
            if any(w in col for w in ["date", "time", "day"]):
                col_indices["date"] = idx
            elif any(w in col for w in ["category", "cat", "item", "type"]):
                col_indices["category"] = idx
            elif any(w in col for w in ["amount", "price", "sum", "cost", "eur", "usd", "val"]):
                col_indices["amount"] = idx
            elif any(w in col for w in ["contributor", "donor", "user", "name", "who", "person"]):
                col_indices["contributor"] = idx
        data_rows = raw_rows[1:]
    else:
        data_rows = raw_rows

    # Security: Limit maximum rows processed per batch to prevent DoS
    data_rows = data_rows[:2000]

    def _sanitize_csv_field(val: str) -> str:
        # Prevent spreadsheet formula injection (=, +, -, @)
        cleaned = val.strip()
        while cleaned and cleaned[0] in ("=", "+", "-", "@", "\t", "\r"):
            cleaned = cleaned[1:].strip()
        return cleaned

    parsed = []
    for row in data_rows:
        def get_val(idx):
            return row[idx].strip() if idx < len(row) else ""

        date_val = get_val(col_indices["date"])
        cat_val = _sanitize_csv_field(get_val(col_indices["category"]))
        amt_val = get_val(col_indices["amount"])
        contrib_val = _sanitize_csv_field(get_val(col_indices["contributor"]))

        if not (date_val or cat_val or amt_val):
            continue
        parsed.append({
            "raw_date": date_val,
            "raw_category": cat_val,
            "raw_amount": amt_val,
            "raw_contributor": contrib_val,
        })
    return parsed


def _parse_amount(raw_amt: str) -> float:
    cleaned = re.sub(r"[^\d.,\-]", "", raw_amt)
    if "," in cleaned and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")
    elif "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(",", "")
    val = float(cleaned)
    return round(abs(val), 2)


def _parse_date(date_str: str) -> datetime:
    date_str = date_str.strip()
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass
    return datetime.now(timezone.utc)


DONATION_KEYWORDS = {
    "donation", "donations", "income", "contribution", "contributions",
    "cash", "paypal", "card", "in", "deposit", "jar", "pledge"
}


def _classify_category(cat: str) -> Tuple[str, str]:
    c_lower = cat.strip().lower()
    if any(kw in c_lower for kw in ["donat", "income", "contribut", "deposit"]) or c_lower in DONATION_KEYWORDS:
        method = "paypal" if "paypal" in c_lower else ("card" if "card" in c_lower else "cash")
        return "donation", method

    if c_lower in {"beans", "sweets", "filters", "cleaning", "maintenance_repair", "depreciation_reserve"}:
        return "expense", c_lower

    if any(k in c_lower for k in ["sweet", "snack", "cookie", "candy", "chocolate", "dessert", "treat", "sugar", "biscuit", "cake"]):
        return "expense", "sweets"
    if any(k in c_lower for k in ["bean", "coffee", "roast", "grain"]):
        return "expense", "beans"
    if any(k in c_lower for k in ["filter", "paper"]):
        return "expense", "filters"
    if any(k in c_lower for k in ["clean", "tablet", "descal", "soap", "detergent"]):
        return "expense", "cleaning"
    if any(k in c_lower for k in ["repair", "maint", "fix", "part", "service"]):
        return "expense", "maintenance_repair"
    if any(k in c_lower for k in ["deprec", "reserve", "fund"]):
        return "expense", "depreciation_reserve"

    return "expense", "beans"


ANON_KEYWORDS = {"", "anonym", "anonymous", "anon", "-", "none", "n/a", "null"}


async def _resolve_or_create_user(db: AsyncSession, contributor: Optional[str], anon_user_id: int) -> Tuple[int, str, bool]:
    if not contributor or contributor.strip().lower() in ANON_KEYWORDS:
        return anon_user_id, "Anonymous", True

    clean = contributor.strip()
    uname = clean.lstrip("@").lower()

    if clean.isdigit():
        res = await db.execute(select(User).where(User.tg_id == int(clean)))
        u = res.scalar_one_or_none()
        if u:
            return u.id, u.first_name, False

    res = await db.execute(select(User).where(func.lower(User.username) == uname))
    u = res.scalar_one_or_none()
    if u:
        return u.id, u.first_name, False

    res = await db.execute(select(User).where(func.lower(User.first_name) == clean.lower()))
    u = res.scalar_one_or_none()
    if u:
        return u.id, u.first_name, False

    min_res = await db.execute(select(func.min(User.tg_id)).where(User.tg_id < 0))
    min_tg_id = min_res.scalar()
    next_tg_id = -1 if (min_tg_id is None or min_tg_id >= 0) else (min_tg_id - 1)

    first_name = clean.lstrip("@")
    username_val = uname if clean.startswith("@") else None
    new_user = User(
        tg_id=next_tg_id,
        username=username_val,
        first_name=first_name,
        role="user",
        is_verified=True,
        pledge_amount=0.0,
        pledge_active=False,
    )
    db.add(new_user)
    await db.flush()
    return new_user.id, new_user.first_name, False


@router.get("/import/sample-template")
async def download_sample_csv_template():
    sample = (
        "date,category,amount,contributor\n"
        "2024-05-01,beans,24.50,Marco\n"
        "2024-05-02,sweets,6.50,\n"
        "2024-05-03,donation,35.00,anonym\n"
        "2024-05-04,filters,8.00,@sarah\n"
        "2024-05-05,cookies,4.20,anonym\n"
        "2024-05-06,donation,15.00,\n"
    )
    return Response(
        content=sample,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=coffee_service_import_template.csv",
            "Cache-Control": "no-cache",
        },
    )


@router.post("/import/preview", response_model=CSVImportSummary)
async def preview_csv_import(
    payload: CSVImportRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = _parse_csv_rows(payload.csv_content)
    if not rows:
        raise HTTPException(status_code=400, detail="No valid data rows found in CSV")

    res = await db.execute(select(User).where(User.tg_id == 0))
    anon_user = res.scalar_one_or_none()
    anon_id = anon_user.id if anon_user else 0

    items_preview: List[CSVImportItem] = []
    donations_count = 0
    expenses_count = 0
    anon_count = 0
    errors: List[str] = []

    for idx, row in enumerate(rows, start=1):
        try:
            amt = _parse_amount(row["raw_amount"])
            dt = _parse_date(row["raw_date"])
            item_type, classified = _classify_category(row["raw_category"])

            contrib_raw = row["raw_contributor"]
            is_anon = not contrib_raw or contrib_raw.strip().lower() in ANON_KEYWORDS
            resolved_name = "Anonymous" if is_anon else contrib_raw.strip().lstrip("@")

            if item_type == "donation":
                donations_count += 1
                if is_anon:
                    anon_count += 1
            else:
                expenses_count += 1

            items_preview.append(
                CSVImportItem(
                    date=dt.strftime("%Y-%m-%d"),
                    category=classified,
                    amount=amt,
                    contributor=contrib_raw if contrib_raw else None,
                    type=item_type,
                    resolved_contributor=resolved_name,
                )
            )
        except Exception as e:
            errors.append(f"Row {idx}: {str(e)}")

    return CSVImportSummary(
        total_rows=len(rows),
        expenses_imported=expenses_count,
        donations_imported=donations_count,
        anonymous_donations=anon_count,
        errors=errors,
        preview=items_preview[:15],
    )


@router.post("/import/csv", response_model=CSVImportSummary)
async def import_csv_data(
    payload: CSVImportRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = _parse_csv_rows(payload.csv_content)
    if not rows:
        raise HTTPException(status_code=400, detail="No valid data rows found in CSV")

    res = await db.execute(select(User).where(User.tg_id == 0))
    anon_user = res.scalar_one_or_none()
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

    donations_count = 0
    expenses_count = 0
    anon_count = 0
    errors: List[str] = []

    for idx, row in enumerate(rows, start=1):
        try:
            amt = _parse_amount(row["raw_amount"])
            dt = _parse_date(row["raw_date"])
            item_type, classified = _classify_category(row["raw_category"])

            contrib_id, contrib_name, is_anon = await _resolve_or_create_user(
                db, row["raw_contributor"], anon_user.id
            )

            if item_type == "donation":
                donation = Donation(
                    user_id=contrib_id,
                    amount=amt,
                    payment_method=classified,
                    status="confirmed",
                    created_at=dt,
                )
                db.add(donation)
                donations_count += 1
                if is_anon:
                    anon_count += 1
            else:
                desc = f"Imported: {row['raw_category'].strip()}" if row['raw_category'].strip() else "Imported expense"
                if not is_anon:
                    desc += f" ({contrib_name})"
                expense = Expense(
                    category=classified,
                    amount=amt,
                    description=desc,
                    receipt_url=None,
                    created_by=admin.tg_id,
                    created_at=dt,
                )
                db.add(expense)
                expenses_count += 1
        except Exception as e:
            errors.append(f"Row {idx}: {str(e)}")

    await db.commit()

    return CSVImportSummary(
        total_rows=len(rows),
        expenses_imported=expenses_count,
        donations_imported=donations_count,
        anonymous_donations=anon_count,
        errors=errors,
        preview=None,
    )

