from __future__ import annotations

import time
from typing import Any

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwk, jwt
from jose.utils import base64url_decode
from pydantic import BaseModel

from app.core.config import settings


bearer_scheme = HTTPBearer(auto_error=False)
_JWKS_CACHE: dict[str, dict[str, Any]] = {}
_JWKS_LAST_FETCHED = 0.0
_JWKS_CACHE_TTL_SECONDS = 3600


class AuthenticatedUser(BaseModel):
	user_id: str
	email: str | None = None
	role: str | None = None
	raw_claims: dict[str, Any]


def _auth_error(detail: str = "Invalid authentication credentials") -> HTTPException:
	return HTTPException(
		status_code=status.HTTP_401_UNAUTHORIZED,
		detail=detail,
		headers={"WWW-Authenticate": "Bearer"},
	)


def _get_jwks(force_refresh: bool = False) -> dict[str, dict[str, Any]]:
	global _JWKS_CACHE, _JWKS_LAST_FETCHED

	now = time.time()
	cache_is_fresh = now - _JWKS_LAST_FETCHED < _JWKS_CACHE_TTL_SECONDS
	if _JWKS_CACHE and cache_is_fresh and not force_refresh:
		return _JWKS_CACHE

	if not settings.SUPABASE_URL:
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail="SUPABASE_URL is not configured",
		)

	try:
		response = httpx.get(settings.supabase_jwks_url, timeout=5.0)
		response.raise_for_status()
	except httpx.HTTPError as exc:
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail="Unable to fetch Supabase signing keys",
		) from exc

	keys = response.json().get("keys", [])
	if not keys:
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail="Supabase signing keys are unavailable",
		)

	_JWKS_CACHE = {key["kid"]: key for key in keys if "kid" in key}
	_JWKS_LAST_FETCHED = now
	return _JWKS_CACHE


def _verify_signature(token: str) -> dict[str, Any]:
	try:
		header = jwt.get_unverified_header(token)
	except Exception as exc:
		raise _auth_error("Malformed authentication token") from exc

	kid = header.get("kid")
	algorithm = header.get("alg")
	if not kid or not algorithm:
		raise _auth_error("Missing token signing metadata")

	jwks = _get_jwks()
	jwk_data = jwks.get(kid)
	if jwk_data is None:
		jwks = _get_jwks(force_refresh=True)
		jwk_data = jwks.get(kid)
	if jwk_data is None:
		raise _auth_error("Unknown token signing key")

	signing_input, encoded_signature = token.rsplit(".", 1)
	decoded_signature = base64url_decode(encoded_signature.encode("utf-8"))
	public_key = jwk.construct(jwk_data, algorithm)
	if not public_key.verify(signing_input.encode("utf-8"), decoded_signature):
		raise _auth_error("Invalid authentication token signature")

	try:
		return jwt.get_unverified_claims(token)
	except Exception as exc:
		raise _auth_error("Unable to read authentication token claims") from exc


def _validate_claims(claims: dict[str, Any]) -> AuthenticatedUser:
	now = int(time.time())
	exp = claims.get("exp")
	nbf = claims.get("nbf")
	issuer = claims.get("iss")
	audience = claims.get("aud")
	user_id = claims.get("sub")

	if exp is not None and int(exp) <= now:
		raise _auth_error("Authentication token has expired")
	if nbf is not None and int(nbf) > now:
		raise _auth_error("Authentication token is not yet valid")
	if issuer != settings.supabase_issuer:
		raise _auth_error("Authentication token issuer is invalid")

	expected_audience = settings.SUPABASE_JWT_AUDIENCE
	if isinstance(audience, str):
		valid_audience = audience == expected_audience
	elif isinstance(audience, list):
		valid_audience = expected_audience in audience
	else:
		valid_audience = False
	if not valid_audience:
		raise _auth_error("Authentication token audience is invalid")

	if not user_id:
		raise _auth_error("Authentication token is missing a subject")

	return AuthenticatedUser(
		user_id=user_id,
		email=claims.get("email"),
		role=claims.get("role"),
		raw_claims=claims,
	)


def get_current_user(
	credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser:
	if credentials is None or credentials.scheme.lower() != "bearer":
		raise _auth_error("Authentication credentials were not provided")

	claims = _verify_signature(credentials.credentials)
	return _validate_claims(claims)
