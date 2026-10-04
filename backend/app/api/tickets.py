from datetime import datetime, timedelta, timezone
from decimal import Decimal

from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import (
    Brigade,
    Client,
    Employee,
    EmployeeRole,
    Ticket,
    TicketPriority,
    TicketStatus,
)
from app.reports.act_pdf import generate_completion_act
from app.schemas import TicketCloseIn, TicketListOut, TicketOut
from app.security import get_current_user, require_roles
from app.services import ticket_service

router = APIRouter(prefix="/tickets", tags=["tickets"])

# Ролевая модель раздела 4.1 отчёта:
# просмотр заявок доступен всем авторизованным сотрудникам,
# создание и назначение бригады — диспетчеру и администратору,
# приём в работу и закрытие списанием материалов — бригаде и администратору.
DISPATCH_ROLES = require_roles(
    EmployeeRole.dispatcher.value, EmployeeRole.admin.value
)
BRIGADE_ROLES = require_roles(
    EmployeeRole.engineer.value,
    EmployeeRole.brigade_lead.value,
    EmployeeRole.admin.value,
)


def _load_ticket_with_relations(db: Session, ticket_id: int) -> Ticket | None:
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
    return db.scalar(stmt)


@router.get("", response_model=TicketListOut)
def list_tickets(
    status: TicketStatus | None = None,
    brigade_id: int | None = None,
    search: str | None = Query(default=None, max_length=100),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    base_query = (
        select(Ticket)
        .options(
            selectinload(Ticket.client).selectinload(Client.organization),
            selectinload(Ticket.address),
            selectinload(Ticket.brigade),
            selectinload(Ticket.work_type),
        )
    )

    if status is not None:
        base_query = base_query.where(Ticket.status == status)
    if brigade_id is not None:
        base_query = base_query.where(Ticket.brigade_id == brigade_id)
    if search:
        search_like = f"%{search}%"
        base_query = base_query.where(
            Ticket.number.ilike(search_like) | Ticket.description.ilike(search_like)
        )

    count_query = select(func.count()).select_from(base_query.subquery())
    total = db.scalar(count_query) or 0

    stmt = (
        base_query.order_by(Ticket.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    items = list(db.scalars(stmt).all())
    return TicketListOut(items=items, total=total)


@router.get("/stats")
def get_stats(
    user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    new_count = db.scalar(
        select(func.count()).select_from(Ticket).where(Ticket.status == TicketStatus.new)
    ) or 0

    in_progress_count = db.scalar(
        select(func.count()).select_from(Ticket).where(Ticket.status == TicketStatus.in_progress)
    ) or 0

    done_today_count = db.scalar(
        select(func.count())
        .select_from(Ticket)
        .where(
            Ticket.status == TicketStatus.done,
            Ticket.closed_at >= today_start,
        )
    ) or 0

    active_brigades_count = db.scalar(
        select(func.count(func.distinct(Ticket.brigade_id)))
        .where(
            Ticket.status.in_([TicketStatus.in_progress, TicketStatus.assigned]),
            Ticket.brigade_id.isnot(None),
        )
    ) or 0

    return {
        "new": new_count,
        "in_progress": in_progress_count,
        "done_today": done_today_count,
        "brigades_active": active_brigades_count,
    }


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(
    ticket_id: int,
    user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = _load_ticket_with_relations(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return ticket


@router.post("/{ticket_id}/close", response_model=TicketOut)
def close_ticket(
    ticket_id: int,
    payload: TicketCloseIn,
    user: Employee = Depends(BRIGADE_ROLES),
    db: Session = Depends(get_db),
):
    try:
        return ticket_service.close_ticket(db, ticket_id, payload)
    except ticket_service.TicketNotFound:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    except ticket_service.TicketAlreadyClosed:
        raise HTTPException(status_code=409, detail="Заявка уже закрыта")
    except ticket_service.TicketCancelled:
        raise HTTPException(status_code=409, detail="Заявка отменена и не может быть закрыта")
    except ticket_service.BrigadeNotAssigned:
        raise HTTPException(
            status_code=409,
            detail="Для списания кабеля заявке должна быть назначена бригада",
        )
    except ticket_service.WorkTypeNotFound:
        raise HTTPException(status_code=404, detail="Вид работ не найден")
    except ticket_service.DispatcherNotFound:
        raise HTTPException(status_code=404, detail="Диспетчер не найден")
    except ticket_service.CableEquipmentNotFound:
        raise HTTPException(
            status_code=404,
            detail="Номенклатура оптического кабеля не найдена",
        )
    except ticket_service.CableEquipmentInvalid:
        raise HTTPException(
            status_code=422,
            detail="Переданная номенклатура не является оптическим кабелем в метрах",
        )
    except ticket_service.CableNotIssuedToBrigade:
        raise HTTPException(
            status_code=409,
            detail="Указанный кабель не числится за бригадой",
        )
    except ticket_service.InsufficientCableStock:
        raise HTTPException(
            status_code=409,
            detail="Недостаточно кабеля в инвентаре бригады",
        )


@router.get("/{ticket_id}/act/pdf", response_class=Response)
def download_completion_act(
    ticket_id: int,
    user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = _load_ticket_with_relations(db, ticket_id)

    if ticket is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if ticket.status != TicketStatus.done:
        raise HTTPException(
            status_code=409,
            detail="Акт доступен только для закрытой заявки",
        )

    pdf_bytes = generate_completion_act(ticket)
    filename = f"act_{ticket.number}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )

class TicketCreateIn(BaseModel):
    client_id: int
    address_id: int
    brigade_id: int | None = None
    work_type_id: int | None = None
    description: str | None = Field(default=None, max_length=2000)
    priority: TicketPriority = TicketPriority.normal


@router.post("", response_model=TicketOut, status_code=201)
def create_ticket(
    payload: TicketCreateIn,
    user: Employee = Depends(DISPATCH_ROLES),
    db: Session = Depends(get_db),
):
    from app.models import Ticket as TicketModel

    ticket = TicketModel(
        client_id=payload.client_id,
        address_id=payload.address_id,
        brigade_id=payload.brigade_id,
        work_type_id=payload.work_type_id,
        description=payload.description,
        priority=payload.priority,
        status=TicketStatus.assigned if payload.brigade_id else TicketStatus.new,
    )
    db.add(ticket)
    db.commit()

    return _load_ticket_with_relations(db, ticket.id)


@router.get("/{ticket_id}/detail")
def get_ticket_detail(
    ticket_id: int,
    user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models import IncidentDiagnostic, TicketComment

    ticket = _load_ticket_with_relations(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    comments_stmt = (
        select(TicketComment)
        .where(TicketComment.ticket_id == ticket_id)
        .order_by(TicketComment.created_at)
    )
    comments = list(db.scalars(comments_stmt).all())

    diagnostic = db.scalar(
        select(IncidentDiagnostic).where(IncidentDiagnostic.ticket_id == ticket_id)
    )

    return {
        "id": ticket.id,
        "number": ticket.number,
        "status": ticket.status.value,
        "priority": ticket.priority.value,
        "description": ticket.description,
        "client": {
            "full_name": ticket.client.full_name,
            "phone": ticket.client.phone,
            "organization": ticket.client.organization.name if ticket.client.organization else None,
        },
        "address": ticket.address.full_address,
        "brigade": ticket.brigade.name if ticket.brigade else None,
        "work_type": ticket.work_type.name if ticket.work_type else None,
        "cable_used_meters": str(ticket.cable_used_meters),
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
        "comments": [
            {
                "id": c.id,
                "body": c.body,
                "author": c.employee.full_name if c.employee else "Диспетчер",
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in comments
        ],
        "diagnostic": (
            {
                "fault_party": diagnostic.fault_party.value,
                "cause_description": diagnostic.cause_description,
            }
            if diagnostic
            else None
        ),
    }
class TicketAssignIn(BaseModel):
    brigade_id: int


@router.post("/{ticket_id}/assign", response_model=TicketOut)
def assign_ticket(
    ticket_id: int,
    payload: TicketAssignIn,
    user: Employee = Depends(DISPATCH_ROLES),
    db: Session = Depends(get_db),
):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    if ticket.status not in (TicketStatus.new, TicketStatus.assigned):
        raise HTTPException(status_code=409, detail="Нельзя назначить бригаду на эту заявку")
    ticket.brigade_id = payload.brigade_id
    ticket.status = TicketStatus.assigned
    db.commit()
    return _load_ticket_with_relations(db, ticket_id)


@router.post("/{ticket_id}/accept", response_model=TicketOut)
def accept_ticket_route(
    ticket_id: int,
    user: Employee = Depends(BRIGADE_ROLES),
    db: Session = Depends(get_db),
):
    try:
        return ticket_service.accept_ticket(db, ticket_id)
    except ticket_service.TicketNotFound:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    except ticket_service.InvalidStatusTransition:
        raise HTTPException(status_code=409, detail="Принять можно только назначенную заявку")

from datetime import datetime, timedelta, timezone


@router.get("/stats/chart")
def get_chart_stats(
    user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Статистика заявок за последние 7 дней + распределение по статусам."""
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=6)

    # Заявки по дням
    stmt = (
        select(
            func.date(Ticket.created_at).label("day"),
            func.count().label("count"),
        )
        .where(Ticket.created_at >= seven_days_ago)
        .group_by(func.date(Ticket.created_at))
        .order_by(func.date(Ticket.created_at))
    )
    rows = db.execute(stmt).all()

    # Заполняем все 7 дней (даже без заявок)
    daily = {}
    for i in range(7):
        d = (now - timedelta(days=6 - i)).strftime("%Y-%m-%d")
        daily[d] = 0
    for row in rows:
        day_str = str(row.day)
        if day_str in daily:
            daily[day_str] = row.count

    labels = list(daily.keys())
    values = list(daily.values())

    # Распределение по статусам
    status_stmt = (
        select(Ticket.status, func.count())
        .group_by(Ticket.status)
    )
    status_rows = db.execute(status_stmt).all()

    status_labels = {
        "new": "Новые",
        "assigned": "Назначены",
        "in_progress": "В работе",
        "done": "Выполнены",
        "cancelled": "Отменены",
    }

    pie_labels = []
    pie_values = []
    for status, count in status_rows:
        pie_labels.append(status_labels.get(status.value, status.value))
        pie_values.append(count)

    return {
        "daily": {"labels": labels, "values": values},
        "by_status": {"labels": pie_labels, "values": pie_values},
    }
