"""Наполнение демонстрационными данными.

Скрипт создаёт согласованный учебный набор:
сотрудники всех ролей (с паролями), бригады, клиенты, адреса, тарифы,
номенклатура склада и инвентарь бригад, заявки на разных этапах жизненного
цикла, журнал ключей и диагностика инцидентов.

Запуск из каталога backend:
    python -m scripts.seed_demo
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import (
    Address,
    Brigade,
    BrigadeInventory,
    BrigadeMember,
    Client,
    Employee,
    EmployeeRole,
    EquipmentCatalog,
    EquipmentCategory,
    FaultParty,
    IncidentDiagnostic,
    KeyLog,
    Organization,
    TariffAndService,
    Ticket,
    TicketComment,
    TicketPriority,
    TicketStatus,
    Unit,
    WarehouseStock,
    WorkType,
)
from app.security import hash_password
from app.services import ticket_service
from app.schemas import TicketCloseIn
from app.models import TicketPriority as TP


def _now(hours: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours)


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if db.query(Employee).count() > 0:
        print("База уже содержит данные — сид пропущен.")
        db.close()
        return

    # --- Сотрудники ---
    employees = {
        "admin": Employee(
            username="admin",
            password_hash=hash_password("admin123"),
            last_name="Ковалёв",
            first_name="Андрей",
            middle_name="Сергеевич",
            role=EmployeeRole.admin,
            phone="+79130000001",
        ),
        "dispatcher": Employee(
            username="dispatcher",
            password_hash=hash_password("disp123"),
            last_name="Морозова",
            first_name="Елена",
            middle_name="Игоревна",
            role=EmployeeRole.dispatcher,
            phone="+79130000002",
        ),
        "lead1": Employee(
            username="lead1",
            password_hash=hash_password("lead123"),
            last_name="Сафин",
            first_name="Ринат",
            middle_name="Маратович",
            role=EmployeeRole.brigade_lead,
            phone="+79130000003",
        ),
        "lead2": Employee(
            username="lead2",
            password_hash=hash_password("lead123"),
            last_name="Белова",
            first_name="Ольга",
            middle_name="Викторовна",
            role=EmployeeRole.brigade_lead,
            phone="+79130000004",
        ),
        "eng1": Employee(
            username="engineer1",
            password_hash=hash_password("eng123"),
            last_name="Шабалин",
            first_name="Максим",
            middle_name=None,
            role=EmployeeRole.engineer,
            phone="+79130000005",
        ),
        "eng2": Employee(
            username="engineer2",
            password_hash=hash_password("eng123"),
            last_name="Ким",
            first_name="Дмитрий",
            middle_name="Александрович",
            role=EmployeeRole.engineer,
            phone="+79130000006",
        ),
        "wh": Employee(
            username="warehouse",
            password_hash=hash_password("wh123"),
            last_name="Титова",
            first_name="Наталья",
            middle_name="Павловна",
            role=EmployeeRole.warehouse_manager,
            phone="+79130000007",
        ),
    }
    db.add_all(employees.values())
    db.flush()

    # --- Бригады ---
    brigade1 = Brigade(
        name="Бригада №1",
        description="Монтаж и пусконаладка GPON",
        lead_employee_id=employees["lead1"].id,
    )
    brigade2 = Brigade(
        name="Бригада №2",
        description="Аварийно-восстановительные работы по медным линиям",
        lead_employee_id=employees["lead2"].id,
    )
    db.add_all([brigade1, brigade2])
    db.flush()

    db.add_all(
        [
            BrigadeMember(
                brigade_id=brigade1.id,
                employee_id=employees["lead1"].id,
                role_in_brigade="старший",
            ),
            BrigadeMember(
                brigade_id=brigade1.id,
                employee_id=employees["eng1"].id,
                role_in_brigade="монтажник",
            ),
            BrigadeMember(
                brigade_id=brigade2.id,
                employee_id=employees["lead2"].id,
                role_in_brigade="старший",
            ),
            BrigadeMember(
                brigade_id=brigade2.id,
                employee_id=employees["eng2"].id,
                role_in_brigade="монтажник",
            ),
        ]
    )

    # --- Тарифы и организация ---
    tariff = TariffAndService(
        code="GPON-100",
        name="GPON 100 Мбит/с",
        service_type="gpon",
        price=Decimal("700.00"),
        description="Домашний интернет по оптике",
    )
    tariff2 = TariffAndService(
        code="ETH-500",
        name="Ethernet 500 Мбит/с (FTTB)",
        service_type="internet",
        price=Decimal("550.00"),
        description="Подключение по медной линии",
    )
    org = Organization(
        name='ООО «Сибирский логистик»',
        inn="5405123456",
        kpp="540501001",
        legal_address="г. Новосибирск, ул. Строителей, 12, офис 304",
        contact_name="Гаврилов П. И.",
        phone="+73830000010",
    )
    db.add_all([tariff, tariff2, org])
    db.flush()

    clients = [
        Client(
            organization_id=org.id,
            tariff_id=tariff.id,
            last_name="Гаврилов",
            first_name="Пётр",
            middle_name="Игоревич",
            phone="+79131111101",
            email="gavrilov@example.ru",
            note="Договор №45/24, B2B",
        ),
        Client(
            tariff_id=tariff.id,
            last_name="Петрова",
            first_name="Анна",
            middle_name="Сергеевна",
            phone="+79131111102",
        ),
        Client(
            tariff_id=tariff2.id,
            last_name="Сидоров",
            first_name="Илья",
            middle_name="Николаевич",
            phone="+79131111103",
        ),
        Client(
            last_name="Орлова",
            first_name="Марина",
            middle_name="Владимировна",
            phone="+79131111104",
            note="Новый абонент, подключение 2 линии",
        ),
        Client(
            organization_id=org.id,
            last_name="Тимофеев",
            first_name="Кирилл",
            middle_name="Денисович",
            phone="+79131111105",
            email="office@example.ru",
            note="B2B, видеонаблюдение",
        ),
    ]
    db.add_all(clients)
    db.flush()

    addresses = [
        Address(
            city="Новосибирск",
            street="Сибирская",
            house="58",
            building="4",
            apartment="12",
            comment="Домофон код 55",
        ),
        Address(
            city="Новосибирск",
            street="Лесная",
            house="21",
            apartment="8",
            comment="Квартира 8, подъезд 2",
        ),
        Address(
            city="Новосибирск",
            street="Кирова",
            house="9",
            building="1",
            entrance="3",
            apartment="25",
        ),
        Address(
            city="Новосибирск",
            street="Гагарина",
            house="104",
            building="1",
            entrance="1",
            apartment="37",
            comment="Панельный дом, кв. 37",
        ),
        Address(
            city="Новосибирск",
            street="Строителей",
            house="12",
            building="2",
            entrance="4",
            comment="Офис «Сибирский логистик», 3 этаж",
        ),
    ]
    db.add_all(addresses)
    db.flush()

    # --- Оборудование и склад ---
    cable = EquipmentCatalog(
        sku="OPT-001",
        name="Кабель оптический G.657A1 (1 км)",
        category=EquipmentCategory.optical_cable,
        unit=Unit.meter,
        price=Decimal("25.00"),
        is_serial_required=False,
    )
    utp = EquipmentCatalog(
        sku="UTP-001",
        name="Кабель витая пара Cat5e (метраж)",
        category=EquipmentCategory.utp_cable,
        unit=Unit.meter,
        price=Decimal("6.50"),
    )
    splitter = EquipmentCatalog(
        sku="SPL-16",
        name="Сплиттер 1x16",
        category=EquipmentCategory.consumable,
        unit=Unit.piece,
        price=Decimal("850.00"),
        is_serial_required=True,
    )
    welder = EquipmentCatalog(
        sku="WLD-001",
        name="Сварочный аппарат для волокон",
        category=EquipmentCategory.tool,
        unit=Unit.piece,
        price=Decimal("0.00"),
    )
    switch = EquipmentCatalog(
        sku="SW-24G",
        name="Коммутатор 24 порта Gigabit",
        category=EquipmentCategory.switch,
        unit=Unit.piece,
        price=Decimal("4200.00"),
        is_serial_required=True,
    )
    db.add_all([cable, utp, splitter, welder, switch])
    db.flush()

    db.add_all(
        [
            WarehouseStock(
                equipment_id=cable.id,
                quantity=Decimal("1000.000"),
                min_quantity=Decimal("150.000"),
            ),
            WarehouseStock(
                equipment_id=utp.id,
                quantity=Decimal("480.000"),
                min_quantity=Decimal("100.000"),
            ),
            WarehouseStock(
                equipment_id=splitter.id,
                quantity=Decimal("6"),
                min_quantity=Decimal("10"),
            ),
            WarehouseStock(
                equipment_id=welder.id, quantity=Decimal("2"), min_quantity=Decimal("1")
            ),
            WarehouseStock(
                equipment_id=switch.id,
                quantity=Decimal("4"),
                min_quantity=Decimal("2"),
            ),
        ]
    )

    db.add_all(
        [
            BrigadeInventory(
                brigade_id=brigade1.id,
                equipment_id=cable.id,
                quantity=Decimal("250.000"),
                note="Выдано на барабане",
            ),
            BrigadeInventory(
                brigade_id=brigade1.id,
                equipment_id=splitter.id,
                quantity=Decimal("4"),
                note="На объектах бригады",
            ),
            BrigadeInventory(
                brigade_id=brigade2.id,
                equipment_id=utp.id,
                quantity=Decimal("60.000"),
                note="Витая пара на аварийные работы",
            ),
            BrigadeInventory(
                brigade_id=brigade2.id,
                equipment_id=welder.id,
                quantity=Decimal("1"),
                note="Сварочный аппарат",
            ),
        ]
    )

    # --- Виды работ ---
    work_types = [
        WorkType(
            code="OPT-SPLICE",
            name="Сварка оптического волокна",
            description="Соединение волокна на объекте",
            default_duration_minutes=90,
            requires_optical_cable=True,
        ),
        WorkType(
            code="OPT-LAY",
            name="Прокладка оптического кабеля",
            description="Прокладка магистрали или стояка",
            default_duration_minutes=240,
            requires_optical_cable=True,
        ),
        WorkType(
            code="DEV-SETUP",
            name="Установка и настройка абонентского оборудования",
            description="Модем, ONT, Wi-Fi роутер",
            default_duration_minutes=60,
            requires_optical_cable=False,
        ),
        WorkType(
            code="FAULT-FIX",
            name="Аварийно-восстановительные работы",
            description="Устранение обрыва линии",
            default_duration_minutes=120,
            requires_optical_cable=False,
        ),
    ]
    db.add_all(work_types)
    db.flush()

    # --- Ключи ---
    db.add_all(
        [
            KeyLog(
                key_name="Чердак: Сибирская, 58/4",
                address_id=addresses[0].id,
                brigade_id=brigade1.id,
                employee_id=employees["eng1"].id,
                purpose="Прокладка стояка",
                issued_at=_now(26),
            ),
            KeyLog(
                key_name="Чердак: Лесная, 21",
                address_id=addresses[1].id,
                brigade_id=brigade1.id,
                employee_id=employees["lead1"].id,
                purpose="Аварийные работы",
                issued_at=_now(30),
            ),
            KeyLog(
                key_name="Щитовая: Кирова, 9/1",
                address_id=addresses[2].id,
                brigade_id=None,
                employee_id=None,
                purpose=None,
                issued_at=_now(48),
                returned_at=_now(20),
                note="Возвращена в ключницу",
            ),
        ]
    )

    # --- Заявки ---
    tickets_spec = [
        dict(
            client=clients[3],
            address=addresses[3],
            brigade=brigade1,
            work_type=work_types[1],
            status=TicketStatus.in_progress,
            priority=TicketPriority.emergency,
            description="Новое подключение абонента, прокладка оптики по стояку 1-4 этажи",
            created=_now(5),
        ),
        dict(
            client=clients[0],
            address=addresses[4],
            brigade=brigade1,
            work_type=work_types[0],
            status=TicketStatus.assigned,
            priority=TicketPriority.high,
            description="Ремонт оптической линии между офисом и этажом",
            created=_now(27),
        ),
        dict(
            client=clients[1],
            address=addresses[1],
            brigade=brigade2,
            work_type=work_types[2],
            status=TicketStatus.assigned,
            priority=TicketPriority.normal,
            description="Настройка абонентского модема и Wi-Fi роутера",
            created=_now(28),
        ),
        dict(
            client=clients[2],
            address=addresses[2],
            brigade=None,
            work_type=work_types[3],
            status=TicketStatus.new,
            priority=TicketPriority.high,
            description="Обрыв витой пары в подъезде 3, абонент без интернета",
            created=_now(2),
        ),
        dict(
            client=clients[1],
            address=addresses[1],
            brigade=None,
            work_type=work_types[3],
            status=TicketStatus.new,
            priority=TicketPriority.normal,
            description="Повторное обращение по тому же адресу — нестабильный сигнал",
            created=_now(3),
        ),
        dict(
            client=clients[0],
            address=addresses[4],
            brigade=None,
            work_type=work_types[2],
            status=TicketStatus.new,
            priority=TicketPriority.low,
            description="Запрос на подключение дополнительного IP-адреса",
            created=_now(1),
        ),
        dict(
            client=clients[2],
            address=addresses[2],
            brigade=brigade1,
            work_type=work_types[3],
            status=TicketStatus.in_progress,
            priority=TicketPriority.normal,
            description="Замена повреждённого участка оптической линии в стояке",
            created=_now(50),
        ),
    ]

    tickets: list[Ticket] = []
    for spec in tickets_spec:
        t = Ticket(
            client_id=spec["client"].id,
            address_id=spec["address"].id,
            brigade_id=spec["brigade"].id if spec["brigade"] else None,
            work_type_id=spec["work_type"].id,
            description=spec["description"],
            status=spec["status"],
            priority=spec["priority"],
            created_at=spec["created"],
        )
        if spec["status"] == TicketStatus.in_progress:
            t.started_at = spec["created"] + timedelta(hours=1)
        db.add(t)
        tickets.append(t)
    db.flush()

    # Закрываем заявку через сервис — тем же кодом, что и в production-пути API,
    # чтобы остатки, диагностика и комментарий рассчитывались согласованно.
    # Списывается оптический кабель, числящийся за бригадой №1.
    ticket_service.close_ticket(
        db,
        tickets[6].id,
        TicketCloseIn(
            work_type_id=work_types[3].id,
            cable_equipment_id=cable.id,
            cable_used_meters=Decimal("35.000"),
            dispatcher_comment="Повреждённый участок заменён, сигнал в норме",
            fault_party=FaultParty.provider,
            cause_description="Повреждение оптического кабеля в стояке при монтажных работах",
        ),
    )

    db.add(
        TicketComment(
            ticket_id=tickets[0].id,
            employee_id=employees["dispatcher"].id,
            body="Клиент подтверждает готовность к монтажу, доступ в подъезд 12:00–18:00",
        )
    )
    db.add(
        TicketComment(
            ticket_id=tickets[0].id,
            employee_id=employees["lead1"].id,
            body="Бригада на объекте, идёт протяжка кабеля по стояку",
        )
    )
    # Диагностика для закрытой заявки уже создана сервисом close_ticket.
    diag = db.scalar(
        select(IncidentDiagnostic).where(IncidentDiagnostic.ticket_id == tickets[6].id)
    )
    if diag:
        diag.cause_code = "FAULT-OPT-01"
        diag.cause_description = "Повреждение оптического кабеля в стояке"

    db.commit()
    print("Demo data seeded:")
    for key, emp in employees.items():
        print(f"  {key:10} user={emp.username:10} role={emp.role.value:16}")
    print("  brigades:", brigade1.id, brigade2.id)
    print("  tickets:", [t.id for t in tickets])
    db.close()


if __name__ == "__main__":
    main()