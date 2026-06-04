from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.core.settings import settings
from app.core.time import parse_compact_utc, utc_now_iso

PLATFORM_FROM_URL = re.compile(r"s2([abc])_mp_acq__kml", re.IGNORECASE)
PLAN_RANGE = re.compile(r"(\d{8}t\d{6})_(\d{8}t\d{6})", re.IGNORECASE)


@dataclass(frozen=True)
class RemotePlan:
    platform: str
    label: str
    url: str
    filename: str
    plan_start_utc: str | None
    plan_stop_utc: str | None


@dataclass(frozen=True)
class DownloadedPlan:
    platform: str
    label: str
    url: str
    filename: str
    plan_start_utc: str | None
    plan_stop_utc: str | None
    downloaded_at_utc: str
    sha256: str
    local_path: str
    placemark_count: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def infer_filename(url: str) -> str:
    path_name = Path(urlparse(url).path).name
    if path_name.lower().endswith(".kml"):
        return path_name
    return f"{path_name}.kml"


def parse_plan_range_from_text(text: str) -> tuple[str | None, str | None]:
    match = PLAN_RANGE.search(text)
    if not match:
        return None, None
    start = parse_compact_utc(match.group(1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    stop = parse_compact_utc(match.group(2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return start, stop


def fetch_remote_plans(source_url: str | None = None) -> list[RemotePlan]:
    """Scrape the Copernicus acquisition-plan page for S2A/S2B/S2C KML links."""
    url = source_url or settings.source_url
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    plans: list[RemotePlan] = []

    for link in soup.find_all("a", href=True):
        href = link["href"]
        match = PLATFORM_FROM_URL.search(href)
        if not match:
            continue

        platform = f"S2{match.group(1).upper()}"
        full_url = urljoin(url, href)
        filename = infer_filename(full_url)
        label = " ".join(link.get_text(" ", strip=True).split()) or filename
        plan_start, plan_stop = parse_plan_range_from_text(full_url + " " + filename)

        plans.append(
            RemotePlan(
                platform=platform,
                label=label,
                url=full_url,
                filename=filename,
                plan_start_utc=plan_start,
                plan_stop_utc=plan_stop,
            )
        )

    # The current page is ordered newest-first per platform. Preserve that order but remove duplicates.
    deduped: list[RemotePlan] = []
    seen: set[str] = set()
    for plan in plans:
        key = plan.url
        if key not in seen:
            deduped.append(plan)
            seen.add(key)
    return deduped


def download_plan(plan: RemotePlan, overwrite: bool = False) -> DownloadedPlan:
    """Download a remote KML plan and store it under data/raw/kml/<platform>."""
    settings.ensure_dirs()
    response = requests.get(plan.url, timeout=60)
    response.raise_for_status()
    content = response.content
    sha256 = hashlib.sha256(content).hexdigest()

    safe_filename = re.sub(r"[^A-Za-z0-9_.-]+", "_", plan.filename)
    local_path = settings.raw_kml_dir / plan.platform / f"{sha256[:12]}_{safe_filename}"

    if overwrite or not local_path.exists():
        local_path.write_bytes(content)

    return DownloadedPlan(
        platform=plan.platform,
        label=plan.label,
        url=plan.url,
        filename=plan.filename,
        plan_start_utc=plan.plan_start_utc,
        plan_stop_utc=plan.plan_stop_utc,
        downloaded_at_utc=utc_now_iso(),
        sha256=sha256,
        local_path=str(local_path),
    )
