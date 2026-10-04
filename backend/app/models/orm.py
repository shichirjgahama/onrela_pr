from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from .enums import (
    EmployeeRole,
    EquipmentCategory,
    FaultParty,
    ServiceType,
    TicketPriority,
    TicketStatus,
    Unit,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[Optional[str]] = mapped_column(String(100))
    role: Mapped[EmployeeRole] = mapped_column(
        SAEnum(EmployeeRole, native_enum=False, length=30),
        default=EmployeeRole.engineer,
        nullable=False,
    )
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    memberships: Mapped[list["BrigadeMember"]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    comments: Mapped[list["TicketComment"]] = relationship(back_populates="employee")
    key_logs: Mapped[list["KeyLog"]] = relationship(back_populates="employee")

    @property
    def full_name(self) -> str:
        return " ".join(
            part
            for part in [self.last_name, self.first_name, self.middle_name]
            if part
        )


class Brigade(Base):
    __tablename__ = "brigades"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    lead_employee_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    lead_employee: Mapped[Optional["Employee"]] = relationship(
        foreign_keys=[lead_employee_id]
    )
    members: Mapped[list["BrigadeMember"]] = relationship(
        back_populates="brigade",
        cascade="all, delete-orphan",
    )
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="brigade")
    inventory: Mapped[list["BrigadeInventory"]] = relationship(
        back_populates="brigade",
        cascade="all, delete-orphan",
    )
    key_logs: Mapped[list["KeyLog"]] = relationship(back_populates="brigade")


class BrigadeMember(Base):
    """
    Many-to-many состав бригад.
    Используется association object, чтобы можно было хранить роль в бригаде и дату назначения.
    """

    __tablename__ = "brigade_members"

    brigade_id: Mapped[int] = mapped_column(
        ForeignKey("brigades.id", ondelete="CASCADE"),
        primary_key=True,
    )
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_in_brigade: Mapped[Optional[str]] = mapped_column(String(50))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    brigade: Mapped["Brigade"] = relationship(back_populates="members")
    employee: Mapped["Employee"] = relationship(back_populates="memberships")


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    inn: Mapped[str] = mapped_column(String(12), unique=True, index=True, nullable=False)
    kpp: Mapped[Optional[str]] = mapped_column(String(9))
    legal_address: Mapped[Optional[str]] = mapped_column(String(255))
    contact_name: Mapped[Optional[str]] = mapped_column(String(200))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    clients: Mapped[list["Client"]] = relationship(back_populates="organization")


class Client(Base):
    """
    Физлицо или представитель юрлица.
    Если клиент представляет организацию, organization_id заполняется.
    """

    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL")
    )
    tariff_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tariffs_and_services.id", ondelete="SET NULL")
    )

    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[Optional[str]] = mapped_column(String(100))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    email: Mapped[Optional[str]] = mapped_column(String(100))
    note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    organization: Mapped[Optional["Organization"]] = relationship(back_populates="clients")
    tariff: Mapped[Optional["TariffAndService"]] = relationship(back_populates="clients")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="client")

    @property
    def full_name(self) -> str:
        return " ".join(
            part
            for part in [self.last_name, self.first_name, self.middle_name]
            if part
        )


class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    street: Mapped[str] = mapped_column(String(150), nullable=False)
    house: Mapped[str] = mapped_column(String(20), nullable=False)
    building: Mapped[Optional[str]] = mapped_column(String(20))
    entrance: Mapped[Optional[str]] = mapped_column(String(20))
    apartment: Mapped[Optional[str]] = mapped_column(String(20))
    comment: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    tickets: Mapped[list["Ticket"]] = relationship(back_populates="address")
    key_logs: Mapped[list["KeyLog"]] = relationship(back_populates="address")

    @property
    def full_address(self) -> str:
        parts: list[str] = []

        if self.city:
            parts.append(f"г. {self.city}")
        if self.street:
            parts.append(f"ул. {self.street}")
        if self.house:
            parts.append(f"д. {self.house}")
        if self.building:
            parts.append(f"корп. {self.building}")
        if self.entrance:
            parts.append(f"подъезд {self.entrance}")
        if self.apartment:
            parts.append(f"кв. {self.apartment}")

        return ", ".join(parts) if parts else "Адрес не указан"


