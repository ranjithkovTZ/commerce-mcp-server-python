from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from backend_mode import BackendMode
from destination_details import DestinationDetails

_NOT_SUPPORTED_MESSAGE = (
    "{method} is not supported in OCC mode. "
    f"Switch BACKEND_MODE to '{BackendMode.BTP.value}' or '{BackendMode.MOCK.value}' to use this tool."
)

DEFAULT_FIELDS = (
    "products(code,name,summary,configurable,configuratorType,multidimensional,"
    "price(FULL),images(DEFAULT),stock(FULL),averageRating,variantOptions,baseProduct,"
    "priceRange(maxPrice(formattedValue),minPrice(formattedValue))),"
    "facets,breadcrumbs,pagination(DEFAULT),sorts(DEFAULT),freeTextSearch,"
    "currentQuery,keywordRedirectUrl"
)


def _join_url(base: str, path: str) -> str:
    return base.rstrip("/") + "/" + path.lstrip("/")


def _absolutize_image_urls(node, base_url: str) -> None:
    """Recursively rewrite OCC image DTO 'url' fields in place.

    OCC always returns media URLs relative to the commerce instance (e.g.
    "/medias/xxx.jpg?context=...") regardless of which endpoint or field
    selector produced them — the media host is allowed to differ from the
    API host, so the client is expected to resolve it. Walk the whole
    response tree rather than a fixed path, since images show up at
    varying depths (product.images, variantOptions[].images,
    baseProduct.images, galleryImages, ...) and new OCC field selectors
    will keep following the same shape.
    """
    if isinstance(node, dict):
        url = node.get("url")
        if isinstance(url, str) and url.startswith("/") and ("format" in node or "imageType" in node):
            node["url"] = _join_url(base_url, url)
        for value in node.values():
            _absolutize_image_urls(value, base_url)
    elif isinstance(node, list):
        for item in node:
            _absolutize_image_urls(item, base_url)


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
        # os.getenv(key, default) only falls back when the var is fully unset,
        # not when it's present-but-empty (which is exactly how .env-template
        # ships these optional vars) — use `or` so a blank value falls back too.
        self._config = config or OccCommerceApiConfig(
            fields=os.getenv("OCC_FIELDS") or DEFAULT_FIELDS,
            page_size=os.getenv("OCC_PAGE_SIZE") or "12",
            lang=os.getenv("OCC_LANG") or "en",
            curr=os.getenv("OCC_CURRENCY") or "USD",
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
        data = data if isinstance(data, dict) else {"value": data}
        _absolutize_image_urls(data, destination.url)
        return data

    def _resolve_params(
        self,
        fields: str | None,
        page_size: int | str | None,
        lang: str | None,
        curr: str | None,
    ) -> dict[str, str]:
        """Resolve caller-supplied overrides against this instance's configured
        defaults (OCC_FIELDS/OCC_PAGE_SIZE/OCC_LANG/OCC_CURRENCY). Callers only
        need to pass what they want to override — everything else falls back
        to the config already resolved at construction time."""
        return {
            "fields": fields if fields is not None else self._config.fields,
            "pageSize": str(page_size) if page_size is not None else self._config.page_size,
            "lang": lang if lang is not None else self._config.lang,
            "curr": curr if curr is not None else self._config.curr,
        }

    def get_products(
        self,
        destination: DestinationDetails,
        *,
        search: str | None = None,
        fields: str | None = None,
        page_size: int | str | None = None,
        lang: str | None = None,
        curr: str | None = None,
    ) -> dict:
        """Get products via OCC products/search — free-text search if `search`
        is given, otherwise an unfiltered listing (one page).

        Args:
            destination (DestinationDetails): The details of the destination.
            search (str | None): Optional free-text search term.
            fields (str | None): Optional OCC field selector override.
            page_size (int | str | None): Optional page size override.
            lang (str | None): Optional language code override.
            curr (str | None): Optional currency code override.

        Returns:
            dict: The products data.
        """
        params = self._resolve_params(fields, page_size, lang, curr)
        if search:
            params["query"] = f"{search}:relevance"
        return self._search(destination, params)

    def get_categories(self, destination: DestinationDetails) -> dict:
        """Not supported in OCC mode.

        Raises:
            RuntimeError: Always — OCC has no stock "list all categories" endpoint.
        """
        raise RuntimeError(_NOT_SUPPORTED_MESSAGE.format(method="get_categories"))

    def get_products_by_category(
        self,
        destination: DestinationDetails,
        category_id: str,
        *,
        fields: str | None = None,
        page_size: int | str | None = None,
        lang: str | None = None,
        curr: str | None = None,
    ) -> dict:
        """Get products filtered by category via OCC query=:relevance:category:{id}.

        Args:
            destination (DestinationDetails): The details of the destination.
            category_id (str): The ID of the category.
            fields (str | None): Optional OCC field selector override.
            page_size (int | str | None): Optional page size override.
            lang (str | None): Optional language code override.
            curr (str | None): Optional currency code override.

        Returns:
            dict: The products data.
        """
        params = self._resolve_params(fields, page_size, lang, curr)
        params["query"] = f":relevance:category:{category_id}"
        return self._search(destination, params)

    def get_retailers(self, destination: DestinationDetails) -> dict:
        """Not supported in OCC mode.

        Raises:
            RuntimeError: Always — OCC has no stock "retailers/BusinessPartners" endpoint.
        """
        raise RuntimeError(_NOT_SUPPORTED_MESSAGE.format(method="get_retailers"))
