from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.security import AuthenticatedUser, get_current_user
from app.db.session import get_session
from app.main import app
from app.models import *  # noqa: F401,F403


def _build_test_engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture()
def test_app():
    engine = _build_test_engine()
    SQLModel.metadata.create_all(engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    test_user_id = str(uuid4())

    def override_current_user() -> AuthenticatedUser:
        return AuthenticatedUser(
            user_id=test_user_id,
            email="test@example.com",
            role="authenticated",
            raw_claims={"sub": test_user_id},
        )

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = override_current_user
    try:
        yield app
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_and_filter_transactions(test_app) -> None:
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        account_response = await ac.post(
            "/v1/accounts",
            json={"name": "Main", "type": "bank", "balance": "0.00", "currency": "usd"},
        )
        category_response = await ac.post(
            "/v1/categories",
            json={"name": "Groceries", "kind": "expense", "is_default": False},
        )

        account_id = account_response.json()["id"]
        category_id = category_response.json()["id"]

        create_response = await ac.post(
            "/v1/transactions",
            json={
                "account_id": account_id,
                "category_id": category_id,
                "type": "expense",
                "amount": "45.67",
                "occurred_at": "2026-03-10T12:00:00Z",
                "note": "Lunch and groceries",
            },
        )
        account_after_create = await ac.get(f"/v1/accounts/{account_id}")
        list_response = await ac.get(
            "/v1/transactions",
            params={"type": "expense", "account_id": account_id},
        )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["amount"] == "45.67"
    assert created["type"] == "expense"
    assert account_after_create.status_code == 200
    assert account_after_create.json()["balance"] == "-45.67"

    assert list_response.status_code == 200
    listed = list_response.json()
    assert len(listed) == 1
    assert listed[0]["id"] == created["id"]


@pytest.mark.asyncio
async def test_get_update_delete_transaction(test_app) -> None:
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        account_response = await ac.post(
            "/v1/accounts",
            json={"name": "Wallet", "type": "cash", "balance": "100.00", "currency": "usd"},
        )
        category_response = await ac.post(
            "/v1/categories",
            json={"name": "Transport", "kind": "expense", "is_default": False},
        )

        account_id = account_response.json()["id"]
        category_id = category_response.json()["id"]

        create_response = await ac.post(
            "/v1/transactions",
            json={
                "account_id": account_id,
                "category_id": category_id,
                "type": "expense",
                "amount": "20.00",
            },
        )
        transaction_id = create_response.json()["id"]
        account_after_create = await ac.get(f"/v1/accounts/{account_id}")

        get_response = await ac.get(f"/v1/transactions/{transaction_id}")
        update_response = await ac.patch(
            f"/v1/transactions/{transaction_id}",
            json={"amount": "25.00", "note": "Taxi fare"},
        )
        account_after_update = await ac.get(f"/v1/accounts/{account_id}")
        delete_response = await ac.delete(f"/v1/transactions/{transaction_id}")
        account_after_delete = await ac.get(f"/v1/accounts/{account_id}")
        after_delete_response = await ac.get(f"/v1/transactions/{transaction_id}")

    assert get_response.status_code == 200
    assert get_response.json()["amount"] == "20.00"
    assert account_after_create.status_code == 200
    assert account_after_create.json()["balance"] == "80.00"

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["amount"] == "25.00"
    assert updated["note"] == "Taxi fare"
    assert account_after_update.status_code == 200
    assert account_after_update.json()["balance"] == "75.00"

    assert delete_response.status_code == 204
    assert account_after_delete.status_code == 200
    assert account_after_delete.json()["balance"] == "100.00"
    assert after_delete_response.status_code == 404


@pytest.mark.asyncio
async def test_create_transaction_requires_owned_account(test_app) -> None:
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/v1/transactions",
            json={"account_id": 9999, "type": "expense", "amount": "12.00"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Account not found for current user"


@pytest.mark.asyncio
async def test_list_transactions_global_search_and_sort(test_app) -> None:
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        account_axis = await ac.post(
            "/v1/accounts",
            json={"name": "Axis", "type": "bank", "balance": "0.00", "currency": "usd"},
        )
        account_wallet = await ac.post(
            "/v1/accounts",
            json={"name": "Wallet", "type": "cash", "balance": "0.00", "currency": "usd"},
        )
        category_food = await ac.post(
            "/v1/categories",
            json={"name": "Food", "kind": "expense", "is_default": False},
        )

        axis_id = account_axis.json()["id"]
        wallet_id = account_wallet.json()["id"]
        food_id = category_food.json()["id"]

        await ac.post(
            "/v1/transactions",
            json={
                "account_id": axis_id,
                "category_id": food_id,
                "type": "expense",
                "amount": "100.00",
                "occurred_at": "2026-03-22T10:00:00Z",
                "note": "Lunch",
            },
        )
        await ac.post(
            "/v1/transactions",
            json={
                "account_id": wallet_id,
                "category_id": food_id,
                "type": "expense",
                "amount": "20.00",
                "occurred_at": "2026-03-21T10:00:00Z",
                "note": "Snack",
            },
        )
        await ac.post(
            "/v1/transactions",
            json={
                "account_id": axis_id,
                "category_id": food_id,
                "type": "income",
                "amount": "500.00",
                "occurred_at": "2026-03-20T10:00:00Z",
                "note": "Salary",
            },
        )

        search_by_account = await ac.get("/v1/transactions", params={"q": "Axis"})
        search_by_date = await ac.get(
            "/v1/transactions",
            params={"q": "22/3/2026", "tz_offset_minutes": -330},
        )
        sort_by_amount_asc = await ac.get(
            "/v1/transactions",
            params={"sort_by": "amount", "sort_dir": "asc", "limit": 10},
        )

    assert search_by_account.status_code == 200
    axis_records = search_by_account.json()
    assert len(axis_records) == 2
    assert all(item["account_id"] == axis_id for item in axis_records)

    assert search_by_date.status_code == 200
    date_records = search_by_date.json()
    assert len(date_records) == 1
    assert date_records[0]["amount"] == "100.00"

    assert sort_by_amount_asc.status_code == 200
    sorted_records = sort_by_amount_asc.json()
    amounts = [item["amount"] for item in sorted_records]
    assert amounts == sorted(amounts, key=lambda value: float(value))
