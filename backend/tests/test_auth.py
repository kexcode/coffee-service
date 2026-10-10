import hashlib
import hmac
import json
import pytest
from app.auth import verify_telegram_init_data
from fastapi import HTTPException


def create_valid_init_data(bot_token: str, user_dict: dict, auth_date: int = 1710000000) -> str:
    user_json = json.dumps(user_dict, separators=(",", ":"))
    params = {
        "auth_date": str(auth_date),
        "query_id": "AAHdF6IQAAAAAN0XohDhrPzN",
        "user": user_json,
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    hash_val = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    # Create raw query string
    return f"auth_date={auth_date}&query_id=AAHdF6IQAAAAAN0XohDhrPzN&user={user_json}&hash={hash_val}"


def test_verify_valid_telegram_init_data():
    token = "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
    user_info = {"id": 12345, "first_name": "Alice", "username": "alice_coffee"}
    raw_init_data = create_valid_init_data(token, user_info)

    result = verify_telegram_init_data(raw_init_data, token)
    assert "user" in result
    user_parsed = json.loads(result["user"])
    assert user_parsed["id"] == 12345
    assert user_parsed["first_name"] == "Alice"


def test_verify_tampered_init_data():
    token = "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
    user_info = {"id": 12345, "first_name": "Alice", "username": "alice_coffee"}
    raw_init_data = create_valid_init_data(token, user_info)

    # Tamper with the user ID in the query string
    tampered_data = raw_init_data.replace("12345", "99999")

    with pytest.raises(HTTPException) as exc_info:
        verify_telegram_init_data(tampered_data, token)
    assert exc_info.value.status_code == 401
    assert "Invalid Telegram initData signature" in exc_info.value.detail


def test_verify_wrong_token():
    token = "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
    wrong_token = "987654321:DifferentTokenHere"
    user_info = {"id": 12345, "first_name": "Alice"}
    raw_init_data = create_valid_init_data(token, user_info)

    with pytest.raises(HTTPException) as exc_info:
        verify_telegram_init_data(raw_init_data, wrong_token)
    assert exc_info.value.status_code == 401
