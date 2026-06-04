from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime configuration for the Sentinel-2 plan explorer."""

    app_name: str = "Sentinel-2 Acquisition Overlap Explorer"
    source_url: str = "https://sentinels.copernicus.eu/copernicus/sentinel-2/acquisition-plans"
    data_dir: Path = Path(os.getenv("S2PLANS_DATA_DIR", Path(__file__).resolve().parents[3] / "data"))
    cors_origins: str = os.getenv(
        "S2PLANS_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )

    @property
    def raw_kml_dir(self) -> Path:
        return self.data_dir / "raw" / "kml"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def acquisitions_path(self) -> Path:
        return self.processed_dir / "acquisitions.parquet"

    @property
    def plans_path(self) -> Path:
        return self.processed_dir / "plans.json"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def ensure_dirs(self) -> None:
        self.raw_kml_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        for platform in ["S2A", "S2B", "S2C"]:
            (self.raw_kml_dir / platform).mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
