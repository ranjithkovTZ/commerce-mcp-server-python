from __future__ import annotations

from dataclasses import dataclass

import httpx

from destination_auth import (
    DestinationServiceTokenProvider,
    load_destination_service_credentials,
)


@dataclass(frozen=True)
class DestinationDetails:
    """Details of a destination as returned by the Destination Service."""
    name: str
    url: str
    authentication: str | None
    auth_header: str | None
    username: str | None
    password: str | None


class DestinationServiceClient:
    """Small wrapper around the Destination Service REST API."""

    def __init__(self, *, destination_service_instance_name: str | None = None):
        creds = load_destination_service_credentials(destination_service_instance_name)
        self._base_uri = creds.uri.rstrip("/")
        self._token_provider = DestinationServiceTokenProvider(creds)

    def get_destination(self, destination_name: str) -> DestinationDetails:
        """Get the destination details

        Args:
            destination_name (str): Name of the destination.

        Raises:
            RuntimeError: If the destination details response is not an object.
            RuntimeError: If the destination details are missing the destinationConfiguration.
            RuntimeError: If the destination configuration is missing the URL.

        Returns:
            DestinationDetails: The details of the destination.
        """
        token = self._token_provider.get_access_token()

        url = f"{self._base_uri}/destination-configuration/v1/destinations/{destination_name}"
        resp = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=20.0)
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, dict):
            raise RuntimeError("Destination details response is not an object")

        dest_cfg = payload.get("destinationConfiguration")
        if not isinstance(dest_cfg, dict):
            raise RuntimeError("Destination details missing destinationConfiguration")

        dest_url = dest_cfg.get("URL")
        if not isinstance(dest_url, str) or not dest_url:
            raise RuntimeError("Destination configuration missing URL")

        authentication = dest_cfg.get("Authentication")
        authentication = authentication if isinstance(authentication, str) else None

        auth_header = None
        auth_tokens = payload.get("authTokens")
        if isinstance(auth_tokens, list) and auth_tokens:
            token0 = auth_tokens[0]
            if isinstance(token0, dict):
                token_type = token0.get("type")
                token_value = token0.get("value")
                if isinstance(token_type, str) and isinstance(token_value, str) and token_value:
                    auth_header = f"{token_type} {token_value}" if token_type else token_value

        username = dest_cfg.get("User") if isinstance(dest_cfg.get("ClientId"), str) else None
        password = dest_cfg.get("Password") if isinstance(dest_cfg.get("ClientSecret"), str) else None

        return DestinationDetails(
            name=destination_name,
            url=dest_url,
            authentication=authentication,
            auth_header=auth_header,
            username=username,
            password=password,
        )
