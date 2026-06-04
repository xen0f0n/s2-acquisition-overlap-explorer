import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

from app.core.overlap import compute_pairwise_overlaps


def test_pairwise_spatiotemporal_overlap():
    gdf = gpd.GeoDataFrame(
        [
            {
                "acquisition_id": "a1",
                "platform": "S2A",
                "mode": "Nominal",
                "start_time_utc": pd.Timestamp("2026-06-04T10:00:00Z"),
                "stop_time_utc": pd.Timestamp("2026-06-04T10:05:00Z"),
                "source_kml": "a.kml",
                "geometry": Polygon([(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)]),
            },
            {
                "acquisition_id": "b1",
                "platform": "S2B",
                "mode": "Nominal",
                "start_time_utc": pd.Timestamp("2026-06-04T10:30:00Z"),
                "stop_time_utc": pd.Timestamp("2026-06-04T10:35:00Z"),
                "source_kml": "b.kml",
                "geometry": Polygon([(1, 1), (3, 1), (3, 3), (1, 3), (1, 1)]),
            },
        ],
        geometry="geometry",
        crs="EPSG:4326",
    )

    overlaps = compute_pairwise_overlaps(gdf, ["S2A", "S2B"], max_delta_minutes=60)
    assert len(overlaps) == 1
    assert overlaps.iloc[0]["time_delta_minutes"] == 30
    assert overlaps.iloc[0]["intersection_area_km2"] > 0


def test_time_threshold_filters_match():
    gdf = gpd.GeoDataFrame(
        [
            {
                "acquisition_id": "a1",
                "platform": "S2A",
                "mode": "Nominal",
                "start_time_utc": pd.Timestamp("2026-06-04T10:00:00Z"),
                "geometry": Polygon([(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)]),
            },
            {
                "acquisition_id": "b1",
                "platform": "S2B",
                "mode": "Nominal",
                "start_time_utc": pd.Timestamp("2026-06-04T12:00:00Z"),
                "geometry": Polygon([(1, 1), (3, 1), (3, 3), (1, 3), (1, 1)]),
            },
        ],
        geometry="geometry",
        crs="EPSG:4326",
    )

    overlaps = compute_pairwise_overlaps(gdf, ["S2A", "S2B"], max_delta_minutes=30)
    assert len(overlaps) == 0



def test_triple_spatiotemporal_overlap():
    from app.core.overlap import compute_triple_overlaps

    gdf = gpd.GeoDataFrame(
        [
            {
                "acquisition_id": "a1",
                "platform": "S2A",
                "mode": "Nominal",
                "start_time_utc": pd.Timestamp("2026-06-04T10:00:00Z"),
                "geometry": Polygon([(0, 0), (3, 0), (3, 3), (0, 3), (0, 0)]),
            },
            {
                "acquisition_id": "b1",
                "platform": "S2B",
                "mode": "Nominal",
                "start_time_utc": pd.Timestamp("2026-06-04T10:20:00Z"),
                "geometry": Polygon([(1, 1), (4, 1), (4, 4), (1, 4), (1, 1)]),
            },
            {
                "acquisition_id": "c1",
                "platform": "S2C",
                "mode": "Nominal",
                "start_time_utc": pd.Timestamp("2026-06-04T10:40:00Z"),
                "geometry": Polygon([(2, 2), (5, 2), (5, 5), (2, 5), (2, 2)]),
            },
        ],
        geometry="geometry",
        crs="EPSG:4326",
    )

    overlaps = compute_triple_overlaps(gdf, ["S2A", "S2B", "S2C"], max_delta_minutes=60)
    assert len(overlaps) == 1
    assert overlaps.iloc[0]["platforms"] == "S2A,S2B,S2C"
    assert overlaps.iloc[0]["time_span_minutes"] == 40
    assert overlaps.iloc[0]["intersection_area_km2"] > 0


def test_triple_time_span_filters_match():
    from app.core.overlap import compute_triple_overlaps

    gdf = gpd.GeoDataFrame(
        [
            {
                "acquisition_id": "a1",
                "platform": "S2A",
                "mode": "Nominal",
                "start_time_utc": pd.Timestamp("2026-06-04T10:00:00Z"),
                "geometry": Polygon([(0, 0), (3, 0), (3, 3), (0, 3), (0, 0)]),
            },
            {
                "acquisition_id": "b1",
                "platform": "S2B",
                "mode": "Nominal",
                "start_time_utc": pd.Timestamp("2026-06-04T10:20:00Z"),
                "geometry": Polygon([(1, 1), (4, 1), (4, 4), (1, 4), (1, 1)]),
            },
            {
                "acquisition_id": "c1",
                "platform": "S2C",
                "mode": "Nominal",
                "start_time_utc": pd.Timestamp("2026-06-04T11:20:00Z"),
                "geometry": Polygon([(2, 2), (5, 2), (5, 5), (2, 5), (2, 2)]),
            },
        ],
        geometry="geometry",
        crs="EPSG:4326",
    )

    overlaps = compute_triple_overlaps(gdf, ["S2A", "S2B", "S2C"], max_delta_minutes=60)
    assert len(overlaps) == 0
