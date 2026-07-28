from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass

import httpx

DEFAULT_TOKEN_EXPIRY_SECONDS = 300
TOKEN_EXPIRY_SAFETY_MARGIN_SECONDS = 30
# OCC's OAuth2 token endpoint always lives at this path under the tenant's base
# URL — not independently configurable, so there's no separate OCC_TOKEN_URL var.
TOKEN_PATH = "/authorizationserver/oauth/token"


@dataclass(frozen=True, kw_only=True)
class OccCommerceCredentials:
    """Credentials for calling SAP Commerce Cloud's OCC API directly (no BTP)."""
    base_url: str
    token_url: str
    client_id: str
    client_secret: str
    base_site_id: str
    website_url: str
    scope: str | None = None


class OccCommerceTokenProvider:
    """Fetches (and caches) an OAuth2 client_credentials access token for the OCC API."""

    def __init__(self, credentials: OccCommerceCredentials):
        self._creds = credentials
        self._client = httpx.Client(timeout=20.0)
        self._cached_token: str | None = None
        self._expires_at: float | None = None

    def get_access_token(self) -> str:
        """Get access token, reusing a cached one until it's near expiry.

        Raises:
            RuntimeError: If the token request fails or the response is invalid.

        Returns:
            str: The access token.
        """
        now = time.monotonic()
        if (
            self._cached_token is not None
            and self._expires_at is not None
            and now < self._expires_at - TOKEN_EXPIRY_SAFETY_MARGIN_SECONDS
        ):
            return self._cached_token

        basic = base64.b64encode(
            f"{self._creds.client_id}:{self._creds.client_secret}".encode("utf-8")
        ).decode("utf-8")

        headers = {
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        data = {"grant_type": "client_credentials"}
        if self._creds.scope:
            data["scope"] = self._creds.scope

        resp = self._client.post(self._creds.token_url, data=data, headers=headers)
        if resp.is_error:
            # httpx's default HTTPStatusError message omits the response body,
            # which is where the OAuth server's actual error (e.g. invalid_client,
            # invalid_scope) lives — surface it so failures are diagnosable.
            raise RuntimeError(
                f"OCC token request failed ({resp.status_code}): {resp.text}"
            )
        payload = resp.json()
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise RuntimeError("OCC commerce token response missing access_token")

        expires_in = payload.get("expires_in")
        if not isinstance(expires_in, (int, float)) or expires_in <= 0:
            expires_in = DEFAULT_TOKEN_EXPIRY_SECONDS

        self._cached_token = token
        self._expires_at = now + expires_in
        return token


def load_occ_commerce_credentials() -> OccCommerceCredentials:
    """Loads OCC-mode Commerce credentials from environment variables.

    Raises:
        RuntimeError: If any required environment variable is missing or empty.
    """
    required = {
        "base_url": "OCC_BASE_URL",
        "client_id": "OCC_CLIENT_ID",
        "client_secret": "OCC_CLIENT_SECRET",
        "base_site_id": "OCC_BASE_SITE_ID",
        "website_url": "WEBSITE_URL",
    }
    values: dict[str, str] = {}
    missing: list[str] = []
    for field, env_var in required.items():
        value = os.getenv(env_var)
        if not value:
            missing.append(env_var)
        else:
            values[field] = value

    if missing:
        raise RuntimeError(
            f"Missing required environment variable(s) for OCC mode: {', '.join(missing)}"
        )

    scope = os.getenv("OCC_SCOPE")
    scope = scope if scope else None

    base_url = values["base_url"].rstrip("/")

    return OccCommerceCredentials(
        base_url=base_url,
        token_url=f"{base_url}{TOKEN_PATH}",
        client_id=values["client_id"],
        client_secret=values["client_secret"],
        base_site_id=values["base_site_id"],
        website_url=values["website_url"].rstrip("/"),
        scope=scope,
    )
