from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session, select

from app.core.security import AuthenticatedUser, get_current_user
from app.db.session import get_session
from app.models.account import Account
from app.schemas.account import AccountCreate, AccountRead, AccountUpdate


router = APIRouter(prefix="/accounts", tags=["accounts"])


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
            detail="Account not found",
        )
    return account


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate,
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AccountRead:
    user_id = _parse_user_id(current_user.user_id)
    account = Account(
        user_id=user_id,
        name=payload.name,
        type=payload.type,
        balance=payload.balance,
        currency=payload.currency.upper(),
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return AccountRead.model_validate(account)


@router.get("", response_model=list[AccountRead])
def list_accounts(
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[AccountRead]:
    user_id = _parse_user_id(current_user.user_id)
    records = session.exec(
        select(Account).where(Account.user_id == user_id).order_by(Account.id)
    ).all()
    return [AccountRead.model_validate(record) for record in records]


@router.get("/{account_id}", response_model=AccountRead)
def get_account(
    account_id: int,
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AccountRead:
    user_id = _parse_user_id(current_user.user_id)
    account = _get_account_or_404(session, account_id, user_id)
    return AccountRead.model_validate(account)


@router.patch("/{account_id}", response_model=AccountRead)
def update_account(
    account_id: int,
    payload: AccountUpdate,
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AccountRead:
    user_id = _parse_user_id(current_user.user_id)
    account = _get_account_or_404(session, account_id, user_id)
    changes = payload.model_dump(exclude_unset=True)
    if "currency" in changes and changes["currency"] is not None:
        changes["currency"] = changes["currency"].upper()

    for key, value in changes.items():
        setattr(account, key, value)

    session.add(account)
    session.commit()
    session.refresh(account)
    return AccountRead.model_validate(account)


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
def delete_account(
    account_id: int,
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Response:
    user_id = _parse_user_id(current_user.user_id)
    account = _get_account_or_404(session, account_id, user_id)
    session.delete(account)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
