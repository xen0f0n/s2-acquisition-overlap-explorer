from __future__ import annotations

import geopandas as gpd
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.api.schemas import OverlapRequest, RefreshRequest, RefreshResponse
from app.core.geojson import gdf_to_geojson_dict
from app.core.overlap import compute_pairwise_overlaps, compute_triple_overlaps
from app.ingest.kml_parser import parse_kml_file
from app.ingest.scrape import download_plan, fetch_remote_plans
from app.storage.parquet import append_acquisitions, filter_acquisitions, read_acquisitions
from app.storage.plans import append_downloaded_plan, read_downloaded_plans

router = APIRouter(prefix="/api")


def _split_csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


@router.get("/plans")
def list_plans() -> dict:
    return {"plans": read_downloaded_plans()}


@router.post("/refresh", response_model=RefreshResponse)
def refresh_plans(payload: RefreshRequest) -> RefreshResponse:
    try:
        remote_plans = fetch_remote_plans()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch Copernicus plan index: {exc}") from exc

    selected = []
    for platform in payload.platforms:
        platform_plans = [plan for plan in remote_plans if plan.platform == platform]
        selected.extend(platform_plans[: payload.max_files_per_platform])

    parsed_frames: list[gpd.GeoDataFrame] = []
    downloaded_records: list[dict] = []

    for remote_plan in selected:
        try:
            downloaded = download_plan(remote_plan, overwrite=payload.overwrite)
            gdf = parse_kml_file(downloaded)
            downloaded_records.append(downloaded.to_dict() | {"placemark_count": int(len(gdf))})
            append_downloaded_plan(downloaded, placemark_count=int(len(gdf)))
            if not gdf.empty:
                parsed_frames.append(gdf)
        except Exception as exc:
            # Continue with other platforms/files; surface partial failure as metadata.
            downloaded_records.append(
                {
                    "platform": remote_plan.platform,
                    "url": remote_plan.url,
                    "filename": remote_plan.filename,
                    "error": str(exc),
                }
            )

    if parsed_frames:
        combined = gpd.GeoDataFrame(
            pd.concat(parsed_frames, ignore_index=True), geometry="geometry", crs="EPSG:4326"
        )
        added = append_acquisitions(combined)
        parsed_count = int(len(combined))
    else:
        added = 0
        parsed_count = 0

    return RefreshResponse(
        downloaded_files=len(selected),
        parsed_acquisitions=parsed_count,
        added_acquisitions=added,
        plans=downloaded_records,
    )


@router.get("/acquisitions")
def get_acquisitions(
    satellites: str | None = Query(default="S2A,S2B,S2C"),
    modes: str | None = Query(default="Nominal"),
    start: str | None = None,
    end: str | None = None,
) -> dict:
    gdf = read_acquisitions()
    filtered = filter_acquisitions(
        gdf,
        satellites=_split_csv(satellites),
        modes=_split_csv(modes),
        start=start,
        end=end,
    )
    return gdf_to_geojson_dict(filtered)


@router.post("/overlaps")
def get_overlaps(payload: OverlapRequest) -> dict:
    gdf = read_acquisitions()
    filtered = filter_acquisitions(
        gdf,
        satellites=payload.satellites,
        modes=payload.modes,
        start=payload.start,
        end=payload.end,
    )
    if payload.match_kind == "triple":
        if len(set(payload.satellites)) != 3:
            raise HTTPException(status_code=400, detail="Triple matching requires exactly three selected satellites.")
        overlaps = compute_triple_overlaps(
            filtered,
            satellites=payload.satellites,
            max_delta_minutes=payload.max_time_delta_minutes,
            require_spatial_intersection=payload.require_spatial_intersection,
            min_intersection_area_km2=payload.min_intersection_area_km2,
            return_intersection_geometry=payload.return_intersection_geometry,
        )
    else:
        overlaps = compute_pairwise_overlaps(
            filtered,
            satellites=payload.satellites,
            max_delta_minutes=payload.max_time_delta_minutes,
            require_spatial_intersection=payload.require_spatial_intersection,
            min_intersection_area_km2=payload.min_intersection_area_km2,
            return_intersection_geometry=payload.return_intersection_geometry,
        )
    return gdf_to_geojson_dict(overlaps)
