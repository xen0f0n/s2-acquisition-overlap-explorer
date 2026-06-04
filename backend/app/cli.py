from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

from app.ingest.kml_parser import parse_kml_file
from app.ingest.scrape import download_plan, fetch_remote_plans
from app.storage.parquet import append_acquisitions, write_acquisitions
from app.storage.plans import append_downloaded_plan, write_downloaded_plans


def cmd_refresh(args: argparse.Namespace) -> None:
    remote_plans = fetch_remote_plans()
    selected = []
    for platform in args.platforms:
        platform_plans = [plan for plan in remote_plans if plan.platform == platform]
        selected.extend(platform_plans[: args.max_files_per_platform])

    parsed_frames = []
    downloaded_count = 0

    for plan in selected:
        print(f"Downloading {plan.platform}: {plan.label} -> {plan.url}")
        downloaded = download_plan(plan, overwrite=args.overwrite)
        gdf = parse_kml_file(downloaded)
        append_downloaded_plan(downloaded, placemark_count=int(len(gdf)))
        downloaded_count += 1
        print(f"  parsed {len(gdf)} placemarks")
        if not gdf.empty:
            parsed_frames.append(gdf)

    if parsed_frames:
        combined = gpd.GeoDataFrame(pd.concat(parsed_frames, ignore_index=True), geometry="geometry", crs="EPSG:4326")
        added = append_acquisitions(combined)
        print(f"Added {added} acquisitions to GeoParquet")
    else:
        print("No acquisitions parsed")

    print(f"Downloaded files: {downloaded_count}")


def cmd_demo_data(_: argparse.Namespace) -> None:
    """Create synthetic data for UI/backend testing without internet."""
    rows = []
    base = pd.Timestamp("2026-06-04T10:00:00Z")
    geometries = {
        "S2A": Polygon([(20, 35), (30, 35), (30, 45), (20, 45), (20, 35)]),
        "S2B": Polygon([(25, 38), (35, 38), (35, 48), (25, 48), (25, 38)]),
        "S2C": Polygon([(22, 34), (32, 34), (32, 44), (22, 44), (22, 34)]),
    }
    offsets = {"S2A": 0, "S2B": 45, "S2C": 90}

    for platform, geom in geometries.items():
        for i in range(4):
            start = base + pd.Timedelta(hours=4 * i, minutes=offsets[platform])
            rows.append(
                {
                    "acquisition_id": f"demo_{platform}_{i}",
                    "platform": platform,
                    "mode": "Nominal",
                    "start_time_utc": start,
                    "stop_time_utc": start + pd.Timedelta(minutes=5),
                    "duration_seconds": 300,
                    "name": f"Demo {platform} acquisition {i}",
                    "description": "Synthetic demo footprint",
                    "style_url": None,
                    "metadata": {},
                    "source_kml": "demo",
                    "source_url": "demo",
                    "source_hash": "demo",
                    "downloaded_at_utc": pd.Timestamp.utcnow(),
                    "plan_start_utc": base,
                    "plan_stop_utc": base + pd.Timedelta(days=1),
                    "geometry": geom,
                }
            )

    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
    write_acquisitions(gdf)
    write_downloaded_plans(
        [
            {
                "platform": platform,
                "label": "Synthetic demo plan",
                "url": "demo",
                "filename": "demo.kml",
                "plan_start_utc": base.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "plan_stop_utc": (base + pd.Timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "downloaded_at_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sha256": "demo",
                "local_path": "demo",
                "placemark_count": 4,
            }
            for platform in ["S2A", "S2B", "S2C"]
        ]
    )
    print(f"Wrote {len(gdf)} synthetic acquisitions")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sentinel-2 acquisition-plan tools")
    sub = parser.add_subparsers(dest="command", required=True)

    refresh = sub.add_parser("refresh", help="Download and parse latest Copernicus KML files")
    refresh.add_argument("--platforms", nargs="+", default=["S2A", "S2B", "S2C"], choices=["S2A", "S2B", "S2C"])
    refresh.add_argument("--max-files-per-platform", type=int, default=1)
    refresh.add_argument("--overwrite", action="store_true")
    refresh.set_defaults(func=cmd_refresh)

    demo = sub.add_parser("demo-data", help="Create synthetic demo acquisitions")
    demo.set_defaults(func=cmd_demo_data)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
