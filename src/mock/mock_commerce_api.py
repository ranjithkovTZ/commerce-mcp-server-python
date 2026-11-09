"""Mock Commerce API that serves local payload files — no BTP destination required."""
from __future__ import annotations

import json
from pathlib import Path

_PAYLOADS = Path(__file__).parent.parent.parent / "assets" / "payloads"


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

    def get_product_details(self, destination=None, product_code: str = "") -> dict:
        """Return a single product's details looked up by product_code (sku)."""
        data = _load("get_product_details_response.json")
        product = data.get(product_code)
        if product is None:
            raise ValueError(f"No product found with product_code '{product_code}'.")
        return product

    def get_product_stock(self, destination=None, product_code: str = "") -> dict:
        """Return a single product's stock/availability looked up by product_code (sku)."""
        data = _load("get_product_stock_response.json")
        stock = data.get(product_code)
        if stock is None:
            raise ValueError(f"No stock availability found for product_code '{product_code}'.")
        return stock

    def get_retailers(self, destination=None) -> dict:
        """Return business partners filtered to retailer type."""
        data = _load("get_business_partners.json")
        filtered = [bp for bp in data.get("value", []) if bp.get("type") == "RETAILER"]
        return {"@odata.context": "$metadata#BusinessPartners", "value": filtered}

    def get_customer_orders(self, destination=None, email: str = "") -> dict:
        """Return a single customer's order history looked up by email."""
        data = _load("get_customer_orders_response.json")
        orders = data.get(email)
        if orders is None:
            raise ValueError(f"No orders found for email '{email}'.")
        return orders

    def get_order_details(self, destination=None, email: str = "", order_id: str = "") -> dict:
        """Return a single order's full details looked up by email and order_id."""
        data = _load("get_order_details_response.json")
        order = data.get(email, {}).get(order_id)
        if order is None:
            raise ValueError(f"No order '{order_id}' found for email '{email}'.")
        return order