class TariffAndService(Base):
    __tablename__ = "tariffs_and_services"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    service_type: Mapped[ServiceType] = mapped_column(
        SAEnum(ServiceType, native_enum=False, length=30),
        nullable=False,
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    clients: Mapped[list["Client"]] = relationship(back_populates="tariff")


class EquipmentCatalog(Base):
    __tablename__ = "equipment_catalog"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[EquipmentCategory] = mapped_column(
        SAEnum(EquipmentCategory, native_enum=False, length=30),
        nullable=False,
    )
    unit: Mapped[Unit] = mapped_column(
        SAEnum(Unit, native_enum=False, length=10),
        default=Unit.piece,
        nullable=False,
    )
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    is_serial_required: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    warehouse_stock: Mapped[Optional["WarehouseStock"]] = relationship(
        back_populates="equipment",
        uselist=False,
        cascade="all, delete-orphan",
    )
    brigade_positions: Mapped[list["BrigadeInventory"]] = relationship(
        back_populates="equipment"
    )


class WarehouseStock(Base):
    """
    Остатки на центральном складе.
    Одна строка на одну номенклатуру.
    """

    __tablename__ = "warehouse_stock"

    id: Mapped[int] = mapped_column(primary_key=True)
    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("equipment_catalog.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        default=Decimal("0"),
        nullable=False,
    )
    min_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        default=Decimal("0"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )

    equipment: Mapped["EquipmentCatalog"] = relationship(back_populates="warehouse_stock")

    __table_args__ = (
        CheckConstraint("quantity >= 0"),
        CheckConstraint("min_quantity >= 0"),
    )


class BrigadeInventory(Base):
    """
    Инвентарь, выданный бригаде.
    Для кабеля количество хранится в метрах.
    """

    __tablename__ = "brigade_inventory"

    id: Mapped[int] = mapped_column(primary_key=True)
    brigade_id: Mapped[int] = mapped_column(
        ForeignKey("brigades.id", ondelete="CASCADE"),
        nullable=False,
    )
    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("equipment_catalog.id", ondelete="CASCADE"),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        default=Decimal("0"),
        nullable=False,
    )
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )
    note: Mapped[Optional[str]] = mapped_column(Text)

    brigade: Mapped["Brigade"] = relationship(back_populates="inventory")
    equipment: Mapped["EquipmentCatalog"] = relationship(back_populates="brigade_positions")

    __table_args__ = (
        UniqueConstraint("brigade_id", "equipment_id", name="uq_brigade_inventory_equipment"),
        CheckConstraint("quantity >= 0"),
    )


class KeyLog(Base):
    """
    Журнал выдачи ключей, например от чердаков и щитовых.
    """

    __tablename__ = "key_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    key_name: Mapped[str] = mapped_column(String(200), nullable=False)
    address_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("addresses.id", ondelete="SET NULL")
    )
    brigade_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("brigades.id", ondelete="SET NULL")
    )
    employee_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL")
    )
    purpose: Mapped[Optional[str]] = mapped_column(String(255))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    returned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    note: Mapped[Optional[str]] = mapped_column(Text)

    address: Mapped[Optional["Address"]] = relationship(back_populates="key_logs")
    brigade: Mapped[Optional["Brigade"]] = relationship(back_populates="key_logs")
    employee: Mapped[Optional["Employee"]] = relationship(back_populates="key_logs")


class WorkType(Base):
    __tablename__ = "work_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    default_duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    requires_optical_cable: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    tickets: Mapped[list["Ticket"]] = relationship(back_populates="work_type")


class Ticket(Base):
    """
    Заявка на выезд/ремонт.

    Важные связи:
    - client: клиент/представитель юрлица;
    - address: адрес выполнения;
    - brigade: назначенная бригада;
    - work_type: тип работы;
    - cable_equipment: конкретный кабель, если он списывается.
    """

    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        default=lambda: f"TK-{uuid4().hex[:8].upper()}",
        nullable=False,
    )

    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    address_id: Mapped[int] = mapped_column(
        ForeignKey("addresses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    brigade_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("brigades.id", ondelete="SET NULL")
    )
    work_type_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("work_types.id", ondelete="SET NULL")
    )
    cable_equipment_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("equipment_catalog.id", ondelete="SET NULL")
    )

    status: Mapped[TicketStatus] = mapped_column(
        SAEnum(TicketStatus, native_enum=False, length=20),
        default=TicketStatus.new,
        index=True,
        nullable=False,
    )
    priority: Mapped[TicketPriority] = mapped_column(
        SAEnum(TicketPriority, native_enum=False, length=20),
        default=TicketPriority.normal,
        nullable=False,
    )

    description: Mapped[Optional[str]] = mapped_column(Text)

    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    cable_used_meters: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        default=Decimal("0"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )

    client: Mapped["Client"] = relationship(back_populates="tickets")
    address: Mapped["Address"] = relationship(back_populates="tickets")
    brigade: Mapped[Optional["Brigade"]] = relationship(back_populates="tickets")
    work_type: Mapped[Optional["WorkType"]] = relationship(back_populates="tickets")
    cable_equipment: Mapped[Optional["EquipmentCatalog"]] = relationship()

    comments: Mapped[list["TicketComment"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketComment.created_at",
    )
    diagnostic: Mapped[Optional["IncidentDiagnostic"]] = relationship(
        back_populates="ticket",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("cable_used_meters >= 0"),
        Index("ix_tickets_status_brigade", "status", "brigade_id"),
    )


class TicketComment(Base):
    __tablename__ = "ticket_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
    )
    employee_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL")
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    ticket: Mapped["Ticket"] = relationship(back_populates="comments")
    employee: Mapped[Optional["Employee"]] = relationship(back_populates="comments")


class IncidentDiagnostic(Base):
    """
    Результат диагностики/ремонта: чья вина, причина и т.п.
    Одна запись на заявку.
    """

    __tablename__ = "incident_diagnostics"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    fault_party: Mapped[FaultParty] = mapped_column(
        SAEnum(FaultParty, native_enum=False, length=30),
        default=FaultParty.unknown,
        nullable=False,
    )
    cause_code: Mapped[Optional[str]] = mapped_column(String(30))
    cause_description: Mapped[Optional[str]] = mapped_column(Text)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    ticket: Mapped["Ticket"] = relationship(back_populates="diagnostic")