from pathlib import Path
from .file_utils import load_items, save_items


class ItemService:
    def __init__(self, path: Path):
        self.path = path

    def all(self, active_only=True):
        items = load_items(self.path)
        return [i for i in items if i.get("active", "true").lower() == "true"] if active_only else items

    def save(self, item: dict, original_code: str | None = None):
        items = load_items(self.path)
        code = item["item_code"].strip().upper()
        if any(i.get("item_code", "").upper() == code and i.get("item_code") != original_code for i in items):
            raise ValueError("Item code already exists.")
        item["item_code"] = code
        for index, existing in enumerate(items):
            if existing.get("item_code") == original_code:
                items[index] = item
                break
        else:
            items.append(item)
        save_items(self.path, items)
