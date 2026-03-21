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
