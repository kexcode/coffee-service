import hashlib
import hmac
import json
import time
from typing import Optional
from urllib.parse import parse_qsl, unquote

from fastapi import Header, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings, Settings
from app.database import get_db
from app.models import User


def verify_telegram_init_data(init_data_raw: str, bot_token: str) -> dict:
    """
    Verifies Telegram Mini App initData HMAC-SHA256 signature.
    Returns parsed query parameters dict if valid, raises HTTPException otherwise.
    """
    if not init_data_raw or not bot_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Telegram initData or Bot Token"
        )

    # Parse query parameters
    parsed_items = dict(parse_qsl(init_data_raw, keep_blank_values=True))
    if "hash" not in parsed_items:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing hash in Telegram initData"
        )

    received_hash = parsed_items.pop("hash")

    # Data-check-string: alphabetically sorted key=value pairs joined by newline
    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(parsed_items.items())
    )

    # Secret key = HMAC_SHA256("WebAppData", bot_token)
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram initData signature"
        )

    return parsed_items


async def get_current_user(
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
    x_dev_tg_id: Optional[str] = Header(None, alias="X-Dev-Tg-Id"),
    x_dev_first_name: Optional[str] = Header(None, alias="X-Dev-First-Name"),
    x_dev_username: Optional[str] = Header(None, alias="X-Dev-Username"),
    x_dev_role: Optional[str] = Header(None, alias="X-Dev-Role"),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validates Telegram Mini App user or handles dev fallback in development mode.
    Ensures user exists in the database and assigns admin role if in ADMIN_TG_IDS.
    """
    tg_id: int
    first_name: str
    username: Optional[str] = None
    role_override: Optional[str] = None

    # Development fallback
    if settings.ENVIRONMENT == "development" and (not x_telegram_init_data or x_telegram_init_data == "mock"):
        dev_id = int(x_dev_tg_id) if x_dev_tg_id and x_dev_tg_id.isdigit() else 999999
        tg_id = dev_id
        first_name = x_dev_first_name or "Dev Barista"
        username = x_dev_username or "coffee_dev"
        role_override = x_dev_role
    else:
        if not x_telegram_init_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="X-Telegram-Init-Data header missing"
            )

        parsed_data = verify_telegram_init_data(x_telegram_init_data, settings.BOT_TOKEN)
        user_raw = parsed_data.get("user")
        if not user_raw:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User field not found in Telegram initData"
            )

        try:
            user_data = json.loads(user_raw)
            tg_id = int(user_data["id"])
            first_name = str(user_data.get("first_name", "Coffee Drinker"))
            username = user_data.get("username")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Malformed user data in initData: {str(e)}"
            )

    # Check/Create user in database
    result = await db.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar_one_or_none()

    # Determine role
    is_admin_configured = settings.is_admin(tg_id, username)
    resolved_role = "admin" if (is_admin_configured or role_override == "admin") else "user"

    if not user:
        is_verified = True if (is_admin_configured or resolved_role == "admin") else False
        user = User(
            tg_id=tg_id,
            first_name=first_name,
            username=username,
            role=resolved_role,
            is_verified=is_verified,
            pledge_amount=0.0,
            pledge_active=False,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        # Update details if changed
        updated = False
        if user.first_name != first_name:
            user.first_name = first_name
            updated = True
        if user.username != username:
            user.username = username
            updated = True
        if is_admin_configured and user.role != "admin":
            user.role = "admin"
            user.is_verified = True
            updated = True
        elif role_override and user.role != role_override:
            user.role = role_override
            if role_override == "admin":
                user.is_verified = True
            updated = True
        elif (user.role == "admin" or is_admin_configured) and not user.is_verified:
            user.is_verified = True
            updated = True

        if updated:
            await db.commit()
            await db.refresh(user)

    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for this action"
        )
    return current_user
