from __future__ import annotations

from itertools import combinations

import geopandas as gpd
import pandas as pd
from shapely import make_valid

EQUAL_AREA_CRS = "EPSG:6933"


def _safe_intersection(a, b):
    try:
        geom = make_valid(a).intersection(make_valid(b))
        if geom.is_empty:
            return None
        return make_valid(geom)
    except Exception:
        return None


def _add_area_km2(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    out = gdf.copy()
    if out.empty:
        out["intersection_area_km2"] = []
        return out
    equal_area = out.to_crs(EQUAL_AREA_CRS)
    out["intersection_area_km2"] = equal_area.geometry.area / 1_000_000.0
    return out


def compute_pairwise_overlaps(
    acquisitions: gpd.GeoDataFrame,
    satellites: list[str],
    max_delta_minutes: float,
    require_spatial_intersection: bool = True,
    min_intersection_area_km2: float = 0.0,
    return_intersection_geometry: bool = True,
) -> gpd.GeoDataFrame:
    if acquisitions.empty or len(satellites) < 2:
        return gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs="EPSG:4326")

    threshold = pd.Timedelta(minutes=float(max_delta_minutes))
    gdf = acquisitions.copy()
    gdf["start_time_utc"] = pd.to_datetime(gdf["start_time_utc"], utc=True, errors="coerce")
    gdf = gdf[gdf["start_time_utc"].notna()]

    records: list[dict] = []

    for sat_a, sat_b in combinations(satellites, 2):
        left = gdf[gdf["platform"] == sat_a].copy()
        right = gdf[gdf["platform"] == sat_b].copy()

        if left.empty or right.empty:
            continue

        right = right.sort_values("start_time_utc")
        right_sindex = right.sindex if require_spatial_intersection else None

        for _, a in left.iterrows():
            time_mask = (right["start_time_utc"] >= a["start_time_utc"] - threshold) & (
                right["start_time_utc"] <= a["start_time_utc"] + threshold
            )
            temporal_candidates = right[time_mask]
            if temporal_candidates.empty:
                continue

            if require_spatial_intersection and right_sindex is not None:
                candidate_positions = right_sindex.query(a.geometry, predicate="intersects")
                spatial_candidates = right.iloc[candidate_positions]
                candidates = temporal_candidates.loc[
                    temporal_candidates.index.intersection(spatial_candidates.index)
                ]
            else:
                candidates = temporal_candidates

            for _, b in candidates.iterrows():
                delta = abs(a["start_time_utc"] - b["start_time_utc"])

                if require_spatial_intersection:
                    intersection = _safe_intersection(a.geometry, b.geometry)
                    if intersection is None:
                        continue
                    output_geometry = intersection if return_intersection_geometry else a.geometry
                else:
                    intersection = None
                    output_geometry = a.geometry

                records.append(
                    {
                        "feature_type": "intersection" if require_spatial_intersection else "temporal_match",
                        "match_id": f"{a['acquisition_id']}__{b['acquisition_id']}",
                        "platform_a": sat_a,
                        "platform_b": sat_b,
                        "platforms": f"{sat_a},{sat_b}",
                        "acquisition_id_a": a.get("acquisition_id"),
                        "acquisition_id_b": b.get("acquisition_id"),
                        "start_time_a": a.get("start_time_utc"),
                        "start_time_b": b.get("start_time_utc"),
                        "stop_time_a": a.get("stop_time_utc"),
                        "stop_time_b": b.get("stop_time_utc"),
                        "time_delta_minutes": delta.total_seconds() / 60.0,
                        "mode_a": a.get("mode"),
                        "mode_b": b.get("mode"),
                        "source_kml_a": a.get("source_kml"),
                        "source_kml_b": b.get("source_kml"),
                        "name_a": a.get("name"),
                        "name_b": b.get("name"),
                        "geometry": output_geometry,
                    }
                )

    if not records:
        return gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs=acquisitions.crs or "EPSG:4326")

    out = gpd.GeoDataFrame(records, geometry="geometry", crs=acquisitions.crs or "EPSG:4326")
    out = _add_area_km2(out)

    if require_spatial_intersection and min_intersection_area_km2 > 0 and not out.empty:
        out = out[out["intersection_area_km2"] >= float(min_intersection_area_km2)]

    if not out.empty:
        out = out.sort_values(["time_delta_minutes", "intersection_area_km2"], ascending=[True, False])

    return out


