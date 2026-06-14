"""
backend/app/core/security.py

Tầng lõi xử lý:
  - Hash / verify mật khẩu (bcrypt + SHA-256 pre-hash để tránh lỗi 72 bytes)
  - Tạo / giải mã JWT token
  - Dependency phân quyền: get_current_manager / get_current_employee
"""

import hashlib
from datetime import datetime, timedelta

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings
from .response import UnauthorizedException, ForbiddenException

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


# ─────────────────────────────────────────────────────────────────────────
# PASSWORD HASHING
# ─────────────────────────────────────────────────────────────────────────
def _prep_password(password: str) -> str:
    """SHA-256 trước khi bcrypt để hỗ trợ mật khẩu dài vô hạn (tránh lỗi 72 bytes)."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    return pwd_context.hash(_prep_password(password))


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(_prep_password(plain), hashed)
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────
# JWT TOKEN
# ─────────────────────────────────────────────────────────────────────────
def create_token(data: dict) -> str:
    payload = data.copy()
    expire = datetime.utcnow() + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    payload.update({"exp": expire})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


# ─────────────────────────────────────────────────────────────────────────
# DEPENDENCIES — PHÂN QUYỀN THEO ROLE
# ─────────────────────────────────────────────────────────────────────────
def get_current_manager(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise UnauthorizedException("Token không hợp lệ hoặc đã hết hạn")
    if payload.get("role") != "manager":
        raise ForbiddenException("Không có quyền truy cập")
    return payload


def get_current_employee(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise UnauthorizedException("Token không hợp lệ hoặc đã hết hạn")
    if payload.get("role") != "employee":
        raise ForbiddenException("Không có quyền truy cập")
    return payload
