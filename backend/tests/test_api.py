import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import engine, Base


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
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

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Check User Me
        me_resp = await client.get("/api/user/me", headers=dev_headers)
        assert me_resp.status_code == 200
        user = me_resp.json()
        assert user["tg_id"] == 1001
        assert user["first_name"] == "Marco"
        assert user["pledge_active"] is False

        # 2. Update Pledge
        pledge_resp = await client.post(
            "/api/pledge",
            headers=dev_headers,
            json={"pledge_amount": 10.0, "pledge_active": True},
        )
        assert pledge_resp.status_code == 200
        updated_user = pledge_resp.json()
        assert updated_user["pledge_amount"] == 10.0
        assert updated_user["pledge_active"] is True

        # 3. Log Cash Donation
        cash_resp = await client.post(
            "/api/donations/cash",
            headers=dev_headers,
            json={"amount": 15.0},
        )
        assert cash_resp.status_code == 201
        donation = cash_resp.json()
        assert donation["amount"] == 15.0
        assert donation["status"] == "pending"

        # 4. Check initial dashboard (balance should be 0 because donation is still pending)
        dash_resp = await client.get("/api/dashboard", headers=dev_headers)
        assert dash_resp.status_code == 200
        dash = dash_resp.json()
        assert dash["total_balance"] == 0.0
        assert dash["active_pledgers_count"] == 1
        assert dash["total_pledged_monthly"] == 10.0

        # 5. Confirm donation as Admin
        admin_headers = {
            "X-Dev-Tg-Id": "9999",
            "X-Dev-First-Name": "AdminBoss",
            "X-Dev-Role": "admin",
        }
        confirm_resp = await client.post(
            f"/api/admin/donations/{donation['id']}/confirm",
            headers=admin_headers,
        )
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["status"] == "confirmed"

        # 6. Add Expense as Admin
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

        # 7. Verify Treasury Balance calculation: €15.00 confirmed - €12.50 expense = €2.50 balance
        dash_resp2 = await client.get("/api/dashboard", headers=dev_headers)
        dash2 = dash_resp2.json()
        assert dash2["total_balance"] == 2.50
        assert dash2["category_breakdown"]["beans"] == 12.50

        # 8. Verify Feed contains both transactions
        feed_resp = await client.get("/api/feed", headers=dev_headers)
        assert feed_resp.status_code == 200
        feed = feed_resp.json()
        assert len(feed) == 2
        types = [item["type"] for item in feed]
        assert "donation" in types
        assert "expense" in types

        # 9. Admin edits expense (correction of amount and description)
        exp_id = expense_resp.json()["id"]
        patch_exp_resp = await client.patch(
            f"/api/admin/expenses/{exp_id}",
            headers=admin_headers,
            json={"amount": 10.0, "description": "1kg Ethiopian Yirgacheffe (Discounted)"},
        )
        assert patch_exp_resp.status_code == 200
        assert patch_exp_resp.json()["amount"] == 10.0
        assert patch_exp_resp.json()["description"] == "1kg Ethiopian Yirgacheffe (Discounted)"

        # 10. Admin edits donation (correction of amount)
        don_id = donation["id"]
        patch_don_resp = await client.patch(
            f"/api/admin/donations/{don_id}",
            headers=admin_headers,
            json={"amount": 20.0},
        )
        assert patch_don_resp.status_code == 200
        assert patch_don_resp.json()["amount"] == 20.0

        # Verify updated balance: €20.00 - €10.00 = €10.00
        dash_resp3 = await client.get("/api/dashboard", headers=dev_headers)
        assert dash_resp3.json()["total_balance"] == 10.00

        # 11. Admin deletes expense
        del_exp_resp = await client.delete(f"/api/admin/expenses/{exp_id}", headers=admin_headers)
        assert del_exp_resp.status_code == 204

        # 12. Admin deletes donation
        del_don_resp = await client.delete(f"/api/admin/donations/{don_id}", headers=admin_headers)
        assert del_don_resp.status_code == 204

        # Balance returns to 0
        dash_resp4 = await client.get("/api/dashboard", headers=dev_headers)
        assert dash_resp4.json()["total_balance"] == 0.00
