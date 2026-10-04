from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee
from app.security import create_token, get_current_user, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    """Список активных сотрудников для учебного входа."""
    stmt = select(Employee).where(Employee.is_active == True).order_by(Employee.last_name)
    employees = list(db.scalars(stmt).all())
    return [
        {
            "id": e.id,
            "username": e.username,
            "full_name": e.full_name,
            "role": e.role.value,
        }
        for e in employees
    ]


class LoginIn(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=1, max_length=128)


@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    """Проверка логина и пароля, выдача подписанного токена."""
    stmt = select(Employee).where(Employee.username == payload.username)
    employee = db.scalar(stmt)
    if employee is None or not verify_password(payload.password, employee.password_hash):
        # Одинаковый ответ для несуществующего пользователя и неверного пароля,
        # чтобы не давать возможность перебирать существующие учётные записи.
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    if not employee.is_active:
        raise HTTPException(status_code=403, detail="Учётная запись заблокирована")
    return {
        "access_token": create_token(employee.id, employee.role.value),
        "token_type": "bearer",
        "user": {
            "id": employee.id,
            "username": employee.username,
            "full_name": employee.full_name,
            "role": employee.role.value,
        },
    }


@router.get("/me")
def current_user(user: Employee = Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role.value,
    }