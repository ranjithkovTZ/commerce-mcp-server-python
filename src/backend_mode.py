from __future__ import annotations

from enum import StrEnum


class BackendMode(StrEnum):
    """Which Commerce backend the server talks to, selected via BACKEND_MODE."""
    MOCK = "mock"
    BTP = "btp"
    OCC = "occ"
