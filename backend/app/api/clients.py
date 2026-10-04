from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Client, Employee
from app.security import get_current_user

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("")
def list_clients(
    user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Client)
        .options(
            selectinload(Client.organization),
            selectinload(Client.tariff),
        )
        .order_by(Client.last_name, Client.first_name)
    )
    clients = list(db.scalars(stmt).all())

    return [
        {
            "id": c.id,
            "full_name": c.full_name,
            "phone": c.phone,
            "email": c.email,
            "type": "b2b" if c.organization_id else "b2c",
            "organization": c.organization.name if c.organization else None,
            "inn": c.organization.inn if c.organization else None,
            "tariff": c.tariff.name if c.tariff else None,
        }
        for c in clients
    ]
