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
            email="profile@example.com",
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
async def test_get_profile_auto_creates_record(test_app) -> None:
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        first = await ac.get("/v1/profile")
        second = await ac.get("/v1/profile")

    assert first.status_code == 200
    assert second.status_code == 200

    first_payload = first.json()
    second_payload = second.json()
    assert first_payload["email"] == "profile@example.com"
    assert first_payload["id"] == second_payload["id"]


@pytest.mark.asyncio
async def test_update_profile_fields(test_app) -> None:
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.get("/v1/profile")
        updated = await ac.patch(
            "/v1/profile",
            json={
                "full_name": "FiDa User",
                "currency": "inr",
                "timezone": "Asia/Kolkata",
            },
        )

    assert updated.status_code == 200
    payload = updated.json()
    assert payload["full_name"] == "FiDa User"
    assert payload["currency"] == "INR"
    assert payload["timezone"] == "Asia/Kolkata"


@pytest.mark.asyncio
async def test_profile_requires_email_for_first_create() -> None:
    engine = _build_test_engine()
    SQLModel.metadata.create_all(engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    test_user_id = str(uuid4())

    def override_current_user() -> AuthenticatedUser:
        return AuthenticatedUser(
            user_id=test_user_id,
            email=None,
            role="authenticated",
            raw_claims={"sub": test_user_id},
        )

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = override_current_user
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/v1/profile")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "Authenticated user email is missing"
