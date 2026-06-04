from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable

import geopandas as gpd
import pandas as pd
from shapely import make_valid
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

from app.ingest.scrape import DownloadedPlan

ISO_DATETIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z")
COMPACT_DATETIME = re.compile(r"\d{8}T\d{6}", re.IGNORECASE)

MODE_ALIASES = {
    "nominal": "Nominal",
    "vicarious": "Vicarious",
    "calibration": "Calibration",
}


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _children_by_local_name(node: ET.Element, local_name: str) -> list[ET.Element]:
    return [child for child in list(node) if _local_name(child.tag) == local_name]


def _first_child_text(node: ET.Element, local_name: str) -> str | None:
    for child in node.iter():
        if _local_name(child.tag) == local_name and child.text:
            return child.text.strip()
    return None


def _all_child_texts(node: ET.Element, local_name: str) -> list[str]:
    out = []
    for child in node.iter():
        if _local_name(child.tag) == local_name and child.text:
            out.append(child.text.strip())
    return out


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = html.unescape(value)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _extract_extended_data(placemark: ET.Element) -> dict[str, str]:
    metadata: dict[str, str] = {}

    for data in placemark.iter():
        local = _local_name(data.tag)
        if local not in {"Data", "SimpleData"}:
            continue

        name = data.attrib.get("name")
        if not name:
            continue

        if local == "Data":
            value = None
            for child in list(data):
                if _local_name(child.tag) == "value" and child.text:
                    value = child.text.strip()
                    break
        else:
            value = data.text.strip() if data.text else None

        if value:
            metadata[name] = value

    return metadata


def _parse_coordinates(coord_text: str) -> list[tuple[float, float]]:
    coords = []
    for token in coord_text.replace("\n", " ").replace("\t", " ").split():
        parts = token.split(",")
        if len(parts) < 2:
            continue
        try:
            lon = float(parts[0])
            lat = float(parts[1])
        except ValueError:
            continue
        coords.append((lon, lat))
    return coords


def _polygon_from_node(polygon_node: ET.Element) -> Polygon | None:
    outer_coords: list[tuple[float, float]] | None = None
    inner_rings: list[list[tuple[float, float]]] = []

    for boundary in polygon_node.iter():
        boundary_name = _local_name(boundary.tag)
        if boundary_name not in {"outerBoundaryIs", "innerBoundaryIs"}:
            continue

        coord_texts = _all_child_texts(boundary, "coordinates")
        if not coord_texts:
            continue
        coords = _parse_coordinates(coord_texts[0])
        if len(coords) < 4:
            continue

        if boundary_name == "outerBoundaryIs":
            outer_coords = coords
        else:
            inner_rings.append(coords)

    if not outer_coords:
        coord_texts = _all_child_texts(polygon_node, "coordinates")
        if not coord_texts:
            return None
        outer_coords = _parse_coordinates(coord_texts[0])

    if len(outer_coords) < 4:
        return None

    try:
        polygon = Polygon(outer_coords, inner_rings)
    except Exception:
        return None

    if polygon.is_empty:
        return None

    valid = make_valid(polygon)
    if valid.is_empty:
        return None
    if valid.geom_type == "Polygon":
        return valid
    if valid.geom_type == "MultiPolygon":
        return valid
    return None


def _extract_geometry(placemark: ET.Element) -> Polygon | MultiPolygon | None:
    polygons = []
    for node in placemark.iter():
        if _local_name(node.tag) == "Polygon":
            poly = _polygon_from_node(node)
            if poly is not None and not poly.is_empty:
                polygons.append(poly)

    if not polygons:
        return None

    geom = unary_union(polygons)
    valid = make_valid(geom)
    if valid.is_empty:
        return None
    if valid.geom_type in {"Polygon", "MultiPolygon"}:
        return valid
    return None


