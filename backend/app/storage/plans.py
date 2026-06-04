from __future__ import annotations

import json
from pathlib import Path

from app.core.settings import settings
from app.ingest.scrape import DownloadedPlan


def read_downloaded_plans(path: Path | None = None) -> list[dict]:
    path = path or settings.plans_path
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except Exception:
        return []


def write_downloaded_plans(plans: list[dict], path: Path | None = None) -> None:
    path = path or settings.plans_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plans, indent=2, ensure_ascii=False))


def append_downloaded_plan(plan: DownloadedPlan, placemark_count: int | None = None) -> None:
    existing = read_downloaded_plans()
    record = plan.to_dict()
    record["placemark_count"] = placemark_count

    by_hash = {item.get("sha256"): item for item in existing if item.get("sha256")}
    by_hash[record["sha256"]] = record
    write_downloaded_plans(list(by_hash.values()))
