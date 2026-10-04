from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Address, Brigade, Client, Employee, EquipmentCatalog, EmployeeRole, Organization, WorkType
from app.security import get_current_user, require_roles

router = APIRouter(prefix="/refs", tags=["refs"])

# Справочники читают все авторизованные сотрудники,
# создание клиента с адресом выполняет диспетчер или администратор.
CLIENT_RECORD_ROLES = require_roles(
    EmployeeRole.dispatcher.value, EmployeeRole.admin.value
)


@router.get("/clients")
def list_clients(
    user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models import Ticket
    
    stmt = (
        select(Client)
        .options(selectinload(Client.organization))
        .order_by(Client.last_name, Client.first_name)
    )
    clients = list(db.scalars(stmt).all())

    result = []
    for c in clients:
        last_address_stmt = (
            select(Address)
            .join(Ticket, Ticket.address_id == Address.id)
            .where(Ticket.client_id == c.id)
            .order_by(Ticket.created_at.desc())
            .limit(1)
        )
        last_address = db.scalar(last_address_stmt)

        result.append({
            "id": c.id,
            "full_name": c.full_name,
            "phone": c.phone,
            "organization": c.organization.name if c.organization else None,
            "last_address": last_address.full_address if last_address else None,
            "last_address_id": last_address.id if last_address else None,
        })

    return result


@router.get("/addresses")
def list_addresses(
    user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Address).order_by(Address.street, Address.house)
    addresses = list(db.scalars(stmt).all())
    return [
        {"id": a.id, "full_address": a.full_address}
        for a in addresses
    ]


@router.get("/brigades")
def list_brigades(
    user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Brigade).order_by(Brigade.name)
    brigades = list(db.scalars(stmt).all())
    return [{"id": b.id, "name": b.name} for b in brigades]


@router.get("/work-types")
def list_work_types(
    user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(WorkType).order_by(WorkType.name)
    work_types = list(db.scalars(stmt).all())
    return [
        {
            "id": w.id,
            "name": w.name,
            "requires_optical_cable": w.requires_optical_cable,
        }
        for w in work_types
    ]


@router.get("/cables")
def list_cables(
    user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(EquipmentCatalog).where(
        EquipmentCatalog.unit == "м"
    ).order_by(EquipmentCatalog.name)
    cables = list(db.scalars(stmt).all())
    return [{"id": c.id, "name": c.name} for c in cables]


from pydantic import BaseModel, Field


class AddressCreateIn(BaseModel):
    city: str | None = None
    street: str = Field(..., min_length=2, max_length=150)
    house: str = Field(..., min_length=1, max_length=20)
    building: str | None = None
    entrance: str | None = None
    apartment: str | None = None
    comment: str | None = None


class ClientCreateIn(BaseModel):
    last_name: str = Field(..., min_length=2, max_length=100)
    first_name: str = Field(..., min_length=2, max_length=100)
    middle_name: str | None = None
    phone: str | None = None
    email: str | None = None
    organization_id: int | None = None
    address: AddressCreateIn


@router.post("/clients", status_code=201)
def create_client(
    payload: ClientCreateIn,
    user: Employee = Depends(CLIENT_RECORD_ROLES),
    db: Session = Depends(get_db),
):
    address = Address(
        city=payload.address.city,
        street=payload.address.street,
        house=payload.address.house,
        building=payload.address.building,
        entrance=payload.address.entrance,
        apartment=payload.address.apartment,
        comment=payload.address.comment,
    )
    db.add(address)
    db.flush()  

    client = Client(
        last_name=payload.last_name,
        first_name=payload.first_name,
        middle_name=payload.middle_name,
        phone=payload.phone,
        email=payload.email,
        organization_id=payload.organization_id,
    )
    db.add(client)
    db.commit()

    return {
        "id": client.id,
        "full_name": client.full_name,
        "phone": client.phone,
        "organization": None,
        "last_address": address.full_address,
        "last_address_id": address.id,
    }

@router.get("/employees")
def list_employees(
    user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Employee).where(Employee.is_active == True).order_by(Employee.last_name)
    employees = list(db.scalars(stmt).all())
    return [{"id": e.id, "full_name": e.full_name, "role": e.role.value} for e in employees]
