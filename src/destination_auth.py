from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class DestinationServiceCredentials:
    uri: str
    clientid: str
    clientsecret: str
    token_service_url: str


class DestinationServiceTokenProvider:
    """Fetches an OAuth access token for calling the Destination Service REST API."""

    TOKEN_PATH = "/oauth/token"

    def __init__(self, credentials: DestinationServiceCredentials):
        self._creds = credentials

    def get_access_token(self) -> str:
        """Get access token

        Raises:
            RuntimeError: If the token request fails or the response is invalid.

        Returns:
            str: The access token.
        """
        token_url = self._creds.token_service_url.rstrip("/")
        if not token_url.endswith(self.TOKEN_PATH):
            token_url += self.TOKEN_PATH

        basic = base64.b64encode(
            f"{self._creds.clientid}:{self._creds.clientsecret}".encode("utf-8")
        ).decode("utf-8")

        headers = {
            "Authorization": f"Bearer {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"grant_type": "client_credentials"}

        resp = httpx.post(token_url, data=data, headers=headers, timeout=20.0)
        resp.raise_for_status()
        token = resp.json().get("access_token")
        if not isinstance(token, str) or not token:
            raise RuntimeError(
                "Destination service token response missing access_token"
            )
        return token


def _load_vcap_services() -> dict[str, Any]:
    raw = os.getenv("VCAP_SERVICES")
    if not raw:
        raise RuntimeError(
            "VCAP_SERVICES is not set (are you running on Cloud Foundry?)"
        )
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError("VCAP_SERVICES is not valid JSON") from e
    if not isinstance(parsed, dict):
        raise RuntimeError("VCAP_SERVICES JSON is not an object")
    return parsed


def load_destination_service_credentials(
    service_instance_name: str | None = None,
) -> DestinationServiceCredentials:
    """Loads bound Destination service credentials from VCAP_SERVICES.

    If service_instance_name is provided, selects the matching binding by its 
    CF service instance name. Otherwise, uses the first bound 'destination' service.
    """

    vcap = _load_vcap_services()
    dest_services = vcap.get("destination")
    if not isinstance(dest_services, list) or not dest_services:
        raise RuntimeError("No 'destination' service found in VCAP_SERVICES")

    selected: dict[str, Any] | None = None
    if service_instance_name:
        for entry in dest_services:
            if isinstance(entry, dict) and entry.get("name") == service_instance_name:
                selected = entry
                break
    if selected is None:
        selected = dest_services[0] if isinstance(dest_services[0], dict) else None

    if not isinstance(selected, dict):
        raise RuntimeError("Destination service binding has unexpected structure")

    creds = selected.get("credentials")
    if not isinstance(creds, dict):
        raise RuntimeError("Destination service binding missing credentials")

    uri = creds.get("uri")
    clientid = creds.get("clientid")
    clientsecret = creds.get("clientsecret")
    token_service_url = creds.get("url")

    if not all(
        isinstance(x, str) and x
        for x in [uri, clientid, clientsecret, token_service_url]
    ):
        raise RuntimeError(
            "Destination service credentials missing one of: " \
            "uri, clientid, clientsecret, token_service_url"
        )

    return DestinationServiceCredentials(
        uri=uri,
        clientid=clientid,
        clientsecret=clientsecret,
        token_service_url=token_service_url,
    )
