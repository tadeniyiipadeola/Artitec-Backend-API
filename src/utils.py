# src/utils.py
import logging
import secrets, string
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from passlib.context import CryptContext
import jwt
from config.settings import JWT_SECRET, JWT_ISS, ACCESS_TTL_MIN

logger = logging.getLogger(__name__)

# Centralized password hashing policy (allows painless future upgrades)
PWD_CONTEXT = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    # You can tune rounds via env if desired: bcrypt__rounds=12
)

SAFE_ALPHABET = string.ascii_letters + string.digits

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def gen_token_urlsafe(n_bytes: int = 32) -> str:
    """High-entropy, URL-safe token (good for jti, nonces, etc.)."""
    return secrets.token_urlsafe(n_bytes)

def gen_public_id(n: int = 26) -> str:
    return "".join(secrets.choice(SAFE_ALPHABET) for _ in range(n))

def gen_token_hex(n_bytes=32):
    return secrets.token_hex(n_bytes)

def hash_password(pw: str) -> str:
    if not pw:
        raise ValueError("Password must not be empty")
    return PWD_CONTEXT.hash(pw)

def verify_password(pw: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return PWD_CONTEXT.verify(pw, hashed)
    except Exception:
        logger.warning("Password verification failed due to malformed hash", exc_info=True)
        return False

def make_access_token(user_public_id: str, user_id: str, email: str) -> str:
    """Issue a short-lived access token.
    Includes standard claims and a jti for traceability.
    """
    if not user_public_id or not email:
        raise ValueError("user_public_id and email are required")
    issued_at = _now_utc()
    payload: Dict[str, Any] = {
        "sub": user_public_id,
        "uid": user_id,
        "email": email,
        "typ": "access",
        "iss": JWT_ISS,
        "iat": int(issued_at.timestamp()),
        "nbf": int(issued_at.timestamp()),
        "exp": int((issued_at + timedelta(minutes=ACCESS_TTL_MIN)).timestamp()),
        "jti": gen_token_urlsafe(18),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def decode_access_token(token: str, verify_iss: bool = True) -> Dict[str, Any]:
    """Decode & minimally validate an access token. Raises jwt exceptions on failure."""
    options = {"require": ["exp", "iat", "nbf", "sub", "typ"], "verify_signature": True}
    claims = jwt.decode(token, JWT_SECRET, algorithms=["HS256"], options=options)
    if verify_iss and claims.get("iss") != JWT_ISS:
        raise jwt.InvalidIssuerError("Invalid token issuer")
    if claims.get("typ") != "access":
        raise jwt.InvalidTokenError("Unexpected token type")
    return claims