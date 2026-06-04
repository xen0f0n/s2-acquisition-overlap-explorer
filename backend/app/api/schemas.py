from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Platform = Literal["S2A", "S2B", "S2C"]
Mode = Literal["Nominal", "Vicarious", "Calibration"]
MatchKind = Literal["pairwise", "triple"]


class RefreshRequest(BaseModel):
    platforms: list[Platform] = Field(default_factory=lambda: ["S2A", "S2B", "S2C"])
    max_files_per_platform: int = Field(default=1, ge=1, le=20)
    overwrite: bool = False


class RefreshResponse(BaseModel):
    downloaded_files: int
    parsed_acquisitions: int
    added_acquisitions: int
    plans: list[dict]


class OverlapRequest(BaseModel):
    satellites: list[Platform] = Field(default_factory=lambda: ["S2A", "S2B", "S2C"])
    modes: list[Mode] | None = Field(default_factory=lambda: ["Nominal"])
    start: str | None = None
    end: str | None = None
    max_time_delta_minutes: float = Field(default=60, gt=0, le=7 * 24 * 60)
    require_spatial_intersection: bool = True
    min_intersection_area_km2: float = Field(default=0, ge=0)
    return_intersection_geometry: bool = True
    match_kind: MatchKind = "pairwise"
