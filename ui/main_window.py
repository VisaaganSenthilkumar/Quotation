from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGridLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QMainWindow,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from services.customer_service import CustomerService
from services.file_utils import load_json, save_json
from services.item_service import ItemService
from services.pdf_service import calculate_total, create_quotation_pdf, generated_item_name, sanitize_filename
from services.quotation_number_service import QuotationNumberService
from utils.validators import validate_item, validate_quotation


class ItemDialog(QDialog):
    def __init__(self, items: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Quotation Item")
        form = QFormLayout(self)
        self.item = QComboBox()
        for item in items:
            self.item.addItem(f"{item['item_code']} - {item['item_name']}", item)
        self.hours = QLineEdit("1")
        self.rate = QLineEdit()
        self.lead_time = QLineEdit("4 Working Days")
        self.item.currentIndexChanged.connect(self._set_rate)
        form.addRow("Item", self.item)
        form.addRow("Total hours", self.hours)
        form.addRow("Unit rate", self.rate)
        form.addRow("Lead time", self.lead_time)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        self._set_rate()

    def _set_rate(self):
        selected = self.item.currentData() or {}
        self.rate.setText(str(selected.get("unit_rate", "")))

    def values(self) -> dict:
        selected = self.item.currentData()
        return {"item_code": selected.get("item_code", ""), "item_name": selected.get("item_name", ""), "hours": self.hours.text(), "rate": self.rate.text(), "lead_time": self.lead_time.text()}


class MainWindow(QMainWindow):
    def __init__(self, paths: dict[str, Path]):
        super().__init__()
        self.paths = paths
        self.config = load_json(paths["config"], {})
        self.customer_service = CustomerService(paths["customers"])
        self.item_service = ItemService(paths["items"])
        self.number_service = QuotationNumberService(paths["database"])
        self.customers = self.customer_service.all()
        self.items = self.item_service.all()
        self.setWindowTitle("Quotation Generator")
        self.resize(1000, 700)
        self._build_ui()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        heading = QLabel("Quotation Generator")
        heading.setStyleSheet("font-size: 22px; font-weight: bold; color:#31618f;")
        layout.addWidget(heading)

        details = QGroupBox("Quotation details")
        grid = QGridLayout(details)
        self.customer = QComboBox()
        for customer in self.customers:
            self.customer.addItem(f"{customer['customer_code']} - {customer['customer_name']}", customer)
        self.project = QLineEdit()
        self.greeting = QLineEdit()
        self.number = QLineEdit("Assigned on generation")
        self.number.setReadOnly(True)
        self.quotation_date = QLabel(date.today().strftime("%-d-%b-%Y") if os.name != "nt" else date.today().strftime("%#d-%b-%Y"))
        self.customer.currentIndexChanged.connect(self._customer_changed)
        grid.addWidget(QLabel("Customer"), 0, 0)
        grid.addWidget(self.customer, 0, 1)
        grid.addWidget(QLabel("Quotation No"), 0, 2)
        grid.addWidget(self.number, 0, 3)
        grid.addWidget(QLabel("Date"), 1, 0)
        grid.addWidget(self.quotation_date, 1, 1)
        grid.addWidget(QLabel("Project name"), 1, 2)
        grid.addWidget(self.project, 1, 3)
        grid.addWidget(QLabel("Dear"), 2, 0)
        grid.addWidget(self.greeting, 2, 1)
        layout.addWidget(details)

        items_box = QGroupBox("Quotation items")
        items_layout = QVBoxLayout(items_box)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Item", "Hours", "Rate", "Total", "Lead time"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        items_layout.addWidget(self.table)
        item_buttons = QHBoxLayout()
        add = QPushButton("Add Item")
        remove = QPushButton("Remove Item")
        add.clicked.connect(self._add_item)
        remove.clicked.connect(self._remove_item)
        item_buttons.addWidget(add)
        item_buttons.addWidget(remove)
        item_buttons.addStretch()
        items_layout.addLayout(item_buttons)
        layout.addWidget(items_box)

        actions = QHBoxLayout()
        preview = QPushButton("Preview")
        draft = QPushButton("Save Draft")
        customers = QPushButton("Customers")
        items = QPushButton("Items")
        generate = QPushButton("Generate PDF")
        clear = QPushButton("Clear")
        settings = QPushButton("Settings")
        exit_button = QPushButton("Exit")
        preview.clicked.connect(self._preview)
        draft.clicked.connect(self._save_draft)
        customers.clicked.connect(self._manage_customers)
        items.clicked.connect(self._manage_items)
        generate.clicked.connect(self._generate)
        clear.clicked.connect(self._clear)
        settings.clicked.connect(self._settings)
        exit_button.clicked.connect(self.close)
        for button in (preview, draft, customers, items, generate, clear, settings, exit_button):
            actions.addWidget(button)
        layout.addLayout(actions)
        self._customer_changed()

    def _customer_changed(self):
        customer = self.customer.currentData() or {}
        self.greeting.setText(customer.get("greeting_name", ""))

    def _add_item(self):
        dialog = ItemDialog(self.items, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        item = dialog.values()
        errors = validate_item(item)
        if errors:
            QMessageBox.warning(self, "Invalid item", "\n".join(errors))
            return
        row = self.table.rowCount()
        self.table.insertRow(row)
        project = self.project.text() or "P/N"
        values = [generated_item_name(item["item_name"], project), item["hours"], item["rate"], str(calculate_total(item["hours"], item["rate"])), item["lead_time"]]
        for column, value in enumerate(values):
            self.table.setItem(row, column, QTableWidgetItem(value))

    def _remove_item(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def _quotation_items(self) -> list[dict]:
        return [{"name": self.table.item(row, 0).text(), "hours": self.table.item(row, 1).text(), "rate": self.table.item(row, 2).text(), "total": self.table.item(row, 3).text(), "lead_time": self.table.item(row, 4).text()} for row in range(self.table.rowCount())]

    def _generate(self):
        customer = self.customer.currentData() or {}
        items = self._quotation_items()
        errors = validate_quotation(customer.get("customer_code", ""), self.project.text(), [{"item_code": item["name"], "hours": item["hours"], "rate": item["rate"], "lead_time": item["lead_time"]} for item in items])
        if errors:
            QMessageBox.warning(self, "Check quotation", "\n".join(errors))
            return
        project_name = self.project.text().strip()
        output_folder = Path(self.config.get("quotation_output_folder", "output/quotations"))
        if not output_folder.is_absolute():
            output_folder = self.paths["root"] / output_folder
        try:
            quotation_number = self.number_service.next_number(customer["customer_code"], quotation_date=date.today().isoformat(), project_name=project_name)
            filename = sanitize_filename(f"{quotation_number.replace('/', '_')}_{project_name}") + ".pdf"
            pdf_path = output_folder / filename
            quotation = {"quotation_number": quotation_number, "date": self.quotation_date.text(), "project_name": project_name, "greeting_name": self.greeting.text().strip(), "items": items}
            create_quotation_pdf(pdf_path, self.config, customer, quotation)
            self.number.setText(quotation_number)
            QMessageBox.information(self, "Quotation generated", f"Created:\n{pdf_path}")
            self._open_file(pdf_path)
        except Exception as exc:
            logging.exception("Could not generate quotation")
            QMessageBox.critical(self, "Generation failed", "The quotation could not be generated. Check logs/application.log for details.")

    def _preview(self):
        customer = self.customer.currentData() or {}
        items = self._quotation_items()
        errors = validate_quotation(customer.get("customer_code", ""), self.project.text(), [{"item_code": item["name"], "hours": item["hours"], "rate": item["rate"], "lead_time": item["lead_time"]} for item in items])
        if errors:
            QMessageBox.warning(self, "Check quotation", "\n".join(errors))
            return
        preview_path = self.paths["root"] / "output" / "quotation-preview.pdf"
        quotation = {"quotation_number": "PREVIEW", "date": self.quotation_date.text(), "project_name": self.project.text().strip(), "greeting_name": self.greeting.text().strip(), "items": items}
        try:
            create_quotation_pdf(preview_path, self.config, customer, quotation)
            self._open_file(preview_path)
        except Exception:
            logging.exception("Could not create quotation preview")
            QMessageBox.critical(self, "Preview failed", "The preview could not be created.")

    def _save_draft(self):
        draft_path, _ = QFileDialog.getSaveFileName(self, "Save draft", str(self.paths["root"] / "output"), "JSON files (*.json)")
        if not draft_path:
            return
        draft = {"customer_code": (self.customer.currentData() or {}).get("customer_code", ""), "project_name": self.project.text(), "greeting_name": self.greeting.text(), "items": self._quotation_items()}
        try:
            save_json(Path(draft_path), draft)
        except OSError:
            QMessageBox.critical(self, "Save failed", "The draft could not be saved.")

    def _manage_customers(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Customer Management")
        layout = QVBoxLayout(dialog)
        list_widget = QListWidget()
        list_widget.addItems(f"{item['customer_code']} - {item['customer_name']}" for item in self.customer_service.all(active_only=False))
        layout.addWidget(list_widget)
        edit = QPushButton("Edit selected customer")
        deactivate = QPushButton("Deactivate selected customer")
        layout.addWidget(edit)
        layout.addWidget(deactivate)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(dialog.reject)
        layout.addWidget(close)

        def selected_customer():
            row = list_widget.currentRow()
            records = self.customer_service.all(active_only=False)
            return records[row] if 0 <= row < len(records) else None

        def edit_customer():
            record = selected_customer()
            if not record:
                return
            editor = QDialog(dialog)
            form = QFormLayout(editor)
            fields = {}
            for key in ("customer_code", "customer_name", "contact_name", "address_line1", "address_line2", "address_line3", "address_line4", "greeting_name"):
                fields[key] = QLineEdit(record.get(key, ""))
                form.addRow(key.replace("_", " ").title(), fields[key])
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
            buttons.accepted.connect(editor.accept)
            buttons.rejected.connect(editor.reject)
            form.addRow(buttons)
            if editor.exec() == QDialog.DialogCode.Accepted:
                updated = {key: field.text().strip() for key, field in fields.items()}
                updated["active"] = record.get("active", True)
                try:
                    self.customer_service.save(updated, record.get("customer_code"))
                    dialog.accept()
                    self._reload_data()
                except ValueError as exc:
                    QMessageBox.warning(dialog, "Customer not saved", str(exc))

        def deactivate_customer():
            record = selected_customer()
            if record:
                self.customer_service.deactivate(record["customer_code"])
                dialog.accept()
                self._reload_data()

        edit.clicked.connect(edit_customer)
        deactivate.clicked.connect(deactivate_customer)
        dialog.exec()

    def _manage_items(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Item Management")
        layout = QVBoxLayout(dialog)
        list_widget = QListWidget()
        records = self.item_service.all(active_only=False)
        list_widget.addItems(f"{item['item_code']} - {item['item_name']} ({item['unit_rate']})" for item in records)
        layout.addWidget(list_widget)
        edit = QPushButton("Edit selected item")
        layout.addWidget(edit)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(dialog.reject)
        layout.addWidget(close)

        def edit_item():
            row = list_widget.currentRow()
            if row < 0:
                return
            record = records[row]
            editor = QDialog(dialog)
            form = QFormLayout(editor)
            fields = {}
            for key in ("item_code", "item_name", "category", "unit_rate", "currency"):
                fields[key] = QLineEdit(record.get(key, ""))
                form.addRow(key.replace("_", " ").title(), fields[key])
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
            buttons.accepted.connect(editor.accept)
            buttons.rejected.connect(editor.reject)
            form.addRow(buttons)
            if editor.exec() == QDialog.DialogCode.Accepted:
                updated = {key: field.text().strip() for key, field in fields.items()}
                updated["active"] = record.get("active", "true")
                try:
                    self.item_service.save(updated, record.get("item_code"))
                    dialog.accept()
                    self._reload_data()
                except ValueError as exc:
                    QMessageBox.warning(dialog, "Item not saved", str(exc))

        edit.clicked.connect(edit_item)
        dialog.exec()

    def _reload_data(self):
        self.customers = self.customer_service.all()
        self.items = self.item_service.all()
        current_code = (self.customer.currentData() or {}).get("customer_code")
        self.customer.clear()
        for customer in self.customers:
            self.customer.addItem(f"{customer['customer_code']} - {customer['customer_name']}", customer)
        for index in range(self.customer.count()):
            if (self.customer.itemData(index) or {}).get("customer_code") == current_code:
                self.customer.setCurrentIndex(index)
                break

    @staticmethod
    def _open_file(path: Path):
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def _clear(self):
        self.project.clear()
        self.table.setRowCount(0)
        self.number.setText("Assigned on generation")
        self._customer_changed()

    def _settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        form = QFormLayout(dialog)
        company = QLineEdit(self.config.get("company_name", ""))
        address_line1 = QLineEdit(self.config.get("address_line1", ""))
        address_line2 = QLineEdit(self.config.get("address_line2", ""))
        address_line3 = QLineEdit(self.config.get("address_line3", ""))
        phone = QLineEdit(self.config.get("phone", ""))
        email = QLineEdit(self.config.get("email", ""))
        website = QLineEdit(self.config.get("website", ""))
        currency = QLineEdit(self.config.get("currency", "USD"))
        logo = QLineEdit(self.config.get("logo_path", ""))
        logo_browse = QPushButton("Browse...")
        logo_row = QWidget()
        logo_layout = QHBoxLayout(logo_row)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.addWidget(logo)
        logo_layout.addWidget(logo_browse)
        output = QLineEdit(self.config.get("quotation_output_folder", "output/quotations"))
        terms = QListWidget()
        terms.addItems(self.config.get("terms", []))
        logo_browse.clicked.connect(lambda: self._browse_logo(logo, dialog))
        form.addRow("Company name", company)
        form.addRow("Address line 1", address_line1)
        form.addRow("Address line 2", address_line2)
        form.addRow("Address line 3", address_line3)
        form.addRow("Phone", phone)
        form.addRow("Email", email)
        form.addRow("Website", website)
        form.addRow("Currency", currency)
        form.addRow("Company logo", logo_row)
        form.addRow("Output folder", output)
        form.addRow("Terms", terms)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config.update({
                "company_name": company.text().strip(),
                "address_line1": address_line1.text().strip(),
                "address_line2": address_line2.text().strip(),
                "address_line3": address_line3.text().strip(),
                "phone": phone.text().strip(),
                "email": email.text().strip(),
                "website": website.text().strip(),
                "currency": currency.text().strip() or "USD",
                "logo_path": logo.text().strip(),
                "quotation_output_folder": output.text().strip() or "output/quotations",
                "terms": [terms.item(i).text() for i in range(terms.count())],
            })
            save_json(self.paths["config"], self.config)

    @staticmethod
    def _browse_logo(logo_field: QLineEdit, parent: QWidget):
        logo_path, _ = QFileDialog.getOpenFileName(
            parent,
            "Select company logo",
            "",
            "Image files (*.png *.jpg *.jpeg *.bmp);;All files (*.*)",
        )
        if logo_path:
            logo_field.setText(logo_path)