def _extract_datetimes(text: str) -> list[pd.Timestamp]:
    candidates: list[pd.Timestamp] = []

    for match in ISO_DATETIME.findall(text):
        parsed = pd.to_datetime(match, utc=True, errors="coerce")
        if pd.notna(parsed):
            candidates.append(parsed)

    for match in COMPACT_DATETIME.findall(text):
        parsed = pd.to_datetime(match.upper(), format="%Y%m%dT%H%M%S", utc=True, errors="coerce")
        if pd.notna(parsed):
            candidates.append(parsed)

    # Keep insertion order but remove duplicates.
    out: list[pd.Timestamp] = []
    seen: set[int] = set()
    for candidate in candidates:
        key = int(candidate.value)
        if key not in seen:
            out.append(candidate)
            seen.add(key)
    return out


def _infer_mode(text: str, metadata: dict[str, str]) -> str | None:
    metadata_values = " ".join(str(v) for v in metadata.values())
    blob = f"{text} {metadata_values}".lower()
    for token, mode in MODE_ALIASES.items():
        if token in blob:
            return mode
    return None


def _first_matching_metadata(metadata: dict[str, str], names: Iterable[str]) -> str | None:
    lowered = {k.lower(): v for k, v in metadata.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value:
            return value
    return None


def parse_kml_file(plan: DownloadedPlan) -> gpd.GeoDataFrame:
    path = Path(plan.local_path)
    root = ET.parse(path).getroot()
    rows: list[dict] = []

    for index, placemark in enumerate(node for node in root.iter() if _local_name(node.tag) == "Placemark"):
        geometry = _extract_geometry(placemark)
        if geometry is None:
            continue

        metadata = _extract_extended_data(placemark)
        name = _clean_text(_first_child_text(placemark, "name"))
        description = _clean_text(_first_child_text(placemark, "description"))
        style_url = _clean_text(_first_child_text(placemark, "styleUrl"))
        time_begin = _first_child_text(placemark, "begin")
        time_end = _first_child_text(placemark, "end")

        metadata_text = " ".join(f"{k}={v}" for k, v in metadata.items())
        combined = " ".join(x for x in [name, description, style_url, metadata_text] if x)

        start_value = _first_matching_metadata(
            metadata,
            [
                "start",
                "start_time",
                "startTime",
                "sensing_start",
                "sensingStart",
                "datatake_start",
                "beginPosition",
            ],
        ) or time_begin
        stop_value = _first_matching_metadata(
            metadata,
            [
                "stop",
                "end",
                "stop_time",
                "stopTime",
                "sensing_stop",
                "sensingStop",
                "datatake_stop",
                "endPosition",
            ],
        ) or time_end

        start_time = pd.to_datetime(start_value, utc=True, errors="coerce") if start_value else pd.NaT
        stop_time = pd.to_datetime(stop_value, utc=True, errors="coerce") if stop_value else pd.NaT

        if pd.isna(start_time) or pd.isna(stop_time):
            candidates = _extract_datetimes(combined)
            if pd.isna(start_time) and candidates:
                start_time = candidates[0]
            if pd.isna(stop_time) and len(candidates) >= 2:
                stop_time = candidates[1]
            elif pd.isna(stop_time) and candidates:
                stop_time = candidates[0]

        acquisition_id = f"{plan.platform}_{plan.sha256[:12]}_{index:05d}"
        duration = None
        if pd.notna(start_time) and pd.notna(stop_time):
            duration = float((stop_time - start_time).total_seconds())
            if duration < 0:
                duration = None

        rows.append(
            {
                "acquisition_id": acquisition_id,
                "platform": plan.platform,
                "mode": _infer_mode(combined, metadata),
                "start_time_utc": start_time if pd.notna(start_time) else None,
                "stop_time_utc": stop_time if pd.notna(stop_time) else None,
                "duration_seconds": duration,
                "name": name,
                "description": description,
                "style_url": style_url,
                "metadata": metadata,
                "source_kml": plan.filename,
                "source_url": plan.url,
                "source_hash": plan.sha256,
                "downloaded_at_utc": plan.downloaded_at_utc,
                "plan_start_utc": plan.plan_start_utc,
                "plan_stop_utc": plan.plan_stop_utc,
                "geometry": geometry,
            }
        )

    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
