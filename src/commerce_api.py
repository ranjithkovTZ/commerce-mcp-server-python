from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from destination_client import DestinationDetails


def _join_url(base: str, path: str) -> str:
    return base.rstrip("/") + "/" + path.lstrip("/")


@dataclass(frozen=True)
class CommerceApiConfig:
    """API paths
    """
    products_path: str = "/odata/v4/catalog/Products"
    categories_path: str = "/odata/v4/catalog/Categories"
    business_partners_path: str = "/odata/v4/commerce/BusinessPartners"


class CommerceApi:
    """Commerce API with all the API calls
    """
    def __init__(self, config: CommerceApiConfig | None = None):
        self._config = config or CommerceApiConfig(
            products_path=os.getenv("COMMERCE_PRODUCTS_PATH", "/odata/v4/catalog/Products")
        )

    def get_products(self, destination: DestinationDetails) -> dict:
        """Get Products

        Args:
            destination (DestinationDetails): The details of the destination.

        Returns:
            dict: The products data.
        """
        url = _join_url(destination.url, self._config.products_path)

        print(f"URL: {url}")

        headers: dict[str, str] = {"Accept": "application/json"}
        if destination.auth_header:
            headers["Authorization"] = f"{destination.auth_header}"

        timeout = httpx.Timeout(30.0)
        resp = httpx.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else {"value": data}

    def get_categories(self, destination: DestinationDetails) -> dict:
        """Get Categories

        Args:
            destination (DestinationDetails): The details of the destination.

        Returns:
            dict: The categories data.
        """
        url = _join_url(destination.url, "/odata/v4/catalog/Categories")

        print(f"URL: {url}")

        headers: dict[str, str] = {"Accept": "application/json"}
        if destination.auth_header:
            headers["Authorization"] = f"{destination.auth_header}"

        timeout = httpx.Timeout(30.0)
        resp = httpx.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else {"value": data}

    def get_products_by_category(self, destination: DestinationDetails, category_id: str) -> dict:
        """Get Products by Category

        Args:
            destination (DestinationDetails): The details of the destination.
            category_id (str): The ID of the category.

        Returns:
            dict: The products data.
        """
        url = _join_url(destination.url, f"/odata/v4/catalog/Products?$filter=category_ID eq '{category_id}'")

        print(f"URL: {url}")

        headers: dict[str, str] = {"Accept": "application/json"}
        if destination.auth_header:
            headers["Authorization"] = f"{destination.auth_header}"

        timeout = httpx.Timeout(30.0)
        resp = httpx.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else {"value": data}


    def get_retailers(self, destination: DestinationDetails) -> dict:
        """Get Retailers (Business Partners)

        Args:
            destination (DestinationDetails): The details of the destination.

        Returns:
            dict: The retailers data.
        """
        url = _join_url(destination.url, "/odata/v4/commerce/BusinessPartners?$filter=type eq 'RETAILER'")

        print(f"URL: {url}")

        headers: dict[str, str] = {"Accept": "application/json"}
        if destination.auth_header:
            headers["Authorization"] = f"{destination.auth_header}"

        timeout = httpx.Timeout(30.0)
        resp = httpx.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else {"value": data}