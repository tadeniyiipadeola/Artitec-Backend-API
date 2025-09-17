# src/utils.py
import secrets, string
from datetime import datetime, timedelta
from passlib.hash import bcrypt
import jwt
from config.settings import JWT_SECRET, JWT_ISS, ACCESS_TTL_MIN

def gen_public_id(n=26):
    alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))

def gen_token_hex(n_bytes=32):
    return secrets.token_hex(n_bytes)

def hash_password(pw: str) -> str:
    return bcrypt.hash(pw)

def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.verify(pw, hashed)

def make_access_token(user_public_id: str, user_id: int, email: str) -> str:
    payload = {
        "sub": user_public_id,
        "uid": user_id,
        "email": email,
        "typ": "access",
        "iss": JWT_ISS,
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TTL_MIN)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")