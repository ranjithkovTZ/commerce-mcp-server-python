"""This is the entry point for the MCP server"""
import os

from pathlib import Path
import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.responses import JSONResponse
from starlette.middleware import Middleware
from xsuaa_sec import XSUAAAuthMiddleware

from commerce_api import CommerceApi
from destination_client import DestinationServiceClient

load_dotenv()
PORT = os.getenv("PORT")
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

if ENVIRONMENT == "local":
    p = Path(os.getenv("VCAP_SERVICES_FILE", "vcap.json"))
    if p.exists():
        os.environ["VCAP_SERVICES"] = p.read_text(encoding="utf-8")


mcp = FastMCP("commerce-mcp-server")

_destination_client = DestinationServiceClient(
    destination_service_instance_name=os.getenv("DESTINATION_SERVICE_INSTANCE_NAME")
)
_commerce_api = CommerceApi()



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
def get_products(destination_name: str | None = None) -> dict:
    """Fetch products from the Commerce API via a BTP Destination.

    Args:
        destination_name: Name of the Destination in the subaccount.
    """

    destination_name = destination_name or os.getenv("DESTINATION_NAME")
    if not destination_name:
        return {
            "status": "error",
            "message": "Missing destination name. Provide destination_name or set DESTINATION_NAME.",
        }

    try:
        destination = _destination_client.get_destination(destination_name)
        data = _commerce_api.get_products(destination)
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
