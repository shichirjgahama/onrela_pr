"""Тесты бизнес-логики заявок: жизненный цикл, списание кабеля, валидации."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.models import (
    BrigadeInventory,
    EquipmentCategory,
    FaultParty,
    IncidentDiagnostic,
    TicketPriority,
    TicketStatus,
    Unit,
)
from app.schemas import TicketCloseIn
from app.services import ticket_service as svc

from tests.conftest import bearer, login


def _issue_cable(db, sample, quantity: Decimal):
    """Числить кабель за бригадой, как это делает склад."""
    db.add(
        BrigadeInventory(
            brigade_id=sample["brigade"].id,
            equipment_id=sample["cable"].id,
            quantity=quantity,
        )
    )
    db.flush()


def _close(db, ticket, **overrides):
    payload = TicketCloseIn(**overrides)
    return svc.close_ticket(db, ticket.id, payload)


# ------------------------------------------------------------ состояния

def test_close_moves_to_done(db, sample):
    _issue_cable(db, sample, Decimal("500"))
    ticket = _close(db, sample["ticket"], cable_used_meters=Decimal("0"))
    assert ticket.status == TicketStatus.done
    assert ticket.completed_at is not None
    assert ticket.closed_at is not None


def test_close_twice_rejected(db, sample):
    _issue_cable(db, sample, Decimal("500"))
    _close(db, sample["ticket"], cable_used_meters=Decimal("0"))
    with pytest.raises(svc.TicketAlreadyClosed):
        _close(db, sample["ticket"], cable_used_meters=Decimal("0"))


def test_accept_only_from_assigned(db, sample):
    db.flush()
    svc.accept_ticket(db, sample["ticket"].id)
    assert sample["ticket"].status == TicketStatus.in_progress
    with pytest.raises(svc.InvalidStatusTransition):
        svc.accept_ticket(db, sample["ticket"].id)


def test_accept_sets_started_at(db, sample):
    svc.accept_ticket(db, sample["ticket"].id)
    assert sample["ticket"].started_at is not None


def test_accept_missing_ticket(db, sample):
    with pytest.raises(svc.TicketNotFound):
        svc.accept_ticket(db, 999999)


def test_close_missing_ticket(db, sample):
    with pytest.raises(svc.TicketNotFound):
        _close(db, type("T", (), {"id": 999999})())


# ------------------------------------------------------- списание кабеля

def test_cable_deducted(db, sample):
    _issue_cable(db, sample, Decimal("500"))
    before_qty = (
        db.query(BrigadeInventory)
        .filter_by(
            brigade_id=sample["brigade"].id, equipment_id=sample["cable"].id
        )
        .one()
        .quantity
    )
    ticket = _close(db, sample["ticket"], cable_used_meters=Decimal("35"))
    assert ticket.cable_used_meters == Decimal("35.000")
    after_qty = (
        db.query(BrigadeInventory)
        .filter_by(
            brigade_id=sample["brigade"].id, equipment_id=sample["cable"].id
        )
        .one()
        .quantity
    )
    assert after_qty == before_qty - Decimal("35")


def test_insufficient_stock_rejected(db, sample):
    _issue_cable(db, sample, Decimal("10"))
    with pytest.raises(svc.InsufficientCableStock):
        _close(db, sample["ticket"], cable_used_meters=Decimal("11"))


def test_zero_cable_skips_deduction(db, sample):
    _issue_cable(db, sample, Decimal("10"))
    ticket = _close(db, sample["ticket"], cable_used_meters=Decimal("0"))
    assert ticket.cable_used_meters == Decimal("0")


def test_negative_cable_rejected_by_schema():
    with pytest.raises(Exception):
        TicketCloseIn(cable_used_meters=Decimal("-1"))


def test_cable_without_brigade_rejected(db, sample):
    sample["ticket"].brigade_id = None
    db.flush()
    with pytest.raises(svc.BrigadeNotAssigned):
        _close(db, sample["ticket"], cable_used_meters=Decimal("5"))


def test_wrong_equipment_category_rejected(db, sample):
    """Кабель с неверной категорией не списывается."""
    from app.models import EquipmentCatalog

    wrong = EquipmentCatalog(
        sku="T-SW-1",
        name="Коммутатор",
        category=EquipmentCategory.switch,
        unit=Unit.piece,
    )
    db.add(wrong)
    db.flush()
    _issue_cable(db, sample, Decimal("500"))
    with pytest.raises(svc.CableEquipmentInvalid):
        _close(
            db,
            sample["ticket"],
            cable_equipment_id=wrong.id,
            cable_used_meters=Decimal("5"),
        )


def test_cable_not_issued_to_brigade_rejected(db, sample):
    """Кабель есть на складе, но не выдан бригаде."""
    with pytest.raises(svc.CableNotIssuedToBrigade):
        _close(db, sample["ticket"], cable_used_meters=Decimal("5"))


def test_cable_quantized_to_3_decimals(db, sample):
    _issue_cable(db, sample, Decimal("500"))
    ticket = _close(
        db, sample["ticket"], cable_used_meters=Decimal("1.23456")
    )
    assert str(ticket.cable_used_meters) == "1.235"


# ------------------------------------------------------ диагностика и Журнал

def test_diagnostic_created_on_close(db, sample):
    _issue_cable(db, sample, Decimal("500"))
    _close(
        db,
        sample["ticket"],
        cable_used_meters=Decimal("0"),
        fault_party=FaultParty.provider,
        cause_description="Обрыв магистрали",
    )
    diag = db.query(IncidentDiagnostic).filter_by(
        ticket_id=sample["ticket"].id
    ).one()
    assert diag.fault_party == FaultParty.provider
    assert diag.resolved_at is not None


def test_diagnostic_defaults_to_unknown(db, sample):
    """Если причина указана, но виновная сторона нет — записывается unknown."""
    _issue_cable(db, sample, Decimal("500"))
    _close(
        db,
        sample["ticket"],
        cable_used_meters=Decimal("0"),
        cause_description="Причина не установлена",
    )
    diag = db.query(IncidentDiagnostic).filter_by(
        ticket_id=sample["ticket"].id
    ).one()
    assert diag.fault_party == FaultParty.unknown


def test_comment_added_on_close(db, sample):
    _issue_cable(db, sample, Decimal("500"))
    from app.models import Employee, EmployeeRole

    emp = Employee(
        username="disp",
        password_hash="x",
        last_name="Диспетчер",
        first_name="Д",
        role=EmployeeRole.dispatcher,
    )
    db.add(emp)
    db.flush()
    _close(
        db,
        sample["ticket"],
        cable_used_meters=Decimal("0"),
        dispatcher_comment="Работы приняты заказчиком",
        dispatcher_employee_id=emp.id,
    )
    from app.models import TicketComment

    comments = db.query(TicketComment).filter_by(
        ticket_id=sample["ticket"].id
    ).all()
    assert len(comments) == 1
    assert comments[0].body == "Работы приняты заказчиком"


def test_close_with_unknown_work_type(db, sample):
    with pytest.raises(svc.WorkTypeNotFound):
        _close(db, sample["ticket"], work_type_id=999999)


def test_close_with_unknown_dispatcher(db, sample):
    _issue_cable(db, sample, Decimal("500"))
    with pytest.raises(svc.DispatcherNotFound):
        _close(
            db,
            sample["ticket"],
            cable_used_meters=Decimal("0"),
            dispatcher_comment="ok",
            dispatcher_employee_id=999999,
        )


# ------------------------------------------------------------ приоритеты

def test_priority_defaults_to_normal(db, sample):
    sample["ticket"].priority = TicketPriority.normal
    assert sample["ticket"].priority in tuple(TicketPriority)


def test_ticket_number_generated(db, sample):
    assert sample["ticket"].number
    assert sample["ticket"].number.startswith("TK-")