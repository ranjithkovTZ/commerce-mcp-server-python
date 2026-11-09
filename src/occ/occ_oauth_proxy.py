"""OAuthProxy variant for OCC's authorizationserver.

Confirmed via a live browser-login attempt against the dev tenant (2026-07-28):
OCC's Spring Authorization Server rejects the RFC 8707 "resource" indicator
parameter that MCP clients (Claude Desktop) include in the /authorize
request, with `invalid_request: Not supported parameter: resource`. OCC's
server validates parameters strictly rather than ignoring unrecognized ones.

fastmcp's OAuthProxy has no public option to omit this parameter -- it's
unconditionally forwarded whenever the client supplied one (see
_build_upstream_authorize_url in fastmcp/server/auth/oauth_proxy.py). That
method is a single-underscore (subclass-overridable) method, so this
overrides just that one step rather than duplicating the rest of its URL
construction.
"""
from __future__ import annotations

from typing import Any

from fastmcp.server.auth import OAuthProxy


class OccOAuthProxy(OAuthProxy):
    """OAuthProxy that never forwards the resource indicator to OCC."""

    def _build_upstream_authorize_url(self, txn_id: str, transaction: dict[str, Any]) -> str:
        transaction = {k: v for k, v in transaction.items() if k != "resource"}
        return super()._build_upstream_authorize_url(txn_id, transaction)
