from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DestinationDetails:
    """Details of how to reach + auth a Commerce backend, regardless of which
    BACKEND_MODE produced them (BTP, OCC, or otherwise)."""
    name: str
    url: str
    authentication: str | None
    auth_header: str | None
    username: str | None
    password: str | None
    base_site_id: str | None = None  # only populated by OCC mode
