"""Тесты аутентификации, токенов и разграничения прав."""

from __future__ import annotations

from app.models import Employee, EmployeeRole
from app.security import (
    create_token,
    decode_token,
    hash_password,
    verify_password,
)

from tests.conftest import bearer, login


def _make_employee(db, username: str, role: EmployeeRole) -> Employee:
    emp = Employee(
        username=username,
        password_hash=hash_password("secret123"),
        last_name="Пользователь",
        first_name=username.capitalize(),
        role=role,
        is_active=True,
    )
    db.add(emp)
    db.commit()
    return emp


# ---------------------------------------------------------------- хеширование

def test_password_hash_is_not_plain():
    stored = hash_password("secret123")
    assert stored != "secret123"
    assert stored.startswith("pbkdf2_sha256$")


def test_verify_password_ok():
    stored = hash_password("secret123")
    assert verify_password("secret123", stored) is True


def test_verify_password_wrong():
    stored = hash_password("secret123")
    assert verify_password("wrong", stored) is False


def test_verify_password_empty():
    assert verify_password("", hash_password("secret123")) is False


def test_verify_password_malformed():
    assert verify_password("secret123", "garbage") is False


# ------------------------------------------------------------------- токены

def test_token_roundtrip():
    token = create_token(10, "admin")
    data = decode_token(token)
    assert data is not None
    assert data["sub"] == 10
    assert data["role"] == "admin"
    assert "exp" in data


def test_token_tampered_rejected():
    token = create_token(10, "admin")
    head, payload, signature = token.split(".")
    forged = f"{head}.{payload}.{'A' * len(signature)}"
    assert decode_token(forged) is None


def test_token_garbage_rejected():
    assert decode_token("not-a-token") is None
    assert decode_token("a.b.c") is None


# ------------------------------------------------------------------- вход

def test_login_ok(client, db):
    _make_employee(db, "tester", EmployeeRole.engineer)
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "tester", "password": "secret123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["username"] == "tester"
    assert body["access_token"]
    assert decode_token(body["access_token"]) is not None


def test_login_wrong_password(client, db):
    _make_employee(db, "tester", EmployeeRole.engineer)
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "tester", "password": "wrong-pass"},
    )
    assert resp.status_code == 401
    assert "логин" in resp.json()["detail"].lower()


def test_login_unknown_user(client, db):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "ghost", "password": "x"},
    )
    assert resp.status_code == 401


def test_login_empty_username(client, db):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "", "password": "x"},
    )
    assert resp.status_code == 422


def test_me_requires_token(client, db):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_returns_user(client, db):
    _make_employee(db, "tester", EmployeeRole.engineer)
    token = login(client, "tester", "secret123")
    resp = client.get("/api/v1/auth/me", headers=bearer(token))
    assert resp.status_code == 200
    assert resp.json()["username"] == "tester"


def test_me_inactive_user_rejected(client, db):
    emp = _make_employee(db, "blocked", EmployeeRole.engineer)
    token = create_token(emp.id, "engineer")
    emp.is_active = False
    db.commit()
    resp = client.get("/api/v1/auth/me", headers=bearer(token))
    assert resp.status_code == 401


# ------------------------------------------------------ разграничение прав

def test_endpoints_require_token(client, db):
    for method, path in [
        ("GET", "/api/v1/tickets"),
        ("GET", "/api/v1/warehouse"),
        ("GET", "/api/v1/keys"),
        ("GET", "/api/v1/clients"),
        ("GET", "/api/v1/brigades"),
        ("GET", "/api/v1/refs/addresses"),
    ]:
        resp = getattr(client, method.lower())(path)
        assert resp.status_code == 401, f"{path} должен требовать токен"


def test_engineer_cannot_create_ticket(client, db, sample):
    _make_employee(db, "eng", EmployeeRole.engineer)
    token = login(client, "eng", "secret123")
    resp = client.post(
        "/api/v1/tickets",
        json={"client_id": sample["client"].id, "address_id": sample["address"].id},
        headers=bearer(token),
    )
    assert resp.status_code == 403
    assert "Недостаточно прав" in resp.json()["detail"]


def test_engineer_can_read_tickets(client, db, sample):
    _make_employee(db, "eng", EmployeeRole.engineer)
    token = login(client, "eng", "secret123")
    resp = client.get("/api/v1/tickets", headers=bearer(token))
    assert resp.status_code == 200


def test_dispatch_roles_can_create_ticket(client, db, sample):
    _make_employee(db, "disp", EmployeeRole.dispatcher)
    token = login(client, "disp", "secret123")
    resp = client.post(
        "/api/v1/tickets",
        json={"client_id": sample["client"].id, "address_id": sample["address"].id},
        headers=bearer(token),
    )
    assert resp.status_code == 201


def test_engineer_cannot_create_equipment(client, db):
    _make_employee(db, "eng", EmployeeRole.engineer)
    token = login(client, "eng", "secret123")
    resp = client.post(
        "/api/v1/warehouse",
        json={
            "name": "Кабель оптический",
            "category": "optical_cable",
            "unit": "м",
            "initial_quantity": 100,
            "min_quantity": 10,
        },
        headers=bearer(token),
    )
    assert resp.status_code == 403


def test_warehouse_role_can_create_equipment(client, db):
    _make_employee(db, "wh", EmployeeRole.warehouse_manager)
    token = login(client, "wh", "secret123")
    resp = client.post(
        "/api/v1/warehouse",
        json={
            "name": "Кабель оптический",
            "category": "optical_cable",
            "unit": "м",
            "initial_quantity": 100,
            "min_quantity": 10,
        },
        headers=bearer(token),
    )
    assert resp.status_code == 201
    assert resp.json()["sku"]


def test_admin_has_wide_access(client, db, sample):
    _make_employee(db, "root", EmployeeRole.admin)
    token = login(client, "root", "secret123")
    assert client.get("/api/v1/tickets", headers=bearer(token)).status_code == 200
    assert client.get("/api/v1/warehouse", headers=bearer(token)).status_code == 200
    assert client.get("/api/v1/keys", headers=bearer(token)).status_code == 200