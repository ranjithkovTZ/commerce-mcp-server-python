"""This is the entry point for the MCP server"""
import os

from pathlib import Path
import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.responses import JSONResponse
from starlette.middleware import Middleware
from xsuaa_sec import XSUAAAuthMiddleware

from backend_mode import BackendMode
from btp.BtpCommerce_api import CommerceApi
from btp.BtpCommerce_client import DestinationServiceClient

load_dotenv()
PORT = os.getenv("PORT")
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
_raw_backend_mode = os.getenv("BACKEND_MODE", BackendMode.BTP.value).strip().lower()
try:
    BACKEND_MODE = BackendMode(_raw_backend_mode)
except ValueError as e:
    valid = ", ".join(m.value for m in BackendMode)
    raise RuntimeError(f"Invalid BACKEND_MODE '{_raw_backend_mode}'. Must be one of: {valid}.") from e
# Internal derived flag only — lets the existing @mcp.tool bodies (which branch
# on MOCK_BACKEND) stay byte-for-byte unchanged.
MOCK_BACKEND = BACKEND_MODE == BackendMode.MOCK

if ENVIRONMENT == "local":
    p = Path(os.getenv("VCAP_SERVICES_FILE", "vcap.json"))
    if p.exists():
        os.environ["VCAP_SERVICES"] = p.read_text(encoding="utf-8")


mcp = FastMCP("commerce-mcp-server")

_backend_client = None

if BACKEND_MODE == BackendMode.MOCK:
    from mock.mock_commerce_api import MockCommerceApi
    _commerce_api = MockCommerceApi()
elif BACKEND_MODE == BackendMode.OCC:
    from occ.occ_commerce_client import OccCommerceClient
    from occ.occ_commerce_api import OccCommerceApi
    _backend_client = OccCommerceClient()
    _commerce_api = OccCommerceApi()
else:  # BackendMode.BTP
    _backend_client = DestinationServiceClient(
        destination_service_instance_name=os.getenv("DESTINATION_SERVICE_INSTANCE_NAME")
    )
    _commerce_api = CommerceApi()


def _get_destination(destination_name: str):
    return _backend_client.get_destination(destination_name)


@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health_check(_request):
    """Health check endpoint.

    Returns:
        JSONResponse: A JSON response indicating the health status.
    """
    return JSONResponse({"status": "ok"})


@mcp.tool
def mcp_ping() -> dict:
    """Ping the MCP service to check if it's reachable."""
    try:
        return {"status": "success", "message": "MCP service is reachable."}
    except httpx.RequestError as e:
        return {"status": "error", "message": f"MCP service is not reachable: {str(e)}"}


@mcp.tool
def get_products(
    fields: str | None = None,
    page_size: int | None = None,
    lang: str | None = None,
    curr: str | None = None,
) -> dict:
    """Fetch products from the Commerce API.

    Args:
        fields: Optional OCC field selector override (OCC mode only; ignored otherwise).
        page_size: Optional page size override (OCC mode only; ignored otherwise).
        lang: Optional language code override (OCC mode only; ignored otherwise).
        curr: Optional currency code override (OCC mode only; ignored otherwise).

    Returns:
        dict: List of products or error message.
    """
    try:
        if MOCK_BACKEND:
            data = _commerce_api.get_products()
            return {"status": "success", "destination": BackendMode.MOCK.value, "data": data}

        destination_name = os.getenv("DESTINATION_NAME") or "COMMERCE_API_DESTINATION"
        destination = _get_destination(destination_name)
        data = _commerce_api.get_products(
            destination, fields=fields, page_size=page_size, lang=lang, curr=curr
        )
        return {"status": "success", "destination": destination_name, "data": data}
    except (httpx.HTTPError, RuntimeError, ValueError, KeyError, TypeError) as e:
        return {"status": "error", "message": str(e)}


@mcp.tool
def get_categories() -> dict:
    """Fetch categories from the Commerce API.

    Returns:
        dict: List of categories or error message.
    """
    try:
        if MOCK_BACKEND:
            data = _commerce_api.get_categories()
            return {"status": "success", "destination": BackendMode.MOCK.value, "data": data}

        destination_name = os.getenv("DESTINATION_NAME") or "COMMERCE_API_DESTINATION"
        destination = _get_destination(destination_name)
        data = _commerce_api.get_categories(destination)
        return {"status": "success", "destination": destination_name, "data": data}
    except (httpx.HTTPError, RuntimeError, ValueError, KeyError, TypeError) as e:
        return {"status": "error", "message": str(e)}


@mcp.tool
def get_products_by_category(
    category_id: str,
    fields: str | None = None,
    page_size: int | None = None,
    lang: str | None = None,
    curr: str | None = None,
) -> dict:
    """Fetch products by category from the Commerce API.

    Args:
        category_id: The ID of the category to filter products by.
        fields: Optional OCC field selector override (OCC mode only; ignored otherwise).
        page_size: Optional page size override (OCC mode only; ignored otherwise).
        lang: Optional language code override (OCC mode only; ignored otherwise).
        curr: Optional currency code override (OCC mode only; ignored otherwise).
    """
    if not category_id:
        return {
            "status": "error",
            "message": "Missing category_id. Provide category_id as an argument.",
        }

    try:
        if MOCK_BACKEND:
            data = _commerce_api.get_products_by_category(category_id=category_id)
            return {"status": "success", "destination": BackendMode.MOCK.value, "data": data}

        destination_name = os.getenv("DESTINATION_NAME") or "COMMERCE_API_DESTINATION"
        destination = _get_destination(destination_name)
        data = _commerce_api.get_products_by_category(
            destination, category_id, fields=fields, page_size=page_size, lang=lang, curr=curr
        )
        return {"status": "success", "destination": destination_name, "data": data}
    except (httpx.HTTPError, RuntimeError, ValueError, KeyError, TypeError) as e:
        return {"status": "error", "message": str(e)}


@mcp.tool
def get_retailers() -> dict:
    """Fetch the retailers.

    Returns:
        dict: List of retailers or error message.
    """
    try:
        if MOCK_BACKEND:
            data = _commerce_api.get_retailers()
            return {"status": "success", "destination": BackendMode.MOCK.value, "data": data}

        destination_name = os.getenv("DESTINATION_NAME") or "COMMERCE_API_DESTINATION"
        destination = _get_destination(destination_name)
        data = _commerce_api.get_retailers(destination)
        return {"status": "success", "destination": destination_name, "data": data}
    except (httpx.HTTPError, RuntimeError, ValueError, KeyError, TypeError) as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    if PORT:
        mcp.run(
            transport="http",
            host="0.0.0.0",
            port=int(PORT),
            middleware=[Middleware(XSUAAAuthMiddleware)],
        )
    else:
        mcp.run()
