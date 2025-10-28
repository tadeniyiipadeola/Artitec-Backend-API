# config/dependencies.py

from typing import Optional, Iterable, Callable
from fastapi import Depends, HTTPException, Request, status
from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import timedelta

from config.db import get_db
from config.settings import JWT_SECRET, JWT_ALG, JWT_ISS  # ensure these exist
from model.user import Users

_LEEWAY = 10  # seconds of clock-skew tolerance

def _get_bearer_token(request: Request) -> str:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    return auth.split(" ", 1)[1].strip()

def _decode_access_token(token: str) -> dict:
    try:
        options = {"verify_aud": False}
        # Disable aud verification unless you explicitly set/expect it
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALG],
            issuer=JWT_ISS if JWT_ISS else None,
            options=options,
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Optional issuer/type checks (match your token minting)
    if JWT_ISS and payload.get("iss") != JWT_ISS:
        raise HTTPException(status_code=401, detail="Invalid token issuer")
    typ = payload.get("typ")
    if typ not in ("access", "bearer", None):
        raise HTTPException(status_code=401, detail="Invalid token type")
    return payload

def _load_user_from_claims(payload: dict, db: Session) -> Users:
    public_id: Optional[str] = payload.get("sub")
    uid: Optional[int] = payload.get("uid")

    if uid is not None:
        user = db.get(Users, uid)
    elif public_id:
        user = db.scalar(select(Users).where(Users.public_id == public_id))
    else:
        user = None

    if not user or user.status != "active":
        # Use 401 to avoid leaking existence; switch to 403 for inactive if you prefer
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user

def require_user(request: Request, db: Session = Depends(get_db)) -> Users:
    token = _get_bearer_token(request)
    payload = _decode_access_token(token)
    return _load_user_from_claims(payload, db)

# Optional helpers

def current_user_optional(request: Request, db: Session = Depends(get_db)) -> Optional[Users]:
    try:
        token = _get_bearer_token(request)
        payload = _decode_access_token(token)
        return _load_user_from_claims(payload, db)
    except HTTPException:
        return None

def require_roles(roles: Iterable[str]) -> Callable:
    """Factory that returns a dependency enforcing one of the given role keys."""
    role_set = set(roles)
    def _dep(user: Users = Depends(require_user)) -> Users:
        user_role_key = getattr(getattr(user, "role", None), "key", None)
        if user_role_key not in role_set:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user
    return _dep

def require_admin(user: Users = Depends(require_user)) -> Users:
    if getattr(getattr(user, "role", None), "key", None) != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    return user