from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.models import (
    BrigadeInventory,
    Client,
    Employee,
    EquipmentCatalog,
    EquipmentCategory,
    FaultParty,
    IncidentDiagnostic,
    Ticket,
    TicketComment,
    TicketStatus,
    Unit,
    WorkType,
)
from app.schemas import TicketCloseIn


class TicketServiceError(Exception):
    pass


class TicketNotFound(TicketServiceError):
    pass


class TicketAlreadyClosed(TicketServiceError):
    pass


class TicketCancelled(TicketServiceError):
    pass


class BrigadeNotAssigned(TicketServiceError):
    pass


class WorkTypeNotFound(TicketServiceError):
    pass


class DispatcherNotFound(TicketServiceError):
    pass


class CableEquipmentNotFound(TicketServiceError):
    pass


class CableEquipmentInvalid(TicketServiceError):
    pass


class CableNotIssuedToBrigade(TicketServiceError):
    pass


class InsufficientCableStock(TicketServiceError):
    pass


def _load_ticket_for_response(db: Session, ticket_id: int) -> Ticket:
    stmt = (
        select(Ticket)
        .options(
            selectinload(Ticket.client).selectinload(Client.organization),
            selectinload(Ticket.address),
            selectinload(Ticket.brigade),
            selectinload(Ticket.work_type),
            selectinload(Ticket.cable_equipment),
        )
        .where(Ticket.id == ticket_id)
    )
    ticket = db.scalar(stmt)
    if ticket is None:
        raise TicketNotFound
    return ticket


def _resolve_cable_equipment(
    db: Session,
    cable_equipment_id: int | None,
) -> EquipmentCatalog:
    if cable_equipment_id is not None:
        equipment = db.get(EquipmentCatalog, cable_equipment_id)
        if equipment is None:
            raise CableEquipmentNotFound
        return equipment

    stmt = (
        select(EquipmentCatalog)
        .where(EquipmentCatalog.category == EquipmentCategory.optical_cable)
        .order_by(EquipmentCatalog.id)
        .limit(1)
    )
    equipment = db.scalar(stmt)

    if equipment is None:
        raise CableEquipmentNotFound

    return equipment


def _deduct_cable(
    db: Session,
    ticket: Ticket,
    payload: TicketCloseIn,
) -> None:
    cable_used = payload.cable_used_meters

    if cable_used <= Decimal("0"):
        ticket.cable_used_meters = Decimal("0")
        return

    if ticket.brigade_id is None:
        raise BrigadeNotAssigned

    equipment = _resolve_cable_equipment(db, payload.cable_equipment_id)

    if equipment.category != EquipmentCategory.optical_cable:
        raise CableEquipmentInvalid

    if equipment.unit != Unit.meter:
        raise CableEquipmentInvalid

    inventory = db.scalar(
        select(BrigadeInventory).where(
            BrigadeInventory.brigade_id == ticket.brigade_id,
            BrigadeInventory.equipment_id == equipment.id,
        )
    )

    if inventory is None:
        raise CableNotIssuedToBrigade

    if inventory.quantity < cable_used:
        raise InsufficientCableStock

    # Атомарное списание.
    # Даже если параллельно пойдет другой запрос, SQL-условие не даст уйти в минус.
    stmt = (
        update(BrigadeInventory)
        .where(
            BrigadeInventory.id == inventory.id,
            BrigadeInventory.quantity >= cable_used,
        )
        .values(
            quantity=BrigadeInventory.quantity - cable_used,
            updated_at=datetime.now(timezone.utc),
        )
    )

    result = db.execute(stmt)

    if result.rowcount != 1:
        raise InsufficientCableStock

    ticket.cable_equipment_id = equipment.id
    ticket.cable_used_meters = cable_used


def close_ticket(
    db: Session,
    ticket_id: int,
    payload: TicketCloseIn,
) -> Ticket:
    ticket = db.get(Ticket, ticket_id)

    if ticket is None:
        raise TicketNotFound

    if ticket.status == TicketStatus.done:
        raise TicketAlreadyClosed

    if ticket.status == TicketStatus.cancelled:
        raise TicketCancelled

    if payload.work_type_id is not None:
        work_type = db.get(WorkType, payload.work_type_id)
        if work_type is None:
            raise WorkTypeNotFound
        ticket.work_type_id = payload.work_type_id

    _deduct_cable(db, ticket, payload)

    now = datetime.now(timezone.utc)

    ticket.status = TicketStatus.done
    ticket.completed_at = now
    ticket.closed_at = now

    if payload.dispatcher_comment:
        employee_id = payload.dispatcher_employee_id

        if employee_id is not None:
            employee = db.get(Employee, employee_id)
            if employee is None:
                raise DispatcherNotFound

        db.add(
            TicketComment(
                ticket_id=ticket.id,
                employee_id=employee_id,
                body=payload.dispatcher_comment,
            )
        )

    if payload.fault_party is not None or payload.cause_description:
        diagnostic = db.scalar(
            select(IncidentDiagnostic).where(
                IncidentDiagnostic.ticket_id == ticket.id
            )
        )

        if diagnostic is not None:
            if payload.fault_party is not None:
                diagnostic.fault_party = payload.fault_party
            if payload.cause_description:
                diagnostic.cause_description = payload.cause_description
            diagnostic.resolved_at = now
        else:
            db.add(
                IncidentDiagnostic(
                    ticket_id=ticket.id,
                    fault_party=payload.fault_party or FaultParty.unknown,
                    cause_description=payload.cause_description,
                    resolved_at=now,
                )
            )

    db.commit()

    return _load_ticket_for_response(db, ticket_id)
class InvalidStatusTransition(Exception):
    """Недопустимый переход статуса заявки."""


def accept_ticket(db: Session, ticket_id: int) -> Ticket:
    """Бригада принимает назначенную заявку в работу."""
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise TicketNotFound
    if ticket.status != TicketStatus.assigned:
        raise InvalidStatusTransition
    ticket.status = TicketStatus.in_progress
    if ticket.started_at is None:
        ticket.started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)
    return ticket
