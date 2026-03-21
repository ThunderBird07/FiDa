from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import delete
from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import AuthenticatedUser, get_current_user
from app.db.session import get_session
from app.models.account import Account
from app.models.transaction import Transaction
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
        select(Account).where(
            Account.id == account_id,
            Account.user_id == user_id,
            Account.is_active.is_(True),
        )
    ).first()
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    return account


def _has_encryption_payload(encrypted_blob: str | None, encryption_nonce: str | None) -> bool:
    return bool(encrypted_blob and encryption_nonce)


def _validate_encryption_fields(
    *,
    encrypted_blob: str | None,
    encryption_nonce: str | None,
    requires_encrypted_write: bool,
) -> None:
    has_blob = bool(encrypted_blob)
    has_nonce = bool(encryption_nonce)
    if has_blob != has_nonce:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="encrypted_blob and encryption_nonce must be provided together",
        )

    if requires_encrypted_write and not (has_blob and has_nonce):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Encrypted payload is required for this write",
        )


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate,
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AccountRead:
    _validate_encryption_fields(
        encrypted_blob=payload.encrypted_blob,
        encryption_nonce=payload.encryption_nonce,
        requires_encrypted_write=settings.ENFORCE_ENCRYPTED_WRITES,
    )

    user_id = _parse_user_id(current_user.user_id)
    account = Account(
        user_id=user_id,
        name=payload.name,
        type=payload.type.value,
        balance=payload.balance,
        currency=payload.currency.upper(),
        encrypted_blob=payload.encrypted_blob,
        encryption_nonce=payload.encryption_nonce,
        encryption_version=payload.encryption_version,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return AccountRead.model_validate(account)


@router.get("", response_model=list[AccountRead])
def list_accounts(
    include_inactive: bool = Query(default=False),
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[AccountRead]:
    user_id = _parse_user_id(current_user.user_id)
    statement = select(Account).where(Account.user_id == user_id)
    if not include_inactive:
        statement = statement.where(Account.is_active.is_(True))

    records = session.exec(statement.order_by(Account.id)).all()
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

    encrypted_blob = changes.get("encrypted_blob")
    encryption_nonce = changes.get("encryption_nonce")
    updates_sensitive_fields = any(
        field in changes for field in ("name", "type", "balance", "currency")
    )
    requires_encrypted_write = settings.ENFORCE_ENCRYPTED_WRITES and updates_sensitive_fields
    _validate_encryption_fields(
        encrypted_blob=encrypted_blob,
        encryption_nonce=encryption_nonce,
        requires_encrypted_write=requires_encrypted_write,
    )

    if settings.ENFORCE_ENCRYPTED_WRITES and _has_encryption_payload(encrypted_blob, encryption_nonce):
        changes["encryption_version"] = changes.get("encryption_version") or account.encryption_version

    if "currency" in changes and changes["currency"] is not None:
        changes["currency"] = changes["currency"].upper()

    if "type" in changes and changes["type"] is not None:
        changes["type"] = changes["type"].value

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
    delete_transactions: bool = Query(default=False),
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Response:
    user_id = _parse_user_id(current_user.user_id)
    account = _get_account_or_404(session, account_id, user_id)

    has_transactions = session.exec(
        select(Transaction.id).where(
            Transaction.user_id == user_id,
            Transaction.account_id == account.id,
        ).limit(1)
    ).first()

    if has_transactions is not None:
        if delete_transactions:
            session.exec(
                delete(Transaction).where(
                    Transaction.user_id == user_id,
                    Transaction.account_id == account.id,
                )
            )
            session.flush()
            session.delete(account)
        else:
            account.is_active = False
            session.add(account)
    else:
        session.delete(account)

    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
