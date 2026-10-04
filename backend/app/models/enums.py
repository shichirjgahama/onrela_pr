from enum import Enum


class EmployeeRole(str, Enum):
    admin = "admin"
    dispatcher = "dispatcher"
    engineer = "engineer"
    brigade_lead = "brigade_lead"
    warehouse_manager = "warehouse_manager"


class ServiceType(str, Enum):
    internet = "internet"
    gpon = "gpon"
    video_surveillance = "video_surveillance"
    phone = "phone"


class EquipmentCategory(str, Enum):
    router = "router"
    switch = "switch"
    optical_cable = "optical_cable"
    utp_cable = "utp_cable"
    tool = "tool"
    consumable = "consumable"


class Unit(str, Enum):
    piece = "шт"
    meter = "м"


class TicketStatus(str, Enum):
    new = "new"
    assigned = "assigned"
    in_progress = "in_progress"
    done = "done"
    cancelled = "cancelled"


class TicketPriority(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"
    emergency = "emergency"


class FaultParty(str, Enum):
    client = "client"
    provider = "provider"
    third_party = "third_party"
    weather = "weather"
    unknown = "unknown"