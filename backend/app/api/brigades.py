from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Brigade, BrigadeInventory, Employee, EmployeeRole
from app.security import get_current_user, require_roles

router = APIRouter(prefix="/brigades", tags=["brigades"])

# Состав бригад читают все, создание и расформирование — диспетчер и администратор.
BRIGADE_RECORD_ROLES = require_roles(
    EmployeeRole.dispatcher.value, EmployeeRole.admin.value
)


class BrigadeCreateIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = None
    lead_employee_id: int | None = None


@router.get("")
def list_brigades(
    user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Brigade)
        .options(
            selectinload(Brigade.lead_employee),
            selectinload(Brigade.members),
            selectinload(Brigade.inventory).selectinload(BrigadeInventory.equipment),
        )
        .order_by(Brigade.id)
    )
    brigades = list(db.scalars(stmt).all())

    result = []
    for brigade in brigades:
        result.append({
            "id": brigade.id,
            "name": brigade.name,
            "description": brigade.description,
            "lead_employee": brigade.lead_employee.full_name if brigade.lead_employee else None,
            "members_count": len(brigade.members),
            "inventory": [
                {
                    "id": item.id,
                    "name": item.equipment.name,
                    "category": item.equipment.category.value,
                    "quantity": str(item.quantity),
                    "unit": item.equipment.unit.value,
                }
                for item in brigade.inventory
            ],
        })

    return result


@router.post("", status_code=201)
def create_brigade(
    payload: BrigadeCreateIn,
    user: Employee = Depends(BRIGADE_RECORD_ROLES),
    db: Session = Depends(get_db),
):
    existing = db.scalar(select(Brigade).where(Brigade.name == payload.name))
    if existing:
        raise HTTPException(status_code=409, detail="Бригада с таким названием уже существует")

    brigade = Brigade(
        name=payload.name,
        description=payload.description,
        lead_employee_id=payload.lead_employee_id,
    )
    db.add(brigade)
    db.commit()

    return {
        "id": brigade.id,
        "name": brigade.name,
        "description": brigade.description,
        "lead_employee": None,
        "members_count": 0,
        "inventory": [],
    }

@router.delete("/{brigade_id}")
def disband_brigade(
    brigade_id: int,
    user: Employee = Depends(BRIGADE_RECORD_ROLES),
    db: Session = Depends(get_db),
):
    brigade = db.get(Brigade, brigade_id)
    if brigade is None:
        raise HTTPException(status_code=404, detail="Бригада не найдена")

    from app.models import Ticket, TicketStatus
    active_tickets = db.scalar(
        select(func.count())
        .select_from(Ticket)
        .where(
            Ticket.brigade_id == brigade_id,
            Ticket.status.in_([TicketStatus.assigned, TicketStatus.in_progress]),
        )
    )
    if active_tickets and active_tickets > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Нельзя расформировать: у бригады {active_tickets} активных заявок",
        )

    for item in list(brigade.inventory):
        db.delete(item)

    db.delete(brigade)
    db.commit()
    return {"ok": True}

