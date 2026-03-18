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
async def test_create_and_list_accounts(test_app) -> None:
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        create_response = await ac.post(
            "/v1/accounts",
            json={
                "name": "Main Checking",
                "type": "bank",
                "balance": "1200.50",
                "currency": "usd",
            },
        )
        list_response = await ac.get("/v1/accounts")

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "Main Checking"
    assert created["type"] == "bank"
    assert created["balance"] == "1200.50"
    assert created["currency"] == "USD"

    assert list_response.status_code == 200
    listed = list_response.json()
    assert len(listed) == 1
    assert listed[0]["id"] == created["id"]


@pytest.mark.asyncio
async def test_get_update_delete_account(test_app) -> None:
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        create_response = await ac.post(
            "/v1/accounts",
            json={
                "name": "Cash Wallet",
                "type": "cash",
                "balance": "300.00",
                "currency": "usd",
            },
        )
        account_id = create_response.json()["id"]

        get_response = await ac.get(f"/v1/accounts/{account_id}")
        update_response = await ac.patch(
            f"/v1/accounts/{account_id}",
            json={"name": "Emergency Cash", "balance": "500.00"},
        )
        delete_response = await ac.delete(f"/v1/accounts/{account_id}")
        after_delete_response = await ac.get(f"/v1/accounts/{account_id}")

    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Cash Wallet"

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] == "Emergency Cash"
    assert updated["balance"] == "500.00"

    assert delete_response.status_code == 204
    assert after_delete_response.status_code == 404
