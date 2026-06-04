from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc(value: Any) -> pd.Timestamp | None:
    if value is None or value == "":
        return None
    parsed = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed


def parse_compact_utc(value: str) -> pd.Timestamp:
    return pd.to_datetime(value.upper(), format="%Y%m%dT%H%M%S", utc=True)
