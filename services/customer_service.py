from pathlib import Path
from .file_utils import load_json, save_json


class CustomerService:
    def __init__(self, path: Path):
        self.path = path

    def all(self, active_only=True):
        customers = load_json(self.path, [])
        return [c for c in customers if c.get("active", True)] if active_only else customers

    def save(self, customer: dict, original_code: str | None = None):
        customers = load_json(self.path, [])
        code = customer["customer_code"].strip().upper()
        if any(c.get("customer_code", "").upper() == code and c.get("customer_code") != original_code for c in customers):
            raise ValueError("Customer code already exists.")
        customer["customer_code"] = code
        for index, existing in enumerate(customers):
            if existing.get("customer_code") == original_code:
                customers[index] = customer
                break
        else:
            customers.append(customer)
        save_json(self.path, customers)

    def deactivate(self, code: str):
        customers = load_json(self.path, [])
        for customer in customers:
            if customer.get("customer_code") == code:
                customer["active"] = False
        save_json(self.path, customers)
