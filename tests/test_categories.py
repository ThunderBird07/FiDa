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
async def test_create_and_list_categories(test_app) -> None:
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        create_response = await ac.post(
            "/v1/categories",
            json={
                "name": "Groceries",
                "kind": "expense",
                "is_default": False,
            },
        )
        list_response = await ac.get("/v1/categories")

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "Groceries"
    assert created["kind"] == "expense"
    assert created["is_default"] is False

    assert list_response.status_code == 200
    listed = list_response.json()
    assert len(listed) == 1
    assert listed[0]["id"] == created["id"]


@pytest.mark.asyncio
async def test_get_update_delete_category(test_app) -> None:
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        create_response = await ac.post(
            "/v1/categories",
            json={
                "name": "Salary",
                "kind": "income",
                "is_default": False,
            },
        )
        category_id = create_response.json()["id"]

        get_response = await ac.get(f"/v1/categories/{category_id}")
        update_response = await ac.patch(
            f"/v1/categories/{category_id}",
            json={"name": "Primary Salary", "is_default": True},
        )
        delete_response = await ac.delete(f"/v1/categories/{category_id}")
        after_delete_response = await ac.get(f"/v1/categories/{category_id}")

    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Salary"

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] == "Primary Salary"
    assert updated["is_default"] is True

    assert delete_response.status_code == 204
    assert after_delete_response.status_code == 404
