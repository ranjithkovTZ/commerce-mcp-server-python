"""This is the entry point for the MCP server"""
import os

from dataclasses import replace
from pathlib import Path
import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token
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

    if PORT:  # only need the interactive OAuth layer when serving HTTP
        from fastmcp.server.auth.providers.jwt import JWTVerifier
        from occ.occ_commerce_auth import load_occ_commerce_credentials
        from occ.occ_oauth_proxy import OccOAuthProxy

        _occ_creds = load_occ_commerce_credentials()
        _mcp_public_base_url = os.getenv("MCP_PUBLIC_BASE_URL", "").strip()
        if not _mcp_public_base_url:
            raise RuntimeError(
                "MCP_PUBLIC_BASE_URL is empty. When PORT is set in OCC mode, set it to this "
                "server's public base URL (e.g. your trycloudflare.com tunnel URL, or "
                "http://localhost:<PORT>) — it must match the impex $redirectUri minus "
                "'/occ/auth/callback'."
            )
        _allowed_redirect_uris = os.getenv("MCP_ALLOWED_CLIENT_REDIRECT_URIS", "").split(",") or None
        _allowed_redirect_uris = [u for u in (_allowed_redirect_uris or []) if u] or None

        mcp.auth = OccOAuthProxy(
            upstream_authorization_endpoint=f"{_occ_creds.base_url}/authorizationserver/oauth/authorize",
            upstream_token_endpoint=_occ_creds.token_url,
            # Reuses the same OCC OAuth client (OCC_CLIENT_ID/SECRET) already
            # used for the anonymous client_credentials flow — it's already
            # registered with the authorization_code grant type. See
            # resources/create_mcp_oauth_client.impex.
            upstream_client_id=_occ_creds.client_id,
            upstream_client_secret=_occ_creds.client_secret,
            # Confirmed against the dev tenant's OIDC discovery document
            # ({OCC_BASE_URL}/authorizationserver/.well-known/openid-configuration):
            # this Commerce instance runs on Spring Authorization Server and
            # issues RS256 JWTs with a real JWKS endpoint, so local signature
            # verification (no per-request network round trip) is used
            # instead of introspection or the legacy check_token endpoint.
            token_verifier=JWTVerifier(
                jwks_uri=f"{_occ_creds.base_url}/authorizationserver/oauth/jwks",
                issuer=f"{_occ_creds.base_url}/authorizationserver",
                audience=_occ_creds.client_id,
            ),
            base_url=_mcp_public_base_url,
            redirect_path="/occ/auth/callback",
            allowed_client_redirect_uris=_allowed_redirect_uris,
            # Live-tenant fact, not yet confirmed — default to terminating
            # PKCE at the proxy until OCC_SUPPORTS_PKCE=true is confirmed
            # against the real authorizationserver (see plan Section 6).
            forward_pkce=os.getenv("OCC_SUPPORTS_PKCE", "false").lower() == "true",
            token_endpoint_auth_method="client_secret_basic",
        )
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
    search: str | None = None,
    fields: str | None = None,
    page_size: int | None = None,
    lang: str | None = None,
    curr: str | None = None,
) -> dict:
    """Fetch products from the Commerce API.

    Args:
        search: Optional free-text search term (OCC mode only; ignored otherwise).
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
            destination, search=search, fields=fields, page_size=page_size, lang=lang, curr=curr
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
def get_product_details(
    product_code: str,
    fields: str | None = None,
    lang: str | None = None,
    curr: str | None = None,
) -> dict:
    """Fetch a single product's details (PDP) from the Commerce API.

    Args:
        product_code: The product code to fetch details for.
        fields: Optional OCC field selector override (OCC mode only; ignored otherwise).
        lang: Optional language code override (OCC mode only; ignored otherwise).
        curr: Optional currency code override (OCC mode only; ignored otherwise).

    Returns:
        dict: The product's details or error message.
    """
    if not product_code:
        return {
            "status": "error",
            "message": "Missing product_code. Provide product_code as an argument.",
        }

    try:
        if MOCK_BACKEND:
            data = _commerce_api.get_product_details(product_code=product_code)
            return {"status": "success", "destination": BackendMode.MOCK.value, "data": data}

        destination_name = os.getenv("DESTINATION_NAME") or "COMMERCE_API_DESTINATION"
        destination = _get_destination(destination_name)
        data = _commerce_api.get_product_details(
            destination, product_code, fields=fields, lang=lang, curr=curr
        )
        return {"status": "success", "destination": destination_name, "data": data}
    except (httpx.HTTPError, RuntimeError, ValueError, KeyError, TypeError) as e:
        return {"status": "error", "message": str(e)}


@mcp.tool
def get_product_stock(product_code: str) -> dict:
    """Fetch a single product's stock/availability details from the Commerce API.

    Args:
        product_code: The product code to check stock for.

    Returns:
        dict: The product's stock/availability details or error message.
    """
    if not product_code:
        return {
            "status": "error",
            "message": "Missing product_code. Provide product_code as an argument.",
        }

    try:
        if MOCK_BACKEND:
            data = _commerce_api.get_product_stock(product_code=product_code)
            return {"status": "success", "destination": BackendMode.MOCK.value, "data": data}

        destination_name = os.getenv("DESTINATION_NAME") or "COMMERCE_API_DESTINATION"
        destination = _get_destination(destination_name)
        data = _commerce_api.get_product_stock(destination, product_code)
        return {"status": "success", "destination": destination_name, "data": data}
    except (httpx.HTTPError, RuntimeError, ValueError, KeyError, TypeError) as e:
        return {"status": "error", "message": str(e)}


@mcp.tool
def get_customer_orders(
    email: str,
    fields: str | None = None,
    page_size: int | None = None,
    current_page: int | None = None,
    sort: str | None = None,
) -> dict:
    """Fetch a customer's order history from the Commerce API, authenticated
    as the CS agent currently logged in to this MCP server.

    NOTE (OCC mode): assumes this tenant's standard OOTB B2C convention that a
    customer's OCC userId equals their email address. If this tenant
    customizes login/uid, `email` will not resolve to the correct customer.

    Args:
        email: The customer's email address (used as OCC's userId).
        fields: Optional OCC field selector override (OCC mode only; ignored otherwise).
        page_size: Optional page size override (OCC mode only; ignored otherwise).
        current_page: Optional zero-based page index override (OCC mode only; ignored otherwise).
        sort: Optional OCC sort key override (OCC mode only; ignored otherwise).

    Returns:
        dict: The customer's order history or error message.
    """
    if not email:
        return {"status": "error", "message": "Missing email. Provide email as an argument."}

    try:
        if MOCK_BACKEND:
            data = _commerce_api.get_customer_orders(email=email)
            return {"status": "success", "destination": BackendMode.MOCK.value, "data": data}

        access_token = get_access_token()
        if access_token is None:
            return {
                "status": "error",
                "message": (
                    "No authenticated agent session found for this request; "
                    "cannot fetch customer orders without agent-level authorization."
                ),
            }
        agent_identity = access_token.claims.get("user_name") or access_token.claims.get("sub")
        print(f"get_customer_orders: agent={agent_identity!r} email={email!r}")

        destination_name = os.getenv("DESTINATION_NAME") or "COMMERCE_API_DESTINATION"
        destination = _get_destination(destination_name)
        # Swap in the agent's own OCC token — this call must run as the
        # specific agent, never under the service-level client_credentials
        # token every other tool in this file uses.
        agent_destination = replace(destination, auth_header=f"Bearer {access_token.token}")
        data = _commerce_api.get_customer_orders(
            agent_destination, email, fields=fields, page_size=page_size,
            current_page=current_page, sort=sort,
        )
        return {"status": "success", "destination": destination_name, "data": data}
    except (httpx.HTTPError, RuntimeError, ValueError, KeyError, TypeError) as e:
        return {"status": "error", "message": str(e)}


@mcp.tool
def get_order_details(email: str, order_id: str, fields: str | None = None) -> dict:
    """Fetch a single order's full details from the Commerce API, authenticated
    as the CS agent currently logged in to this MCP server.

    NOTE (OCC mode): assumes this tenant's standard OOTB B2C convention that a
    customer's OCC userId equals their email address. If this tenant
    customizes login/uid, `email` will not resolve to the correct customer.

    Args:
        email: The customer's email address (used as OCC's userId) that placed the order.
        order_id: The order code/ID to fetch details for.
        fields: Optional OCC field selector override (OCC mode only; ignored otherwise).

    Returns:
        dict: The order's details or error message.
    """
    if not email or not order_id:
        return {
            "status": "error",
            "message": "Missing email or order_id. Provide both as arguments.",
        }

    try:
        if MOCK_BACKEND:
            data = _commerce_api.get_order_details(email=email, order_id=order_id)
            return {"status": "success", "destination": BackendMode.MOCK.value, "data": data}

        access_token = get_access_token()
        if access_token is None:
            return {
                "status": "error",
                "message": (
                    "No authenticated agent session found for this request; "
                    "cannot fetch order details without agent-level authorization."
                ),
            }
        agent_identity = access_token.claims.get("user_name") or access_token.claims.get("sub")
        print(f"get_order_details: agent={agent_identity!r} email={email!r} order_id={order_id!r}")

        destination_name = os.getenv("DESTINATION_NAME") or "COMMERCE_API_DESTINATION"
        destination = _get_destination(destination_name)
        # Same as get_customer_orders: this call must run as the specific
        # agent, never under the service-level client_credentials token.
        agent_destination = replace(destination, auth_header=f"Bearer {access_token.token}")
        data = _commerce_api.get_order_details(agent_destination, email, order_id, fields=fields)
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
        # XSUAA gates the separate BTP-hosted deployment path; in OCC mode,
        # authentication is handled entirely by mcp.auth (OAuthProxy, wired
        # above) — stacking both would force every CS agent to also mint an
        # unrelated BTP token for no security benefit.
        extra_middleware = [Middleware(XSUAAAuthMiddleware)] if BACKEND_MODE == BackendMode.BTP else []
        mcp.run(
            transport="http",
            host="0.0.0.0",
            port=int(PORT),
            middleware=extra_middleware,
        )
    else:
        mcp.run()
