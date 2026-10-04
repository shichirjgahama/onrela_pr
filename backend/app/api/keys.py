from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Employee, EmployeeRole, KeyLog
from app.security import get_current_user, require_roles

router = APIRouter(prefix="/keys", tags=["keys"])

# Журнал ключей читают все; выдачу/возврат/переименование выполняет диспетчер и администратор.
KEY_RECORD_ROLES = require_roles(
    EmployeeRole.dispatcher.value, EmployeeRole.admin.value
)


class KeyIssueIn(BaseModel):
    key_name: str = Field(..., min_length=2, max_length=200)
    address_id: int | None = None
    brigade_id: int | None = None
    employee_id: int | None = None
    purpose: str | None = None
    note: str | None = None
    to_storage: bool = False


class KeyEditIn(BaseModel):
    old_name: str
    new_name: str = Field(..., min_length=2, max_length=200)
    address_id: int | None = None


@router.get("")
def list_keys(
    user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(KeyLog)
        .options(
            selectinload(KeyLog.address),
            selectinload(KeyLog.brigade),
            selectinload(KeyLog.employee),
        )
        .order_by(KeyLog.issued_at.desc())
    )
    logs = list(db.scalars(stmt).all())

    return [
        {
            "id": k.id,
            "key_name": k.key_name,
            "address": k.address.full_address if k.address else None,
            "address_id": k.address_id,
            "brigade": k.brigade.name if k.brigade else None,
            "employee": k.employee.full_name if k.employee else None,
            "purpose": k.purpose,
            "issued_at": k.issued_at.isoformat() if k.issued_at else None,
            "returned_at": k.returned_at.isoformat() if k.returned_at else None,
            "is_issued": k.returned_at is None,
        }
        for k in logs
    ]


@router.post("", status_code=201)
def issue_key(
    payload: KeyIssueIn,
    user: Employee = Depends(KEY_RECORD_ROLES),
    db: Session = Depends(get_db),
):
    log = KeyLog(
        key_name=payload.key_name,
        address_id=payload.address_id,
        brigade_id=None if payload.to_storage else payload.brigade_id,
        employee_id=None if payload.to_storage else payload.employee_id,
        purpose=payload.purpose,
        note=payload.note,
    )
    if payload.to_storage:
        log.returned_at = datetime.now(timezone.utc)
    db.add(log)
    db.commit()
    return {"id": log.id}


@router.put("/edit")
def edit_key(
    payload: KeyEditIn,
    user: Employee = Depends(KEY_RECORD_ROLES),
    db: Session = Depends(get_db),
):
    if payload.old_name != payload.new_name:
        db.execute(
            update(KeyLog)
            .where(KeyLog.key_name == payload.old_name)
            .values(key_name=payload.new_name)
        )
    db.execute(
        update(KeyLog)
        .where(KeyLog.key_name == payload.new_name)
        .values(address_id=payload.address_id)
    )
    db.commit()
    return {"ok": True}


@router.post("/{key_id}/return")
def return_key(
    key_id: int,
    user: Employee = Depends(KEY_RECORD_ROLES),
    db: Session = Depends(get_db),
):
    log = db.get(KeyLog, key_id)
    if log is None:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    if log.returned_at is not None:
        raise HTTPException(status_code=409, detail="Ключ уже возвращён")
    log.returned_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": log.id}
