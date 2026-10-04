from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import FaultParty, TicketStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ClientOut(ORMModel):
    id: int
    full_name: str
    phone: Optional[str] = None
    organization_id: Optional[int] = None


class AddressOut(ORMModel):
    id: int
    full_address: str


class WorkTypeOut(ORMModel):
    id: int
    name: str


class BrigadeOut(ORMModel):
    id: int
    name: str


class TicketOut(ORMModel):
    id: int
    number: str
    status: TicketStatus
    client: ClientOut
    address: AddressOut
    work_type: Optional[WorkTypeOut] = None
    brigade: Optional[BrigadeOut] = None
    cable_used_meters: Decimal = Decimal("0")
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


class TicketCloseIn(BaseModel):
    work_type_id: Optional[int] = None

    cable_equipment_id: Optional[int] = None

    cable_used_meters: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))

    dispatcher_employee_id: Optional[int] = None
    dispatcher_comment: Optional[str] = Field(default=None, max_length=2000)

    fault_party: Optional[FaultParty] = None
    cause_description: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("cable_used_meters", mode="after")
    @classmethod
    def quantize_cable(cls, value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.001"))


class TicketListOut(BaseModel):
    items: list[TicketOut]
    total: int