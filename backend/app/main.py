from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.core.settings import settings
from app.storage.parquet import read_acquisitions
from app.storage.plans import read_downloaded_plans

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health() -> dict:
    acquisitions = read_acquisitions()
    return {
        "status": "ok",
        "app": settings.app_name,
        "data_dir": str(settings.data_dir),
        "acquisition_count": int(len(acquisitions)),
        "downloaded_plan_count": len(read_downloaded_plans()),
    }
