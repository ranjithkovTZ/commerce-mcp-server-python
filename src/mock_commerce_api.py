"""Mock Commerce API that serves local payload files — no BTP destination required."""
from __future__ import annotations

import json
from pathlib import Path

_PAYLOADS = Path(__file__).parent.parent / "assets" / "payloads"


def _load(filename: str) -> dict:
    """Load and parse a JSON payload file from the local payload directory."""
    return json.loads((_PAYLOADS / filename).read_text(encoding="utf-8"))


class MockCommerceApi:
    """Mock implementation of the Commerce API using local payload files."""

    def get_products(self, destination=None) -> dict:
        """Return all products from the mock payload."""
        return _load("get_products_response.json")

    def get_categories(self, destination=None) -> dict:
        """Return all categories from the mock payload."""
        return _load("get_categories.json")

    def get_products_by_category(self, destination=None, category_id: str = "") -> dict:
        """Return products filtered by the provided category ID."""
        data = _load("get_products_response.json")
        filtered = [p for p in data.get("value", []) if p.get("category_ID") == category_id]
        return {"@odata.context": "$metadata#Products", "value": filtered}

    def get_retailers(self, destination=None) -> dict:
        """Return business partners filtered to retailer type."""
        data = _load("get_business_partners.json")
        filtered = [bp for bp in data.get("value", []) if bp.get("type") == "RETAILER"]
        return {"@odata.context": "$metadata#BusinessPartners", "value": filtered}
