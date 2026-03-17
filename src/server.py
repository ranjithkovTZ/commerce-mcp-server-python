"""This is the entry point for the MCP server"""
import os
import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.responses import JSONResponse

load_dotenv()
PORT = os.getenv("PORT")

mcp = FastMCP("commerce-mcp-server")



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


if __name__ == "__main__":
    # Cloud Foundry sets $PORT; in that case run the MCP server over HTTP.
    # Locally (no $PORT), default to STDIO to work with `fastmcp dev` and MCP Inspector.
    if PORT:
        from starlette.middleware import Middleware
        from xsuaa_sec import XSUAAAuthMiddleware

        mcp.run(
            transport="http",
            host="0.0.0.0",
            port=int(PORT),
            middleware=[Middleware(XSUAAAuthMiddleware)],
        )
    else:
        mcp.run()
