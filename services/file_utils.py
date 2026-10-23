from __future__ import annotations

import csv
import json
import logging
import os
import sqlite3
import tempfile
from pathlib import Path

DEFAULT_CONFIG = {
    "company_name": "ECV Interconnect Solutions Private Limited",
    "address_line1": "",
    "address_line2": "",
    "address_line3": "",
    "phone": "",
    "email": "",
    "website": "",
    "logo_path": "",
    "quotation_output_folder": "output/quotations",
    "currency": "USD",
    "company_code": "ECV",
    "terms": []
}

DEFAULT_CUSTOMERS = [{"customer_code": "MMS", "customer_name": "MMS Corporation (edit placeholder)", "contact_name": "Contact name", "address_line1": "Address line 1", "address_line2": "Address line 2", "address_line3": "", "address_line4": "", "greeting_name": "Customer", "active": True}]
DEFAULT_ITEMS = [{"item_code": "PCB_NRE", "item_name": "PCB NRE FOR P/N", "category": "PCB", "unit_rate": "23", "currency": "USD", "active": "true"}]


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        os.replace(temporary, path)
    except Exception:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def load_json(path: Path, default):
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        logging.exception("Could not load JSON file %s", path)
        return default


def save_json(path: Path, value) -> None:
    atomic_write_text(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def load_items(path: Path) -> list[dict]:
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    except (FileNotFoundError, csv.Error, OSError):
        logging.exception("Could not load item CSV %s", path)
        return []


def save_items(path: Path, items: list[dict]) -> None:
    fields = ["item_code", "item_name", "category", "unit_rate", "currency", "active"]
    output = []
    from io import StringIO
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows({field: item.get(field, "") for field in fields} for item in items)
    atomic_write_text(path, stream.getvalue())


def initialize_app(root: Path) -> dict[str, Path]:
    config_dir, data_dir = root / "config", root / "data"
    output_dir, logs_dir = root / "output" / "quotations", root / "logs"
    config_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=logs_dir / "application.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config_path = config_dir / "config.json"
    if not config_path.exists():
        save_json(config_path, DEFAULT_CONFIG)
    customer_path = data_dir / "customers.json"
    if not customer_path.exists():
        save_json(customer_path, DEFAULT_CUSTOMERS)
    item_path = data_dir / "items.csv"
    if not item_path.exists():
        save_items(item_path, DEFAULT_ITEMS)
    database_path = data_dir / "quotation.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS quotation_sequences (
                customer_code TEXT NOT NULL,
                quotation_year INTEGER NOT NULL,
                last_sequence INTEGER NOT NULL,
                PRIMARY KEY (customer_code, quotation_year)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS quotations (
                quotation_number TEXT PRIMARY KEY,
                customer_code TEXT NOT NULL,
                quotation_year INTEGER NOT NULL,
                quotation_date TEXT NOT NULL,
                project_name TEXT NOT NULL,
                pdf_file TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
    return {"root": root, "config": config_path, "customers": customer_path, "items": item_path, "database": database_path, "output": output_dir, "logs": logs_dir}
