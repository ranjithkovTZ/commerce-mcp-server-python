from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from destination_details import DestinationDetails

DEFAULT_FIELDS = (
    "products(code,name,summary,configurable,configuratorType,multidimensional,"
    "price(FULL),images(DEFAULT),stock(FULL),averageRating,variantOptions,baseProduct,"
    "priceRange(maxPrice(formattedValue),minPrice(formattedValue))),"
    "facets,breadcrumbs,pagination(DEFAULT),sorts(DEFAULT),freeTextSearch,"
    "currentQuery,keywordRedirectUrl"
)


def _join_url(base: str, path: str) -> str:
    return base.rstrip("/") + "/" + path.lstrip("/")


@dataclass(frozen=True)
class OccCommerceApiConfig:
    """API paths and search defaults for SAP Commerce Cloud's OCC v2 API."""
    fields: str = DEFAULT_FIELDS
    page_size: str = "12"
    lang: str = "en"
    curr: str = "USD"


class OccCommerceApi:
    """Commerce API that calls SAP Commerce Cloud's native OCC (v2) REST API."""

    def __init__(self, config: OccCommerceApiConfig | None = None):
        self._config = config or OccCommerceApiConfig(
            fields=os.getenv("OCC_FIELDS", DEFAULT_FIELDS),
            page_size=os.getenv("OCC_PAGE_SIZE", "12"),
            lang=os.getenv("OCC_LANG", "en"),
            curr=os.getenv("OCC_CURRENCY", "USD"),
        )
        self._client = httpx.Client(timeout=httpx.Timeout(30.0))

    def _require_base_site_id(self, destination: DestinationDetails) -> str:
        if not destination.base_site_id:
            raise RuntimeError(
                "base_site_id missing on destination; check OCC_BASE_SITE_ID in .env"
            )
        return destination.base_site_id

    def _headers(self, destination: DestinationDetails) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if destination.auth_header:
            headers["Authorization"] = destination.auth_header
        return headers

    def _search(self, destination: DestinationDetails, params: dict[str, str]) -> dict:
        base_site_id = self._require_base_site_id(destination)
        url = _join_url(destination.url, f"/occ/v2/{base_site_id}/products/search")

        print(f"URL: {url}")

        resp = self._client.get(url, params=params, headers=self._headers(destination))
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else {"value": data}

    def get_products(self, destination: DestinationDetails) -> dict:
        """Get products (unfiltered, first page) via OCC products/search.

        Args:
            destination (DestinationDetails): The details of the destination.

        Returns:
            dict: The products data.
        """
        params = {
            "fields": self._config.fields,
            "pageSize": self._config.page_size,
            "lang": self._config.lang,
            "curr": self._config.curr,
        }
        return self._search(destination, params)

    def get_categories(self, destination: DestinationDetails) -> dict:
        """Not supported in OCC mode.

        Raises:
            RuntimeError: Always — OCC has no stock "list all categories" endpoint.
        """
        raise RuntimeError(
            "get_categories is not supported in OCC mode. "
            "Switch BACKEND_MODE to 'BTP' or 'mock' to use this tool."
        )

    def get_products_by_category(self, destination: DestinationDetails, category_id: str) -> dict:
        """Get products filtered by category via OCC query=:relevance:category:{id}.

        Args:
            destination (DestinationDetails): The details of the destination.
            category_id (str): The ID of the category.

        Returns:
            dict: The products data.
        """
        params = {
            "fields": self._config.fields,
            "query": f":relevance:category:{category_id}",
            "pageSize": self._config.page_size,
            "lang": self._config.lang,
            "curr": self._config.curr,
        }
        return self._search(destination, params)

    def get_retailers(self, destination: DestinationDetails) -> dict:
        """Not supported in OCC mode.

        Raises:
            RuntimeError: Always — OCC has no stock "retailers/BusinessPartners" endpoint.
        """
        raise RuntimeError(
            "get_retailers is not supported in OCC mode. "
            "Switch BACKEND_MODE to 'BTP' or 'mock' to use this tool."
        )
