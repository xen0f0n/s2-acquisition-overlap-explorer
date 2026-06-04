from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import geopandas as gpd
import pandas as pd

from app.core.settings import settings


DATETIME_COLUMNS = [
    "start_time_utc",
    "stop_time_utc",
    "downloaded_at_utc",
    "plan_start_utc",
    "plan_stop_utc",
]


def _normalise_for_parquet(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    out = gdf.copy()
    for col in DATETIME_COLUMNS:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], utc=True, errors="coerce")
    if "metadata" in out.columns:
        out["metadata"] = out["metadata"].apply(lambda x: json.dumps(x or {}, ensure_ascii=False))
    return out


def _restore_from_parquet(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    out = gdf.copy()
    for col in DATETIME_COLUMNS:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], utc=True, errors="coerce")
    if "metadata" in out.columns:
        def load_metadata(value):
            if isinstance(value, dict):
                return value
            if not value:
                return {}
            try:
                return json.loads(value)
            except Exception:
                return {}
        out["metadata"] = out["metadata"].apply(load_metadata)
    return out


def read_acquisitions(path: Path | None = None) -> gpd.GeoDataFrame:
    path = path or settings.acquisitions_path
    if not path.exists():
        return gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs="EPSG:4326")
    gdf = gpd.read_parquet(path)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    return _restore_from_parquet(gdf)


def write_acquisitions(gdf: gpd.GeoDataFrame, path: Path | None = None) -> None:
    path = path or settings.acquisitions_path
    path.parent.mkdir(parents=True, exist_ok=True)
    out = _normalise_for_parquet(gdf)
    out.to_parquet(path, index=False)


def append_acquisitions(new_gdf: gpd.GeoDataFrame, path: Path | None = None) -> int:
    path = path or settings.acquisitions_path
    existing = read_acquisitions(path)

    if existing.empty:
        combined = new_gdf
    elif new_gdf.empty:
        combined = existing
    else:
        combined = pd.concat([existing, new_gdf], ignore_index=True)
        combined = gpd.GeoDataFrame(combined, geometry="geometry", crs="EPSG:4326")

    if not combined.empty and "acquisition_id" in combined.columns:
        before = len(combined)
        combined = combined.drop_duplicates(subset=["acquisition_id"], keep="last")
        added = len(combined) - len(existing.drop_duplicates(subset=["acquisition_id"], keep="last")) if not existing.empty else len(combined)
    else:
        added = len(new_gdf)

    write_acquisitions(combined, path)
    return max(0, added)


def filter_acquisitions(
    gdf: gpd.GeoDataFrame,
    satellites: Iterable[str] | None = None,
    modes: Iterable[str] | None = None,
    start: str | None = None,
    end: str | None = None,
) -> gpd.GeoDataFrame:
    if gdf.empty:
        return gdf

    out = gdf.copy()
    if satellites:
        sat_set = set(satellites)
        out = out[out["platform"].isin(sat_set)]

    if modes:
        mode_set = set(modes)
        out = out[out["mode"].isin(mode_set)]

    out["start_time_utc"] = pd.to_datetime(out["start_time_utc"], utc=True, errors="coerce")

    if start:
        start_ts = pd.to_datetime(start, utc=True, errors="coerce")
        if pd.notna(start_ts):
            out = out[out["start_time_utc"] >= start_ts]

    if end:
        end_ts = pd.to_datetime(end, utc=True, errors="coerce")
        if pd.notna(end_ts):
            out = out[out["start_time_utc"] <= end_ts]

    return gpd.GeoDataFrame(out, geometry="geometry", crs=gdf.crs or "EPSG:4326")
