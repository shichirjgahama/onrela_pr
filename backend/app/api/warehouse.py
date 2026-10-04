from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import (
    Employee,
    EmployeeRole,
    EquipmentCatalog,
    EquipmentCategory,
    Unit,
    WarehouseStock,
)
from app.security import get_current_user, require_roles

router = APIRouter(prefix="/warehouse", tags=["warehouse"])

# Остатки склада видят все сотрудники, а номенклатуру заводит кладовщик и администратор.
WAREHOUSE_ROLES = require_roles(
    EmployeeRole.warehouse_manager.value, EmployeeRole.admin.value
)


class EquipmentCreateIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    category: EquipmentCategory
    unit: Unit
    initial_quantity: float = Field(default=0, ge=0)
    min_quantity: float = Field(default=0, ge=0)


def _generate_sku(category: EquipmentCategory) -> str:
    prefix = {
        EquipmentCategory.router: "RTR",
        EquipmentCategory.switch: "SW",
        EquipmentCategory.optical_cable: "OPT",
        EquipmentCategory.utp_cable: "UTP",
        EquipmentCategory.tool: "TLS",
        EquipmentCategory.consumable: "CON",
    }[category]
    return f"{prefix}-{uuid4().hex[:6].upper()}"


@router.get("")
def list_warehouse(
    user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(WarehouseStock)
        .options(selectinload(WarehouseStock.equipment))
        .order_by(WarehouseStock.equipment_id)
    )
    items = list(db.scalars(stmt).all())

    return [
        {
            "id": item.id,
            "name": item.equipment.name,
            "category": item.equipment.category.value,
            "quantity": str(item.quantity),
            "min_quantity": str(item.min_quantity),
            "unit": item.equipment.unit.value,
            "is_low": item.quantity <= item.min_quantity,
        }
        for item in items
    ]


@router.post("", status_code=201)
def create_equipment(
    payload: EquipmentCreateIn,
    user: Employee = Depends(WAREHOUSE_ROLES),
    db: Session = Depends(get_db),
):
    existing = db.scalar(
        select(EquipmentCatalog).where(EquipmentCatalog.name == payload.name)
    )
    if existing:
        raise HTTPException(status_code=409, detail="Такая позиция уже существует")

    equipment = EquipmentCatalog(
        sku=_generate_sku(payload.category),
        name=payload.name,
        category=payload.category,
        unit=payload.unit,
    )
    db.add(equipment)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Не удалось добавить позицию: нарушено ограничение уникальности",
        ) from exc

    stock = WarehouseStock(
        equipment_id=equipment.id,
        quantity=payload.initial_quantity,
        min_quantity=payload.min_quantity,
    )
    db.add(stock)
    db.commit()

    return {
        "id": equipment.id,
        "sku": equipment.sku,
        "name": equipment.name,
        "category": equipment.category.value,
        "unit": equipment.unit.value,
        "quantity": str(stock.quantity),
        "min_quantity": str(stock.min_quantity),
        "is_low": stock.quantity <= stock.min_quantity,
    }
