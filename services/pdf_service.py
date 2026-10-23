from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


# ============================================================
# PDF LAYOUT CONFIGURATION
# Change the values below to customize the PDF appearance.
# Do not modify the PDF generation logic below.
# ============================================================

PAGE_MARGIN_LEFT = 18  # mm
PAGE_MARGIN_RIGHT = 18  # mm
PAGE_MARGIN_TOP = 16  # mm
PAGE_MARGIN_BOTTOM = 16  # mm

SPACE_AFTER_HEADER = 7  # mm
SPACE_AFTER_CUSTOMER = 7  # mm
SPACE_AFTER_PROJECT = 4  # mm
SPACE_BEFORE_ITEMS = 5  # mm
SPACE_BEFORE_TERMS = 25  # mm
SPACE_BETWEEN_TERMS = 1  # mm

LOGO_WIDTH = 45  # mm
LOGO_HEIGHT = 45  # mm
LOGO_COLUMN_WIDTH = 48  # mm
COMPANY_COLUMN_WIDTH = 126  # mm
HEADER_ROW_HEIGHT = 27  # mm
LOGO_POSITION = "CENTER"
HEADER_CELL_PADDING = 5
HEADER_TOP_PADDING = 4
HEADER_BOTTOM_PADDING = 4

COMPANY_NAME_FONT = "Helvetica-Bold"
COMPANY_NAME_FONT_SIZE = 18
COMPANY_NAME_COLOR = "#18324B"
COMPANY_NAME_ALIGNMENT = "CENTER"

ADDRESS_FONT = "Helvetica"
ADDRESS_FONT_SIZE = 10
ADDRESS_COLOR = "#000000"
ADDRESS_ALIGNMENT = "CENTER"
ADDRESS_LINE_SPACING = 12

EMAIL_WEBSITE_FONT = "Helvetica"
EMAIL_WEBSITE_FONT_SIZE = 10
EMAIL_WEBSITE_COLOR = "#000000"
EMAIL_WEBSITE_ALIGNMENT = "CENTER"

SECTION_HEADING_FONT = "Helvetica-Bold"
SECTION_HEADING_FONT_SIZE = 9
SECTION_HEADING_COLOR = "#18324B"
SECTION_HEADING_LINE_SPACING = 11

GENERAL_TEXT_FONT = "Helvetica"
GENERAL_TEXT_SIZE = 9
GENERAL_TEXT_COLOR = "#000000"
GENERAL_TEXT_LINE_SPACING = 12
SMALL_TEXT_FONT = "Helvetica"
SMALL_TEXT_SIZE = 8
SMALL_TEXT_COLOR = "#000000"
SMALL_TEXT_LINE_SPACING = 9

TABLE_FONT = "Helvetica"
TABLE_FONT_SIZE = 8
TABLE_HEADER_FONT = "Helvetica-Bold"
TABLE_HEADER_FONT_SIZE = 8
TABLE_HEADER_TEXT_COLOR = "#FFFFFF"
TABLE_HEADER_BACKGROUND = "#18324B"
TABLE_HEADER_ALIGNMENT = "CENTER"
TABLE_HEADER_LINE_SPACING = 10
TABLE_BORDER_COLOR = "#9AA8B4"
TABLE_BORDER_THICKNESS = 0.35
TABLE_COLUMN_WIDTHS = (68, 21, 27, 29, 29)  # mm
TABLE_CELL_PADDING = 5
TABLE_ROW_COLORS = ("#FFFFFF", "#F5F7F8")

CUSTOMER_COLUMN_WIDTHS = (92, 82)  # mm
CUSTOMER_HEADING_BORDER_COLOR = "#18324B"
CUSTOMER_HEADING_BORDER_THICKNESS = 0.5
CUSTOMER_HEADING_BOTTOM_PADDING = 5

PROJECT_NAME_FONT = "Helvetica"
PROJECT_NAME_FONT_SIZE = 9
PROJECT_NAME_COLOR = "#000000"
PROJECT_NAME_ALIGNMENT = "LEFT"
PROJECT_NAME_BACKGROUND = "#E9EEF2"
PROJECT_NAME_BORDER_COLOR = "#9AA8B4"
PROJECT_NAME_BORDER_THICKNESS = 0.35
PROJECT_NAME_CELL_PADDING = 6
PROJECT_NAME_TOP_PADDING = 5
PROJECT_NAME_BOTTOM_PADDING = 5

