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
    products_path: str = "/Products"


class CommerceApi:
    """Commerce API with all the API calls
    """
    def __init__(self, config: CommerceApiConfig | None = None):
        self._config = config or CommerceApiConfig(
            products_path=os.getenv("COMMERCE_PRODUCTS_PATH", "/Products")
        )

    def get_products(self, destination: DestinationDetails) -> dict:
        """Get Products

        Args:
            destination (DestinationDetails): The details of the destination.

        Returns:
            dict: The products data.
        """
        url = _join_url(destination.url, self._config.products_path)

        headers: dict[str, str] = {"Accept": "application/json"}
        if destination.auth_header:
            headers["Authorization"] = f"Bearer {destination.auth_header}"

        timeout = httpx.Timeout(30.0)
        resp = httpx.get(url, headers=headers, timeout=timeout)

        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else {"value": data}
