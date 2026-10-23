from __future__ import annotations

from decimal import Decimal, InvalidOperation


def validate_item(item: dict) -> list[str]:
    errors = []
    if not item.get("item_code"):
        errors.append("Item is mandatory.")
    try:
        hours = Decimal(str(item.get("hours", "")))
        if hours <= 0:
            errors.append("Total hours must be greater than zero.")
    except (InvalidOperation, ValueError):
        errors.append("Total hours must be numeric.")
    try:
        if Decimal(str(item.get("rate", ""))) < 0:
            errors.append("Unit rate cannot be negative.")
    except (InvalidOperation, ValueError):
        errors.append("Unit rate must be numeric.")
    if not item.get("lead_time", "").strip():
        errors.append("Lead time is mandatory.")
    return errors


def validate_quotation(customer_code: str, project_name: str, items: list[dict]) -> list[str]:
    errors = []
    if not customer_code:
        errors.append("Customer is mandatory.")
    if not project_name.strip():
        errors.append("Project name is mandatory.")
    if not items:
        errors.append("Add at least one quotation item.")
    for item in items:
        errors.extend(validate_item(item))
    return errors
