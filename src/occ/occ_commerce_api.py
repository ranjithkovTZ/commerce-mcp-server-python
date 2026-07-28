from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

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

# The single-product endpoint returns one ProductWsDTO (not a search results
# envelope), so it uses OCC's flat BASIC/DEFAULT/FULL field-level aliases
# rather than the nested "products(...)" shape above.
DEFAULT_PRODUCT_FIELDS = "FULL"


def _join_url(base: str, path: str) -> str:
    return base.rstrip("/") + "/" + path.lstrip("/")


def _absolutize_urls(node, *, media_base_url: str, website_base_url: str) -> None:
    """Recursively rewrite every OCC 'url' field in place to an absolute URL.

    OCC returns every host-relative link (media DTOs like "/medias/xxx.jpg",
    a product's own PDP link like "/Open-Catalogue/.../p/{code}", category
    redirect links, ...) relative to the commerce instance, regardless of
    which endpoint or field selector produced them — the client is expected
    to resolve them itself. Media URLs resolve against the OCC API host
    (media DTOs are recognizable by their "format"/"imageType" siblings);
    everything else (product/category/other navigational links) resolves
    against the storefront host instead, since that's the site a customer
    would actually be redirected to — the two hosts are not guaranteed to
    be the same. Walk the whole response tree rather than a fixed path,
    since these show up at varying depths (product.images,
    product.categories, variantOptions[].images, baseProduct.images, ...)
    and new OCC field selectors will keep following the same shape.
    """
    if isinstance(node, dict):
        url = node.get("url")
        if isinstance(url, str) and url.startswith("/"):
            is_media = "format" in node or "imageType" in node
            node["url"] = _join_url(media_base_url if is_media else website_base_url, url)
        for value in node.values():
            _absolutize_urls(value, media_base_url=media_base_url, website_base_url=website_base_url)
    elif isinstance(node, list):
        for item in node:
            _absolutize_urls(item, media_base_url=media_base_url, website_base_url=website_base_url)


@dataclass(frozen=True)
class OccCommerceApiConfig:
    """API paths and search defaults for SAP Commerce Cloud's OCC v2 API."""
    fields: str = DEFAULT_FIELDS
    page_size: str = "12"
    lang: str = "en"
    curr: str = "USD"
    product_fields: str = DEFAULT_PRODUCT_FIELDS


class OccCommerceApi:
    """Commerce API that calls SAP Commerce Cloud's native OCC (v2) REST API."""

    def __init__(self, config: OccCommerceApiConfig | None = None):
        self._config = config or OccCommerceApiConfig()
        self._client = httpx.Client(timeout=httpx.Timeout(30.0))

    def _require_base_site_id(self, destination: DestinationDetails) -> str:
        if not destination.base_site_id:
            raise RuntimeError(
                "base_site_id missing on destination; check OCC_BASE_SITE_ID in .env"
            )
        return destination.base_site_id

    def _require_website_url(self, destination: DestinationDetails) -> str:
        if not destination.website_url:
            raise RuntimeError(
                "website_url missing on destination; check WEBSITE_URL in .env"
            )
        return destination.website_url

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
        _absolutize_urls(
            data,
            media_base_url=destination.url,
            website_base_url=self._require_website_url(destination),
        )
        return data

    def _get_product(
        self, destination: DestinationDetails, product_code: str, params: dict[str, str]
    ) -> dict:
        base_site_id = self._require_base_site_id(destination)
        # product_code goes into the URL path (not a query param), so it needs
        # explicit escaping — httpx only escapes query param values, not paths.
        url = _join_url(
            destination.url, f"/occ/v2/{base_site_id}/products/{quote(str(product_code), safe='')}"
        )

        print(f"URL: {url}")

        resp = self._client.get(url, params=params, headers=self._headers(destination))
        resp.raise_for_status()
        data = resp.json()
        data = data if isinstance(data, dict) else {"value": data}
        _absolutize_urls(
            data,
            media_base_url=destination.url,
            website_base_url=self._require_website_url(destination),
        )
        return data

    def _get_unit_code(self, destination: DestinationDetails, product_code: str) -> str:
        data = self._get_product(destination, product_code, {"fields": "code,sapUnit"})
        unit_code = data.get("sapUnit", {}).get("code")
        if not unit_code:
            raise RuntimeError(f"Product '{product_code}' has no sapUnit; cannot resolve stock availability.")
        return unit_code

    def _stock_availability(
        self, destination: DestinationDetails, product_code: str, unit_code: str
    ) -> dict:
        base_site_id = self._require_base_site_id(destination)
        url = _join_url(destination.url, f"/occ/v2/{base_site_id}/productAvailabilities")

        print(f"URL: {url}")

        resp = self._client.get(
            url,
            params={"filters": f"{product_code}:{unit_code}"},
            headers=self._headers(destination),
        )
        resp.raise_for_status()
        items = resp.json().get("availabilityItems") or []
        if not items:
            raise ValueError(f"No stock availability found for product_code '{product_code}'.")
        return items[0]

    def _resolve_params(
        self,
        fields: str | None,
        page_size: int | str | None,
        lang: str | None,
        curr: str | None,
    ) -> dict[str, str]:
        """Resolve caller-supplied overrides against this instance's built-in
        defaults (DEFAULT_FIELDS, page size 12, lang "en", curr "USD"). Callers
        only need to pass what they want to override for a given call."""
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

    def get_product_details(
        self,
        destination: DestinationDetails,
        product_code: str,
        *,
        fields: str | None = None,
        lang: str | None = None,
        curr: str | None = None,
    ) -> dict:
        """Get a single product's details (PDP) via OCC GET /products/{productCode}.

        Args:
            destination (DestinationDetails): The details of the destination.
            product_code (str): The product code (OCC `code`) to fetch.
            fields (str | None): Optional OCC field selector override (defaults to FULL).
            lang (str | None): Optional language code override.
            curr (str | None): Optional currency code override.

        Returns:
            dict: The single product's details.
        """
        # No pageSize/query here — unlike _resolve_params, this endpoint returns
        # one ProductWsDTO, not a paged search result.
        params = {
            "fields": fields if fields is not None else self._config.product_fields,
            "lang": lang if lang is not None else self._config.lang,
            "curr": curr if curr is not None else self._config.curr,
        }
        return self._get_product(destination, product_code, params)

    def get_product_stock(self, destination: DestinationDetails, product_code: str) -> dict:
        """Get a single product's real-time stock/availability via OCC's OOTB
        GET /productAvailabilities?filters={productCode}:{unitCode} endpoint.

        Args:
            destination (DestinationDetails): The details of the destination.
            product_code (str): The product code to check stock for.

        Returns:
            dict: The single product's availability item
                ({"productCode": ..., "unitAvailabilities": [...]}).
        """
        unit_code = self._get_unit_code(destination, product_code)
        return self._stock_availability(destination, product_code, unit_code)

    def get_retailers(self, destination: DestinationDetails) -> dict:
        """Not supported in OCC mode.

        Raises:
            RuntimeError: Always — OCC has no stock "retailers/BusinessPartners" endpoint.
        """
        raise RuntimeError(_NOT_SUPPORTED_MESSAGE.format(method="get_retailers"))
