from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session, select

from app.core.security import AuthenticatedUser, get_current_user
from app.db.session import get_session
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate


router = APIRouter(prefix="/categories", tags=["categories"])


def _parse_user_id(raw_user_id: str) -> UUID:
    try:
        return UUID(raw_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user id is not a valid UUID",
        ) from exc


def _get_category_or_404(session: Session, category_id: int, user_id: UUID) -> Category:
    category = session.exec(
        select(Category).where(
            Category.id == category_id,
            Category.user_id == user_id,
        )
    ).first()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return category


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> CategoryRead:
    user_id = _parse_user_id(current_user.user_id)
    category = Category(
        user_id=user_id,
        name=payload.name,
        kind=payload.kind,
        is_default=payload.is_default,
    )
    session.add(category)
    session.commit()
    session.refresh(category)
    return CategoryRead.model_validate(category)


@router.get("", response_model=list[CategoryRead])
def list_categories(
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[CategoryRead]:
    user_id = _parse_user_id(current_user.user_id)
    records = session.exec(
        select(Category)
        .where(Category.user_id == user_id)
        .order_by(Category.kind, Category.name)
    ).all()
    return [CategoryRead.model_validate(record) for record in records]


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(
    category_id: int,
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> CategoryRead:
    user_id = _parse_user_id(current_user.user_id)
    category = _get_category_or_404(session, category_id, user_id)
    return CategoryRead.model_validate(category)


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> CategoryRead:
    user_id = _parse_user_id(current_user.user_id)
    category = _get_category_or_404(session, category_id, user_id)
    changes = payload.model_dump(exclude_unset=True)

    for key, value in changes.items():
        setattr(category, key, value)

    session.add(category)
    session.commit()
    session.refresh(category)
    return CategoryRead.model_validate(category)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
def delete_category(
    category_id: int,
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Response:
    user_id = _parse_user_id(current_user.user_id)
    category = _get_category_or_404(session, category_id, user_id)
    session.delete(category)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
