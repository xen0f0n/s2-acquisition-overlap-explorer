from __future__ import annotations

import json
from typing import Any

import geopandas as gpd
import pandas as pd


DATETIME_COLUMNS = {
    "start_time_utc",
    "stop_time_utc",
    "plan_start_utc",
    "plan_stop_utc",
    "downloaded_at_utc",
    "start_time_a",
    "start_time_b",
    "start_time_c",
    "stop_time_a",
    "stop_time_b",
    "stop_time_c",
}


def gdf_to_geojson_dict(gdf: gpd.GeoDataFrame) -> dict[str, Any]:
    """Return a JSON-safe GeoJSON FeatureCollection from a GeoDataFrame."""
    if gdf.empty:
        return {"type": "FeatureCollection", "features": []}

    safe = gdf.copy()

    for col in safe.columns:
        if col in DATETIME_COLUMNS or pd.api.types.is_datetime64_any_dtype(safe[col]):
            safe[col] = pd.to_datetime(safe[col], utc=True, errors="coerce").dt.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

    safe = safe.where(pd.notnull(safe), None)
    return json.loads(safe.to_json())
