from pathlib import Path

from services.file_utils import initialize_app
from services.pdf_service import calculate_total, generated_item_name, sanitize_filename
from services.quotation_number_service import QuotationNumberService
from utils.validators import validate_item, validate_quotation


def test_number_sequences_and_year_rollover(tmp_path: Path):
    paths = initialize_app(tmp_path)
    service = QuotationNumberService(paths["database"])
    assert service.next_number("MPI", 2026) == "MPI/2026/Q001"
    assert service.next_number("MPI", 2026) == "MPI/2026/Q002"
    assert service.next_number("MMS", 2026) == "MMS/2026/Q001"
    assert service.next_number("MPI", 2026) == "MPI/2026/Q003"
    assert service.next_number("MPI", 2027) == "MPI/2027/Q001"


def test_calculation_and_item_name():
    assert calculate_total("18", "23") == 414
    assert generated_item_name("PCB NRE FOR P/N", "Project A") == "PCB NRE FOR Project A"
    assert generated_item_name("PCB NRE", "Project A") == "PCB NRE FOR Project A"


def test_filename_sanitization():
    assert sanitize_filename("MPI/2026/Q001:Project?") == "MPI_2026_Q001_Project_"


def test_validation():
    assert validate_quotation("MPI", "Project", [{"item_code": "PCB", "hours": "18", "rate": "23", "lead_time": "4 days"}]) == []
    assert "Project name is mandatory." in validate_quotation("MPI", "", [])
    assert "Total hours must be greater than zero." in validate_item({"item_code": "PCB", "hours": "0", "rate": "23", "lead_time": "4 days"})
