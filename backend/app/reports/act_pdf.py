from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models import Ticket, TicketStatus


_FONT_NAME = "CyrFont"
_FONT_BOLD_NAME = "CyrFont-Bold"
_fonts_ready = False


def _find_regular_font() -> Path | None:
    candidates = [
        Path(__file__).resolve().parent.parent / "fonts" / "DejaVuSans.ttf",
        Path("app/fonts/DejaVuSans.ttf"),
        Path("fonts/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]

    for path in candidates:
        if path.exists():
            return path

    return None


def _find_bold_font(regular_path: Path) -> Path | None:
    candidates = [
        regular_path.parent / "DejaVuSans-Bold.ttf",
        Path("app/fonts/DejaVuSans-Bold.ttf"),
        Path("fonts/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
        Path("C:/Windows/Fonts/DejaVuSans-Bold.ttf"),
    ]

    if regular_path.name.lower() == "arial.ttf":
        candidates.append(Path("C:/Windows/Fonts/arialbd.ttf"))

    for path in candidates:
        if path.exists():
            return path

    return None


def _ensure_fonts() -> None:
    global _fonts_ready, _FONT_BOLD_NAME

    if _fonts_ready:
        return

    regular = _find_regular_font()

    if regular is None:
        raise RuntimeError(
            "Не найден шрифт с поддержкой кириллицы. "
            "Положите DejaVuSans.ttf в app/fonts/ или установите шрифты DejaVu в системе."
        )

    pdfmetrics.registerFont(TTFont(_FONT_NAME, str(regular)))

    bold = _find_bold_font(regular)

    if bold is not None:
        pdfmetrics.registerFont(TTFont(_FONT_BOLD_NAME, str(bold)))
    else:
        _FONT_BOLD_NAME = _FONT_NAME

    pdfmetrics.registerFontFamily(
        _FONT_NAME,
        normal=_FONT_NAME,
        bold=_FONT_BOLD_NAME,
        italic=_FONT_NAME,
        boldItalic=_FONT_BOLD_NAME,
    )

    _fonts_ready = True


def _escape(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _format_datetime(value) -> str:
    if value is None:
        return "—"
    return value.strftime("%d.%m.%Y %H:%M")


def _format_decimal(value: Decimal | None) -> str:
    if value is None:
        value = Decimal("0")
    return format(value, ".3f")


def generate_completion_act(
    ticket: Ticket,
    output_path: str | Path | None = None,
) -> bytes:
    if ticket.status != TicketStatus.done:
        raise ValueError("Акт можно генерировать только для закрытой заявки")

    _ensure_fonts()

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title="Акт выполненных работ",
        author="ISP ERP System",
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()

    base_style = ParagraphStyle(
        "ActBase",
        parent=styles["Normal"],
        fontName=_FONT_NAME,
        fontSize=11,
        leading=14,
    )

    label_style = ParagraphStyle(
        "ActLabel",
        parent=base_style,
        fontName=_FONT_BOLD_NAME,
    )

    title_style = ParagraphStyle(
        "ActTitle",
        parent=styles["Title"],
        fontName=_FONT_BOLD_NAME,
        fontSize=16,
        leading=20,
        spaceAfter=8,
    )

    subtitle_style = ParagraphStyle(
        "ActSubtitle",
        parent=base_style,
        fontName=_FONT_BOLD_NAME,
        fontSize=12,
        spaceAfter=18,
    )

    elements = []

    elements.append(Paragraph("АКТ выполненных работ", title_style))
    elements.append(
        Paragraph(f"к заявке № {_escape(ticket.number)}", subtitle_style)
    )

    client_name = ticket.client.full_name if ticket.client else "—"

    if ticket.client and ticket.client.organization:
        client_name = f"{client_name} / {ticket.client.organization.name}"

    address = ticket.address.full_address if ticket.address else "—"
    work_type = ticket.work_type.name if ticket.work_type else "—"
    brigade = ticket.brigade.name if ticket.brigade else "—"
    cable_name = (
        ticket.cable_equipment.name
        if ticket.cable_equipment
        else "Оптический кабель"
    )

    rows = [
        ("Номер заявки", ticket.number),
        ("Дата закрытия", _format_datetime(ticket.closed_at or ticket.completed_at)),
        ("ФИО клиента", client_name),
        ("Адрес выполнения", address),
        ("Вид работы", work_type),
        ("Бригада", brigade),
        ("Материал", cable_name),
        ("Использовано кабеля, м", _format_decimal(ticket.cable_used_meters)),
    ]

    table_data = [
        [
            Paragraph(_escape(label), label_style),
            Paragraph(_escape(value), base_style),
        ]
        for label, value in rows
    ]

    info_table = Table(
        table_data,
        colWidths=[5.5 * cm, 11.5 * cm],
    )

    info_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f2f2f2")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    elements.append(info_table)
    elements.append(Spacer(1, 1.2 * cm))

    elements.append(
        Paragraph(
            "Работы выполнены в соответствии с заявкой. "
            "Заказчик претензий по объему и качеству выполненных работ не имеет.",
            base_style,
        )
    )

    elements.append(Spacer(1, 2.0 * cm))

    signature_data = [
        [
            "Исполнитель",
            "____________________",
            "Заказчик",
            "____________________",
        ]
    ]

    signature_table = Table(
        signature_data,
        colWidths=[2.5 * cm, 6 * cm, 2.5 * cm, 6 * cm],
    )

    signature_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 0), (1, 0), "CENTER"),
                ("ALIGN", (3, 0), (3, 0), "CENTER"),
            ]
        )
    )

    elements.append(signature_table)

    doc.build(elements)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(pdf_bytes)

    return pdf_bytes