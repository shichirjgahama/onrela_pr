"""Общие фикстуры: изолированная тестовая БД и готовые данные."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Пока выполняется весь прогон, устанавливаем тестовое имя БД до импорта приложения.
os.environ.setdefault("ISP_ERP_TEST", "1")

from app import models  # noqa: E402,F401
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    Address,
    Brigade,
    Client,
    Employee,
    EmployeeRole,
    EquipmentCatalog,
    EquipmentCategory,
    IncidentDiagnostic,
    KeyLog,
    Ticket,
    TicketComment,
    TicketPriority,
    TicketStatus,
    Unit,
    WarehouseStock,
    WorkType,
)
from app.security import create_token  # noqa: E402


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(session_factory):
    def _override():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def sample(db):
    """Минимальный согласованный набор данных."""
    emp = Employee(
        username="tester",
        password_hash="x",
        last_name="Тестов",
        first_name="Иван",
        role=EmployeeRole.engineer,
    )
    db.add(emp)
    brigade = Brigade(name="Бригада Тест", lead_employee=emp)
    client_obj = Client(last_name="Клиент", first_name="Кл")
    db.add_all([brigade, client_obj])
    db.flush()

    address = Address(street="Тестовая", house="1")
    cable = EquipmentCatalog(
        sku="T-OPT-1",
        name="Кабель оптический",
        category=EquipmentCategory.optical_cable,
        unit=Unit.meter,
    )
    work = WorkType(code="T-01", name="Сварка", requires_optical_cable=True)
    db.add_all([address, cable, work])
    db.flush()

    db.add(
        WarehouseStock(equipment_id=cable.id, quantity=500, min_quantity=50)
    )
    ticket = Ticket(
        client_id=client_obj.id,
        address_id=address.id,
        brigade_id=brigade.id,
        work_type_id=work.id,
        status=TicketStatus.assigned,
        priority=TicketPriority.high,
        description="Тестовая заявка",
    )
    db.add(ticket)
    db.flush()

    return {
        "employee": emp,
        "brigade": brigade,
        "client": client_obj,
        "address": address,
        "cable": cable,
        "work": work,
        "ticket": ticket,
    }


@pytest.fixture()
def auth_tokens():
    return {
        "admin": create_token(1, "admin"),
        "dispatcher": create_token(2, "dispatcher"),
        "engineer": create_token(3, "engineer"),
        "warehouse": create_token(4, "warehouse_manager"),
    }


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def login(client: TestClient, username: str, password: str) -> str:
    """Создаёт пользователя, логинится и возвращает токен."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]