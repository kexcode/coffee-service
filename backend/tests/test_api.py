import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from app.main import app
from app.config import get_settings
from app.database import get_db, Base
from app.models import Setting

# Ensure test suite always allows dev header authentication regardless of container ENVIRONMENT
get_settings().ENVIRONMENT = "development"

test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with _test_session_factory() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _test_session_factory() as session:
        session.add(Setting(key="monthly_target", value="150.0"))
        session.add(Setting(key="paypal_me_url", value="https://paypal.me"))
        await session.commit()
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_healthcheck():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "coffee-service"


@pytest.mark.asyncio
async def test_dashboard_and_pledge_flow():
    dev_headers = {
        "X-Dev-Tg-Id": "1001",
        "X-Dev-First-Name": "Marco",
        "X-Dev-Username": "marco_barista",
    }
    admin_headers = {
        "X-Dev-Tg-Id": "9999",
        "X-Dev-First-Name": "AdminBoss",
        "X-Dev-Role": "admin",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Check User Me (New user defaults to unverified)
        me_resp = await client.get("/api/user/me", headers=dev_headers)
        assert me_resp.status_code == 200
        user = me_resp.json()
        assert user["tg_id"] == 1001
        assert user["first_name"] == "Marco"
        assert user["is_verified"] is False
        assert user["pledge_active"] is False
        user_id = user["id"]

        # 2. Check unverified dashboard (metrics masked, paypal_me_url available)
        dash_unverified_resp = await client.get("/api/dashboard", headers=dev_headers)
        assert dash_unverified_resp.status_code == 200
        dash_unverified = dash_unverified_resp.json()
        assert dash_unverified["is_verified"] is False
        assert dash_unverified["total_balance"] == 0.0
        assert "paypal" in dash_unverified["paypal_me_url"].lower()

        # 3. Check unverified feed (empty for unverified visitors)
        feed_unverified_resp = await client.get("/api/feed", headers=dev_headers)
        assert feed_unverified_resp.status_code == 200
        assert feed_unverified_resp.json() == []

        # 4. Unverified user can freely log cash donation and pledge
        cash_resp = await client.post(
            "/api/donations/cash",
            headers=dev_headers,
            json={"amount": 15.0},
        )
        assert cash_resp.status_code == 201
        donation = cash_resp.json()
        assert donation["amount"] == 15.0
        assert donation["status"] == "pending"

        pledge_resp = await client.post(
            "/api/pledge",
            headers=dev_headers,
            json={"pledge_amount": 10.0, "pledge_active": True},
        )
        assert pledge_resp.status_code == 200

        # 5. Admin lists users and verifies Marco
        users_resp = await client.get("/api/admin/users", headers=admin_headers)
        assert users_resp.status_code == 200
        user_list = users_resp.json()
        assert any(u["id"] == user_id and u["is_verified"] is False for u in user_list)

        verify_resp = await client.patch(
            f"/api/admin/users/{user_id}/verify",
            headers=admin_headers,
            json={"is_verified": True},
        )
        assert verify_resp.status_code == 200
        assert verify_resp.json()["is_verified"] is True

        # 6. Admin confirms cash donation
        confirm_resp = await client.post(
            f"/api/admin/donations/{donation['id']}/confirm",
            headers=admin_headers,
        )
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["status"] == "confirmed"

        # 7. Admin records expense
        expense_resp = await client.post(
            "/api/admin/expenses",
            headers=admin_headers,
            json={
                "category": "beans",
                "amount": 12.50,
                "description": "1kg Ethiopian Yirgacheffe",
            },
        )
        assert expense_resp.status_code == 201
        assert expense_resp.json()["amount"] == 12.50

        # 8. Now verified, Marco can see full Treasury balance: €15.00 confirmed - €12.50 = €2.50
        dash_resp2 = await client.get("/api/dashboard", headers=dev_headers)
        dash2 = dash_resp2.json()
        assert dash2["is_verified"] is True
        assert dash2["total_balance"] == 2.50
        assert dash2["category_breakdown"]["beans"] == 12.50

        # 9. Verified feed returns transactions with user_id
        feed_resp = await client.get("/api/feed", headers=dev_headers)
        assert feed_resp.status_code == 200
        feed = feed_resp.json()
        assert len(feed) == 2
        don_item = next(item for item in feed if item["type"] == "donation")
        assert don_item["user_id"] == user_id

        # 10. Admin creates second user (Luca) and re-assigns donation contributor to Luca
        luca_headers = {
            "X-Dev-Tg-Id": "1002",
            "X-Dev-First-Name": "Luca",
            "X-Dev-Username": "luca_coffee",
        }
        luca_me = await client.get("/api/user/me", headers=luca_headers)
        luca_id = luca_me.json()["id"]

        reassign_resp = await client.patch(
            f"/api/admin/donations/{donation['id']}",
            headers=admin_headers,
            json={"user_id": luca_id, "created_at": "2026-03-15T12:00:00Z"},
        )
        assert reassign_resp.status_code == 200
        assert reassign_resp.json()["user_id"] == luca_id
        assert reassign_resp.json()["user_first_name"] == "Luca"
        assert reassign_resp.json()["created_at"].startswith("2026-03-15")

        exp_id = expense_resp.json()["id"]
        exp_date_resp = await client.patch(
            f"/api/admin/expenses/{exp_id}",
            headers=admin_headers,
            json={"created_at": "2026-02-10T12:00:00Z"},
        )
        assert exp_date_resp.status_code == 200
        assert exp_date_resp.json()["created_at"].startswith("2026-02-10")

        # 11. Role management: promote Luca to admin
        role_resp = await client.patch(
            f"/api/admin/users/{luca_id}/role",
            headers=admin_headers,
            json={"role": "admin"},
        )
        assert role_resp.status_code == 200
        assert role_resp.json()["role"] == "admin"
        assert role_resp.json()["is_verified"] is True

        # Demote oneself should fail
        admin_me = await client.get("/api/user/me", headers=admin_headers)
        self_admin_id = admin_me.json()["id"]
        demote_self_resp = await client.patch(
            f"/api/admin/users/{self_admin_id}/role",
            headers=admin_headers,
            json={"role": "user"},
        )
        assert demote_self_resp.status_code == 400


@pytest.mark.asyncio
async def test_sweets_anonymous_and_csv_import():
    admin_headers = {
        "X-Dev-Tg-Id": "9999",
        "X-Dev-First-Name": "AdminBoss",
        "X-Dev-Role": "admin",
    }
    user_headers = {
        "X-Dev-Tg-Id": "2001",
        "X-Dev-First-Name": "Sarah",
        "X-Dev-Username": "sarah_coffee",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Log expense in sweets category
        exp_resp = await client.post(
            "/api/admin/expenses",
            headers=admin_headers,
            json={
                "category": "sweets",
                "amount": 7.50,
                "description": "Artisan Cantucci and Chocolate",
            },
        )
        assert exp_resp.status_code == 201
        assert exp_resp.json()["category"] == "sweets"

        # 2. Log anonymous cash donation
        anon_cash_resp = await client.post(
            "/api/donations/cash",
            headers=user_headers,
            json={"amount": 25.0, "is_anonymous": True},
        )
        assert anon_cash_resp.status_code == 201
        anon_data = anon_cash_resp.json()
        assert anon_data["amount"] == 25.0
        assert anon_data["user_first_name"] == "Anonymous"
        assert anon_data["user_username"] is None

        # 3. CSV Import Preview
        csv_sample = (
            "date,category,amount,contributor\n"
            "2024-05-01,beans,20.00,Sarah\n"
            "2024-05-02,sweets,5.50,\n"
            "2024-05-03,donation,30.00,anonym\n"
            "2024-05-04,cookies,4.00,anonym\n"
            "2024-05-05,donation,15.00,@new_donor\n"
        )
        preview_resp = await client.post(
            "/api/admin/import/preview",
            headers=admin_headers,
            json={"csv_content": csv_sample},
        )
        assert preview_resp.status_code == 200
        preview = preview_resp.json()
        assert preview["total_rows"] == 5
        assert preview["donations_imported"] == 2
        assert preview["expenses_imported"] == 3
        assert preview["anonymous_donations"] == 1
        assert len(preview["preview"]) == 5

        # 4. Actual CSV Import
        import_resp = await client.post(
            "/api/admin/import/csv",
            headers=admin_headers,
            json={"csv_content": csv_sample},
        )
        assert import_resp.status_code == 200
        summary = import_resp.json()
        assert summary["total_rows"] == 5
        assert summary["donations_imported"] == 2
        assert summary["expenses_imported"] == 3
        assert summary["anonymous_donations"] == 1
        assert len(summary["errors"]) == 0

        # Verify Dashboard includes sweets in category breakdown
        dash_resp = await client.get("/api/dashboard", headers=admin_headers)
        assert dash_resp.status_code == 200
        dash = dash_resp.json()
        assert "sweets" in dash["category_breakdown"]
        # Initial 7.50 + imported 5.50 + imported cookies 4.00 = 17.00
        assert dash["category_breakdown"]["sweets"] == 17.00

        # Verify Feed works with mixed naive and timezone-aware timestamps
        feed_resp = await client.get("/api/feed", headers=admin_headers)
        assert feed_resp.status_code == 200
        assert len(feed_resp.json()) >= 6

        # Verify sample CSV download endpoint
        sample_resp = await client.get("/api/admin/import/sample-template")
        assert sample_resp.status_code == 200
        assert "date,category,amount,contributor" in sample_resp.text


@pytest.mark.asyncio
async def test_concurrent_first_visit_no_race_condition():
    import asyncio
    new_user_headers = {
        "X-Dev-Tg-Id": "777888",
        "X-Dev-First-Name": "Alex",
        "X-Dev-Username": "alex_barista",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r1, r2, r3 = await asyncio.gather(
            client.get("/api/user/me", headers=new_user_headers),
            client.get("/api/dashboard", headers=new_user_headers),
            client.get("/api/feed", headers=new_user_headers),
        )
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 200


