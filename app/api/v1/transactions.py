from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import and_, or_
from sqlmodel import Session, select

from app.core.security import AuthenticatedUser, get_current_user
from app.db.session import get_session
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction, TransactionType
from app.schemas.transaction import TransactionCreate, TransactionRead, TransactionUpdate


router = APIRouter(prefix="/transactions", tags=["transactions"])


def _parse_user_id(raw_user_id: str) -> UUID:
    try:
        return UUID(raw_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user id is not a valid UUID",
        ) from exc


def _get_account_or_404(session: Session, account_id: int, user_id: UUID) -> Account:
    account = session.exec(
        select(Account).where(Account.id == account_id, Account.user_id == user_id)
    ).first()
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found for current user",
        )
    return account


def _get_category_or_404(session: Session, category_id: int, user_id: UUID) -> Category:
    category = session.exec(
        select(Category).where(
            Category.id == category_id,
            or_(Category.user_id == user_id, and_(Category.user_id.is_(None), Category.is_default.is_(True))),
        )
    ).first()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found for current user",
        )
    return category


def _get_transaction_or_404(session: Session, transaction_id: int, user_id: UUID) -> Transaction:
    transaction = session.exec(
        select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user_id)
    ).first()
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    return transaction


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> TransactionRead:
    user_id = _parse_user_id(current_user.user_id)
    _get_account_or_404(session, payload.account_id, user_id)

    if payload.category_id is not None:
        _get_category_or_404(session, payload.category_id, user_id)

    transaction = Transaction(
        user_id=user_id,
        account_id=payload.account_id,
        category_id=payload.category_id,
        type=payload.type,
        amount=payload.amount,
        occurred_at=payload.occurred_at or datetime.now(timezone.utc),
        note=payload.note,
    )
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return TransactionRead.model_validate(transaction)


@router.get("", response_model=list[TransactionRead])
def list_transactions(
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
    type_: TransactionType | None = Query(default=None, alias="type"),
    account_id: int | None = None,
    category_id: int | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> list[TransactionRead]:
    user_id = _parse_user_id(current_user.user_id)
    statement = select(Transaction).where(Transaction.user_id == user_id)

    if type_ is not None:
        statement = statement.where(Transaction.type == type_)
    if account_id is not None:
        statement = statement.where(Transaction.account_id == account_id)
    if category_id is not None:
        statement = statement.where(Transaction.category_id == category_id)
    if from_date is not None:
        statement = statement.where(Transaction.occurred_at >= from_date)
    if to_date is not None:
        statement = statement.where(Transaction.occurred_at <= to_date)

    records = session.exec(statement.order_by(Transaction.occurred_at.desc(), Transaction.id.desc())).all()
    return [TransactionRead.model_validate(record) for record in records]


@router.get("/{transaction_id}", response_model=TransactionRead)
def get_transaction(
    transaction_id: int,
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> TransactionRead:
    user_id = _parse_user_id(current_user.user_id)
    transaction = _get_transaction_or_404(session, transaction_id, user_id)
    return TransactionRead.model_validate(transaction)


@router.patch("/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> TransactionRead:
    user_id = _parse_user_id(current_user.user_id)
    transaction = _get_transaction_or_404(session, transaction_id, user_id)

    changes = payload.model_dump(exclude_unset=True)

    if "account_id" in changes and changes["account_id"] is not None:
        _get_account_or_404(session, changes["account_id"], user_id)

    if "category_id" in changes and changes["category_id"] is not None:
        _get_category_or_404(session, changes["category_id"], user_id)

    for key, value in changes.items():
        setattr(transaction, key, value)

    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return TransactionRead.model_validate(transaction)


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
def delete_transaction(
    transaction_id: int,
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Response:
    user_id = _parse_user_id(current_user.user_id)
    transaction = _get_transaction_or_404(session, transaction_id, user_id)
    session.delete(transaction)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