TERMS_FONT = "Helvetica"
TERMS_FONT_SIZE = 8
TERMS_COLOR = "#000000"
TERMS_LINE_SPACING = 9
TERMS_HEADING_FONT = "Helvetica-Bold"
TERMS_HEADING_SIZE = 9
TERMS_HEADING_COLOR = "#000000"

BACKGROUND_COLOR = "#FFFFFF"
HEADER_BACKGROUND_COLOR = "#FAFCFD"
BODY_TEXT_COLOR = "#000000"
PLACEHOLDER_TEXT_COLOR = "#6C7882"


def pdf_color(value: str):
    return colors.HexColor(value)


def text_alignment(value: str) -> int:
    return {"LEFT": TA_LEFT, "CENTER": TA_CENTER, "RIGHT": TA_RIGHT}[value.upper()]


def draw_page_background(canvas, document) -> None:
    canvas.saveState()
    canvas.setFillColor(pdf_color(BACKGROUND_COLOR))
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.restoreState()


def sanitize_filename(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")
    return value or "quotation"


def generated_item_name(item_name: str, project_name: str) -> str:
    base = re.sub(r"\s+", " ", item_name).strip()
    project = project_name.strip()
    if not project:
        return base
    base = re.sub(r"\s+FOR\s+P/N\s*$", "", base, flags=re.IGNORECASE)
    base = re.sub(r"\s+FOR\s*$", "", base, flags=re.IGNORECASE)
    return f"{base} FOR {project}"


def money(value: str | int | float | Decimal) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("A monetary value must be numeric.") from exc
    return result.quantize(Decimal("0.01"))


def calculate_total(hours: str | int | float | Decimal, rate: str | int | float | Decimal) -> Decimal:
    return (money(hours) * money(rate)).quantize(Decimal("0.01"))


def create_quotation_pdf(path: Path, config: dict, customer: dict, quotation: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontName=GENERAL_TEXT_FONT, fontSize=GENERAL_TEXT_SIZE, leading=GENERAL_TEXT_LINE_SPACING, textColor=pdf_color(GENERAL_TEXT_COLOR))
    small = ParagraphStyle("Small", parent=body, fontName=SMALL_TEXT_FONT, fontSize=SMALL_TEXT_SIZE, leading=SMALL_TEXT_LINE_SPACING, textColor=pdf_color(SMALL_TEXT_COLOR))
    right = ParagraphStyle("Right", parent=body, alignment=TA_RIGHT)
    centered = ParagraphStyle("Centered", parent=small, alignment=text_alignment("CENTER"), textColor=pdf_color(PLACEHOLDER_TEXT_COLOR))
    title = ParagraphStyle("Title", parent=styles["Heading1"], fontName=COMPANY_NAME_FONT, fontSize=COMPANY_NAME_FONT_SIZE, leading=COMPANY_NAME_FONT_SIZE, textColor=pdf_color(COMPANY_NAME_COLOR), alignment=text_alignment(COMPANY_NAME_ALIGNMENT))
    section = ParagraphStyle("Section", parent=body, fontName=SECTION_HEADING_FONT, fontSize=SECTION_HEADING_FONT_SIZE, leading=SECTION_HEADING_LINE_SPACING, textColor=pdf_color(SECTION_HEADING_COLOR))
    table_body = ParagraphStyle("TableBody", parent=body, fontName=TABLE_FONT, fontSize=TABLE_FONT_SIZE)
    table_right = ParagraphStyle("TableRight", parent=table_body, alignment=TA_RIGHT)
    document = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=PAGE_MARGIN_RIGHT * mm, leftMargin=PAGE_MARGIN_LEFT * mm, topMargin=PAGE_MARGIN_TOP * mm, bottomMargin=PAGE_MARGIN_BOTTOM * mm, onFirstPage=draw_page_background)
    table_header = ParagraphStyle("TableHeader", parent=small, fontName=TABLE_HEADER_FONT, fontSize=TABLE_HEADER_FONT_SIZE, leading=TABLE_HEADER_LINE_SPACING, textColor=pdf_color(TABLE_HEADER_TEXT_COLOR), alignment=text_alignment(TABLE_HEADER_ALIGNMENT))
    story = []
    logo = config.get("logo_path", "")
    address_lines = [config.get(key, "") for key in ("address_line1", "address_line2", "address_line3")]
    contact_lines = [config.get(key, "") for key in ("phone", "email", "website")]
    if logo and Path(logo).is_file():
        logo_content = Image(logo, width=LOGO_WIDTH * mm, height=LOGO_HEIGHT * mm, kind="proportional")
    else:
        logo_content = Paragraph("COMPANY<br/>LOGO", centered)
    company_address = ParagraphStyle(
        "CompanyAddress",
        parent=body,
        alignment=text_alignment(ADDRESS_ALIGNMENT),
        fontName=ADDRESS_FONT,
        fontSize=ADDRESS_FONT_SIZE,
        leading=ADDRESS_LINE_SPACING,
        textColor=pdf_color(ADDRESS_COLOR),
    )
    company_contact = ParagraphStyle(
        "CompanyContact",
        parent=company_address,
        alignment=text_alignment(EMAIL_WEBSITE_ALIGNMENT),
        fontName=EMAIL_WEBSITE_FONT,
        fontSize=EMAIL_WEBSITE_FONT_SIZE,
        textColor=pdf_color(EMAIL_WEBSITE_COLOR),
    )
    company_content = [Paragraph(config.get("company_name", ""), title)]
    if any(address_lines):
        company_content.append(Paragraph("<br/>".join(line for line in address_lines if line), company_address))
    if any(contact_lines):
        company_content.append(Paragraph("<br/>".join(line for line in contact_lines if line), company_contact))

    header = Table([[logo_content, company_content]], colWidths=[LOGO_COLUMN_WIDTH * mm, COMPANY_COLUMN_WIDTH * mm], rowHeights=[HEADER_ROW_HEIGHT * mm])
    header.setStyle(TableStyle([
        ("BOX", (0, 0), (0, 0), 0.0, pdf_color(HEADER_BACKGROUND_COLOR)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), LOGO_POSITION),
        ("LEFTPADDING", (0, 0), (-1, -1), HEADER_CELL_PADDING),
        ("RIGHTPADDING", (0, 0), (-1, -1), HEADER_CELL_PADDING),
        ("TOPPADDING", (0, 0), (-1, -1), HEADER_TOP_PADDING),
        ("BOTTOMPADDING", (0, 0), (-1, -1), HEADER_BOTTOM_PADDING),
    ]))
    story.append(header)
    story.append(Spacer(1, SPACE_AFTER_HEADER * mm))

    customer_lines = [customer.get("contact_name", ""), customer.get("customer_name", "")]
    customer_lines += [customer.get(key, "") for key in ("address_line1", "address_line2", "address_line3", "address_line4")]
    info = [[Paragraph("QUOTATION TO", section), Paragraph("QUOTATION", section)], [Paragraph("<br/>".join(line for line in customer_lines if line), body), Paragraph(f"<b>Quotation No:</b> {quotation['quotation_number']}<br/><b>Date:</b> {quotation['date']}", body)]]
    customer_table = Table(info, colWidths=[width * mm for width in CUSTOMER_COLUMN_WIDTHS])
    customer_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTNAME", (0, 0), (-1, 0), SECTION_HEADING_FONT), ("LINEBELOW", (0, 0), (-1, 0), CUSTOMER_HEADING_BORDER_THICKNESS, pdf_color(CUSTOMER_HEADING_BORDER_COLOR)), ("BOTTOMPADDING", (0, 0), (-1, 0), CUSTOMER_HEADING_BOTTOM_PADDING)]))
    story.append(customer_table)
    story.append(Spacer(1, SPACE_AFTER_CUSTOMER * mm))
    project_style = ParagraphStyle("ProjectName", parent=body, fontName=PROJECT_NAME_FONT, fontSize=PROJECT_NAME_FONT_SIZE, textColor=pdf_color(PROJECT_NAME_COLOR), alignment=text_alignment(PROJECT_NAME_ALIGNMENT))
    project_table = Table([[Paragraph("PROJECT NAME", section)], [Paragraph(quotation["project_name"], project_style)]], colWidths=[sum(CUSTOMER_COLUMN_WIDTHS) * mm])
    project_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), pdf_color(PROJECT_NAME_BACKGROUND)),
        ("BOX", (0, 0), (-1, -1), PROJECT_NAME_BORDER_THICKNESS, pdf_color(PROJECT_NAME_BORDER_COLOR)),
        ("LINEBELOW", (0, 0), (-1, 0), PROJECT_NAME_BORDER_THICKNESS, pdf_color(PROJECT_NAME_BORDER_COLOR)),
        ("LEFTPADDING", (0, 0), (-1, -1), PROJECT_NAME_CELL_PADDING),
        ("RIGHTPADDING", (0, 0), (-1, -1), PROJECT_NAME_CELL_PADDING),
        ("TOPPADDING", (0, 0), (-1, -1), PROJECT_NAME_TOP_PADDING),
        ("BOTTOMPADDING", (0, 0), (-1, -1), PROJECT_NAME_BOTTOM_PADDING),
    ]))
    story.append(project_table)
    story.append(Spacer(1, SPACE_AFTER_PROJECT * mm))
    story.append(Paragraph(f"Dear {quotation['greeting_name']},", body))
    story.append(Paragraph("We are pleased to quote the following in response to your enquiry.", body))
    story.append(Spacer(1, SPACE_BEFORE_ITEMS * mm))

    currency = config.get("currency", "USD")
    rows = [[Paragraph("Item Name", table_header), Paragraph("Total Hours", table_header), Paragraph("Unit Rate", table_header), Paragraph("Estimated Total Price", table_header), Paragraph("Completion<br/>(General Lead Time)", table_header)]]
    for item in quotation["items"]:
        rows.append([Paragraph(item["name"], table_body), Paragraph(str(item["hours"]), table_right), Paragraph(f"{currency} {item['rate']}/Hour", table_right), Paragraph(f"{currency} {item['total']}", table_right), Paragraph(item["lead_time"], table_body)])
    table = Table(rows, colWidths=[width * mm for width in TABLE_COLUMN_WIDTHS], repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), pdf_color(TABLE_HEADER_BACKGROUND)), ("TEXTCOLOR", (0, 0), (-1, 0), pdf_color(TABLE_HEADER_TEXT_COLOR)), ("GRID", (0, 0), (-1, -1), TABLE_BORDER_THICKNESS, pdf_color(TABLE_BORDER_COLOR)), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [pdf_color(color) for color in TABLE_ROW_COLORS]), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), TABLE_CELL_PADDING), ("RIGHTPADDING", (0, 0), (-1, -1), TABLE_CELL_PADDING), ("TOPPADDING", (0, 0), (-1, -1), TABLE_CELL_PADDING), ("BOTTOMPADDING", (0, 0), (-1, -1), TABLE_CELL_PADDING)]))
    story.append(table)
    story.append(Spacer(1, SPACE_BEFORE_TERMS * mm))
    terms_heading = ParagraphStyle("TermsHeading", parent=body, fontName=TERMS_HEADING_FONT, fontSize=TERMS_HEADING_SIZE, textColor=pdf_color(TERMS_HEADING_COLOR))
    terms_text = ParagraphStyle("TermsText", parent=small, fontName=TERMS_FONT, fontSize=TERMS_FONT_SIZE, leading=TERMS_LINE_SPACING, textColor=pdf_color(TERMS_COLOR))
    story.append(Paragraph("Terms &amp; Conditions", terms_heading))
    for index, term in enumerate(config.get("terms", []), 1):
        story.append(Paragraph(f"{index}. {term}", terms_text))
        story.append(Spacer(1, SPACE_BETWEEN_TERMS * mm))
    document.build(story)
    return path
