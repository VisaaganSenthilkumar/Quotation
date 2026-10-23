# Quotation Generator

A local Windows desktop application for creating professional quotation PDFs. It uses PySide6 for the interface, ReportLab for A4 PDF output, JSON and CSV for editable master data, and SQLite for transactional quotation numbering.

## Run from source

```powershell
py -m pip install -r requirements.txt
py app.py
```

The first run creates `data/quotation.db`, `output/quotations/`, and `logs/application.log` without overwriting existing JSON, CSV, or configuration files.

## Features

- MPI and editable MMS customer records in `data/customers.json`
- MLO, MLC, and PCB rates in `data/items.csv`
- Configurable company details, output folder, and terms in `config/config.json`
- Separate transactional quotation sequences per customer and year
- Decimal-safe totals and multi-item quotations
- A4, multi-page ReportLab PDFs with repeating table headers
- Local-only operation with application logging

## Data management

JSON and CSV files are human-readable and can be edited while the application is closed. The Settings dialog edits the common company fields and terms. Customer and item service classes provide the persistence layer for future management dialogs without putting master data in Python logic.

## Numbering

Numbers are generated from SQLite, not filenames. A number is committed only when Generate PDF is confirmed, using the form `CUSTOMER/YYYY/Q###`, with independent sequences for each customer and year.

## Build the Windows executable

```powershell
pyinstaller --noconfirm --clean --name QuotationGenerator --windowed app.py
```

Deploy the generated executable together with `config/`, `data/`, `output/`, and `logs/`. The application recreates missing folders and seed files on startup.

## Troubleshooting

Check `logs/application.log` for file, database, and PDF errors. If a PDF cannot be opened automatically, it remains in the configured output folder and can be opened manually.
