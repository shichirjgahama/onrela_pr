"""Аутентификация и авторизация.

Учебный проект: пароли хешируются PBKDF2-HMAC-SHA256 (120 000 итераций),
токен — подписанный HMAC-SHA256 токен в формате JWT (без внешних зависимостей).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Iterable

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee

PBKDF2_ITERATIONS = 120_000
TOKEN_TTL_SECONDS = 12 * 60 * 60

# Секрет подписи токена. Для повторяемости учебного проекта задан константой;
# в промышленной системе значение читается из переменной окружения.
SECRET_KEY = os.environ.get("ISP_ERP_SECRET", "onrela-isp-erp-dev-secret")


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_token(employee_id: int, role: str) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64(
        json.dumps(
            {
                "sub": employee_id,
                "role": role,
                "exp": int(time.time()) + TOKEN_TTL_SECONDS,
                "iat": int(time.time()),
            }
        ).encode()
    )
    message = f"{header}.{payload}".encode()
    signature = _b64(hmac.new(SECRET_KEY.encode(), message, hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def decode_token(token: str) -> dict | None:
    try:
        header, payload, signature = token.split(".")
    except ValueError:
        return None
    message = f"{header}.{payload}".encode()
    expected = _b64(hmac.new(SECRET_KEY.encode(), message, hashlib.sha256).digest())
    if not hmac.compare_digest(expected, signature):
        return None
    try:
        data = json.loads(_b64decode(payload))
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or data.get("exp", 0) < time.time():
        return None
    return data


def get_token_from_request(request: Request) -> str | None:
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return None
    return authorization[len("Bearer ") :].strip() or None


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> Employee:
    """Зависимость: требует валидный токен и возвращает активного сотрудника."""
    token = get_token_from_request(request)
    if token is None:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    data = decode_token(token)
    if data is None:
        raise HTTPException(status_code=401, detail="Недействительный или просроченный токен")
    employee = db.get(Employee, data.get("sub"))
    if employee is None or not employee.is_active:
        raise HTTPException(status_code=401, detail="Сотрудник не найден или заблокирован")
    return employee


def require_roles(*roles: str):
    """Зависимость: допускает только указанные роли."""

    allowed: frozenset[str] = frozenset(roles)

    def dependency(user: Employee = Depends(get_current_user)) -> Employee:
        if user.role.value not in allowed:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Недостаточно прав для этого действия "
                    f"(роль «{user.role.value}» допускается только на просмотр)"
                ),
            )
        return user

    return dependency


def roles_from(roles: Iterable[str]) -> frozenset[str]:
    return frozenset(roles)