def compute_triple_overlaps(
    acquisitions: gpd.GeoDataFrame,
    satellites: list[str],
    max_delta_minutes: float,
    require_spatial_intersection: bool = True,
    min_intersection_area_km2: float = 0.0,
    return_intersection_geometry: bool = True,
) -> gpd.GeoDataFrame:
    """Find true 3-way S2A/S2B/S2C matches.

    A triple match means:
    - exactly three distinct selected platforms are present;
    - the max pairwise start-time span across the three acquisitions is <= threshold;
    - if spatial intersection is required, the common intersection A ∩ B ∩ C is non-empty.
    """
    unique_satellites = list(dict.fromkeys(satellites))
    if acquisitions.empty or len(unique_satellites) != 3:
        return gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs=acquisitions.crs or "EPSG:4326")

    threshold = pd.Timedelta(minutes=float(max_delta_minutes))
    gdf = acquisitions.copy()
    gdf["start_time_utc"] = pd.to_datetime(gdf["start_time_utc"], utc=True, errors="coerce")
    gdf = gdf[gdf["start_time_utc"].notna()]

    frames = {sat: gdf[gdf["platform"] == sat].copy().sort_values("start_time_utc") for sat in unique_satellites}
    if any(frame.empty for frame in frames.values()):
        return gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs=acquisitions.crs or "EPSG:4326")

    sat_a, sat_b, sat_c = unique_satellites
    left = frames[sat_a]
    mid = frames[sat_b]
    right = frames[sat_c]

    mid_sindex = mid.sindex if require_spatial_intersection else None
    right_sindex = right.sindex if require_spatial_intersection else None

    records: list[dict] = []

    for _, a in left.iterrows():
        time_min = a["start_time_utc"] - threshold
        time_max = a["start_time_utc"] + threshold

        b_candidates = mid[(mid["start_time_utc"] >= time_min) & (mid["start_time_utc"] <= time_max)]
        c_candidates = right[(right["start_time_utc"] >= time_min) & (right["start_time_utc"] <= time_max)]

        if b_candidates.empty or c_candidates.empty:
            continue

        if require_spatial_intersection and mid_sindex is not None and right_sindex is not None:
            b_spatial = mid.iloc[mid_sindex.query(a.geometry, predicate="intersects")]
            c_spatial = right.iloc[right_sindex.query(a.geometry, predicate="intersects")]
            b_candidates = b_candidates.loc[b_candidates.index.intersection(b_spatial.index)]
            c_candidates = c_candidates.loc[c_candidates.index.intersection(c_spatial.index)]

        if b_candidates.empty or c_candidates.empty:
            continue

        for _, b in b_candidates.iterrows():
            for _, c in c_candidates.iterrows():
                times = [a["start_time_utc"], b["start_time_utc"], c["start_time_utc"]]
                time_span = max(times) - min(times)
                if time_span > threshold:
                    continue

                delta_ab = abs(a["start_time_utc"] - b["start_time_utc"]).total_seconds() / 60.0
                delta_ac = abs(a["start_time_utc"] - c["start_time_utc"]).total_seconds() / 60.0
                delta_bc = abs(b["start_time_utc"] - c["start_time_utc"]).total_seconds() / 60.0

                if require_spatial_intersection:
                    ab = _safe_intersection(a.geometry, b.geometry)
                    if ab is None:
                        continue
                    common = _safe_intersection(ab, c.geometry)
                    if common is None:
                        continue
                    output_geometry = common if return_intersection_geometry else a.geometry
                else:
                    output_geometry = a.geometry

                records.append(
                    {
                        "feature_type": "triple_intersection" if require_spatial_intersection else "triple_temporal_match",
                        "match_id": f"{a['acquisition_id']}__{b['acquisition_id']}__{c['acquisition_id']}",
                        "platform_a": sat_a,
                        "platform_b": sat_b,
                        "platform_c": sat_c,
                        "platforms": f"{sat_a},{sat_b},{sat_c}",
                        "acquisition_id_a": a.get("acquisition_id"),
                        "acquisition_id_b": b.get("acquisition_id"),
                        "acquisition_id_c": c.get("acquisition_id"),
                        "start_time_a": a.get("start_time_utc"),
                        "start_time_b": b.get("start_time_utc"),
                        "start_time_c": c.get("start_time_utc"),
                        "stop_time_a": a.get("stop_time_utc"),
                        "stop_time_b": b.get("stop_time_utc"),
                        "stop_time_c": c.get("stop_time_utc"),
                        "time_delta_minutes": time_span.total_seconds() / 60.0,
                        "time_span_minutes": time_span.total_seconds() / 60.0,
                        "delta_ab_minutes": delta_ab,
                        "delta_ac_minutes": delta_ac,
                        "delta_bc_minutes": delta_bc,
                        "mode_a": a.get("mode"),
                        "mode_b": b.get("mode"),
                        "mode_c": c.get("mode"),
                        "source_kml_a": a.get("source_kml"),
                        "source_kml_b": b.get("source_kml"),
                        "source_kml_c": c.get("source_kml"),
                        "name_a": a.get("name"),
                        "name_b": b.get("name"),
                        "name_c": c.get("name"),
                        "geometry": output_geometry,
                    }
                )

    if not records:
        return gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs=acquisitions.crs or "EPSG:4326")

    out = gpd.GeoDataFrame(records, geometry="geometry", crs=acquisitions.crs or "EPSG:4326")
    out = _add_area_km2(out)

    if require_spatial_intersection and min_intersection_area_km2 > 0 and not out.empty:
        out = out[out["intersection_area_km2"] >= float(min_intersection_area_km2)]

    if not out.empty:
        out = out.sort_values(["time_span_minutes", "intersection_area_km2"], ascending=[True, False])

    return out

