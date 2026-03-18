"""XSUAA Auth Middleware
Raises:
    RuntimeError: Raised if the XSUAA service is not found in the environment or 
    if there are issues with token validation.
Returns:
    Self: An instance of the XSUAAAuthMiddleware class that can be used 
    as ASGI middleware in a FastMCP application.
"""
from __future__ import annotations

import os

import jwt
from cfenv import AppEnv
from sap import xssec
from starlette.responses import JSONResponse


class XSUAAAuthMiddleware:
    """XSUAA Auth Middleware
    """
    def __init__(self, app):
        self.app = app
        env = AppEnv()
        xsuaa_service_name = os.getenv("XSUAA_SERVICE_NAME", "mcp-xsuaa-service")
        service = env.get_service(name=xsuaa_service_name)
        if service is None:
            raise RuntimeError(
                f"XSUAA service '{xsuaa_service_name}' not found. Check binding/service name."
            )
        self.uaa_service = service.credentials

        xsappname = self.uaa_service.get("xsappname")
        default_scope = f"{xsappname}.mcp" if isinstance(xsappname, str) and xsappname else "uaa.resource"
        self.scope = os.getenv("XSUAA_SCOPE", default_scope)

    async def __call__(self, scope, receive, send):
        """Handle incoming requests and perform XSUAA authentication.
           This is a bare minimum to just check the authentication and scope.

        Args:
            scope (dict): The ASGI scope dictionary.
            receive (Callable): The ASGI receive callable.
            send (Callable): The ASGI send callable.

        Returns:
            None
        """
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)

        path = scope.get("path") or ""
        if path == "/health":
            return await self.app(scope, receive, send)

        # Only protect MCP endpoint.
        if not path.startswith("/mcp"):
            return await self.app(scope, receive, send)

        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        if "authorization" not in headers:
            res = JSONResponse({"error": "missing_authorization"}, status_code=403)
            return await res(scope, receive, send)

        access_token = headers.get("authorization", "")[7:]

        print(jwt.decode(access_token, options={"verify_signature": False}))

        security_context = xssec.create_security_context(access_token, self.uaa_service)
        is_authorized = security_context.check_scope(self.scope)
        print(f"is_authorized: {is_authorized}")

        if not is_authorized:
            res = JSONResponse({"error": "forbidden"}, status_code=403)
            return await res(scope, receive, send)

        return await self.app(scope, receive, send)
