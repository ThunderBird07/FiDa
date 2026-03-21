from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.security import AuthenticatedUser, get_current_user
from app.db.session import get_session
from app.models.user import UserProfile
from app.schemas.profile import UserProfileRead, UserProfileUpdate


router = APIRouter(prefix="/profile", tags=["profile"])

COUNTRY_CURRENCY_MAP = {
    "AU": "AUD",
    "CA": "CAD",
    "DE": "EUR",
    "IN": "INR",
    "JP": "JPY",
    "LK": "LKR",
    "SG": "SGD",
    "AE": "AED",
    "GB": "GBP",
    "US": "USD",
}


def _currency_for_country(country_code: str, fallback_currency: str) -> str:
    code = str(country_code or "").upper()
    return COUNTRY_CURRENCY_MAP.get(code, (fallback_currency or "USD").upper())


def _parse_user_id(raw_user_id: str) -> UUID:
    try:
        return UUID(raw_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user id is not a valid UUID",
        ) from exc


def _get_or_create_profile(session: Session, current_user: AuthenticatedUser) -> UserProfile:
    user_id = _parse_user_id(current_user.user_id)

    profile = session.exec(select(UserProfile).where(UserProfile.id == user_id)).first()
    if profile is not None:
        return profile

    if not current_user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authenticated user email is missing",
        )

    # If a profile already exists for this email, reuse it to avoid duplicate rows.
    profile_by_email = session.exec(
        select(UserProfile).where(UserProfile.email == current_user.email)
    ).first()
    if profile_by_email is not None:
        if profile_by_email.id != user_id:
            profile_by_email.id = user_id
            session.add(profile_by_email)
            session.commit()
            session.refresh(profile_by_email)
        return profile_by_email

    profile = UserProfile(
        id=user_id,
        email=current_user.email,
    )
    session.add(profile)
    try:
        session.commit()
    except IntegrityError:
        # Handle concurrent creation safely by fetching the winner row.
        session.rollback()
        existing = session.exec(
            select(UserProfile).where(UserProfile.email == current_user.email)
        ).first()
        if existing is None:
            raise
        if existing.id != user_id:
            existing.id = user_id
            session.add(existing)
            session.commit()
            session.refresh(existing)
        return existing

    session.refresh(profile)
    return profile


@router.get("", response_model=UserProfileRead)
def get_profile(
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> UserProfileRead:
    profile = _get_or_create_profile(session, current_user)
    return UserProfileRead.model_validate(profile)


@router.patch("", response_model=UserProfileRead)
def update_profile(
    payload: UserProfileUpdate,
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> UserProfileRead:
    profile = _get_or_create_profile(session, current_user)
    changes = payload.model_dump(exclude_unset=True)
    if "currency" in changes and changes["currency"] is not None:
        changes["currency"] = changes["currency"].upper()
    if "country" in changes and changes["country"] is not None:
        changes["country"] = changes["country"].upper()
        changes["currency"] = _currency_for_country(changes["country"], profile.currency)

    for key, value in changes.items():
        setattr(profile, key, value)

    session.add(profile)
    session.commit()
    session.refresh(profile)
    return UserProfileRead.model_validate(profile)
