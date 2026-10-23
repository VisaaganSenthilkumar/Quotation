from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


class QuotationNumberService:
    def __init__(self, database_path: Path, company_code: str = ""):
        self.database_path = database_path
        self.company_code = company_code

    def next_number(
        self,
        customer_code: str,
        quotation_year: int | None = None,
        quotation_date: str | None = None,
        project_name: str = "",
        pdf_file: str = "",
    ) -> str:
        customer_code = customer_code.strip().upper()
        if not customer_code:
            raise ValueError("Customer code is required.")
        year = quotation_year or datetime.now().year
        date_value = quotation_date or datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(self.database_path, timeout=10, isolation_level=None) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute(
                    "SELECT last_sequence FROM quotation_sequences WHERE customer_code = ? AND quotation_year = ?",
                    (customer_code, year),
                ).fetchone()
                sequence = (row[0] if row else 0) + 1
                connection.execute(
                    "INSERT INTO quotation_sequences(customer_code, quotation_year, last_sequence) VALUES (?, ?, ?) "
                    "ON CONFLICT(customer_code, quotation_year) DO UPDATE SET last_sequence = excluded.last_sequence",
                    (customer_code, year, sequence),
                )
                quotation_number = f"{customer_code}/{year}/Q{sequence:03d}"
                connection.execute(
                    "INSERT INTO quotations(quotation_number, customer_code, quotation_year, quotation_date, project_name, pdf_file, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (quotation_number, customer_code, year, date_value, project_name, pdf_file, datetime.now().isoformat(timespec="seconds")),
                )
                connection.execute("COMMIT")
                return quotation_number
            except Exception:
                connection.execute("ROLLBACK")
                raise
