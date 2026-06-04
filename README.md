# Sentinel-2 Acquisition Overlap Explorer

A local web app for exploring planned Sentinel-2 acquisitions and finding near-simultaneous overlaps between **S2A**, **S2B**, and **S2C**.

The app downloads Copernicus Sentinel-2 acquisition-plan KML files, parses the planned swath footprints into GeoParquet, computes pairwise or true three-satellite overlaps in Python, and renders the results in a React/deck.gl map interface.

## What it does

- Downloads the latest Sentinel-2 acquisition-plan KMLs for S2A, S2B, and S2C.
- Parses planned acquisition footprints, acquisition times, modes, and source metadata.
- Stores normalized acquisition records as GeoParquet.
- Computes spatio-temporal overlaps server-side with FastAPI, GeoPandas, pandas, and Shapely.
- Supports both:
  - pairwise matches: `S2A ↔ S2B`, `S2A ↔ S2C`, `S2B ↔ S2C`
  - true triple matches: `S2A ∩ S2B ∩ S2C`
- Provides a deck.gl map UI with satellite filters, acquisition-mode filters, date range, and time-difference threshold.
- Keeps the default map view clean by showing overlap geometries first, with raw source swaths available as optional context.

## Data note

The Copernicus acquisition-plan KMLs describe **planned acquisition swaths**. They are useful for planning and exploratory analysis, but they should not be treated as exact product footprints.

The UI therefore treats the overlap geometries as planning-level results, not as authoritative product boundaries.

## Architecture

```text
s2-acquisition-overlap/
  backend/                 FastAPI API, KML ingestion, overlap logic, GeoParquet storage
  frontend/                React + Vite + deck.gl frontend
  data/                    Local raw KML files and processed GeoParquet outputs
  docker-compose.yml       Local Docker Compose setup
  Makefile                 Common development commands
```

```text
Copernicus KML files
        ↓
backend ingestion
        ↓
normalized GeoDataFrame
        ↓
GeoParquet cache
        ↓
FastAPI overlap endpoints
        ↓
React + deck.gl map UI
```

## Quick start with Docker

From the repository root:

```bash
docker compose up --build
```

Open the frontend:

```text
http://localhost:5173
```

The backend API is available at:

```text
http://localhost:8000
```

API docs:

```text
http://localhost:8000/docs
```

After the app starts, either click **Refresh latest plans** in the UI or run:

```bash
docker compose exec backend python -m app.cli refresh --platforms S2A S2B S2C --max-files-per-platform 1
```

## Run locally without Docker

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Fetch and parse the latest acquisition plans:

```bash
python -m app.cli refresh --platforms S2A S2B S2C --max-files-per-platform 1
```

Run the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Offline demo data

If you want to test the UI without downloading live Copernicus KML files, generate synthetic demo data:

```bash
cd backend
python -m app.cli demo-data
```

Then start the backend and frontend normally.

## Using the app

1. Refresh or generate acquisition data.
2. Select the Sentinel-2 units you want to compare.
3. Choose acquisition modes. `Nominal` is the recommended default.
4. Set a date range.
5. Move the time-difference slider, for example 15 minutes, 1 hour, or 6 hours.
6. Choose the match type:
   - **Pairwise matches** for two-satellite overlaps.
   - **All three together** for true S2A/S2B/S2C triple overlaps.
7. Choose map detail:
   - **Clean**: overlap geometries only. Recommended default.
   - **Context**: overlaps plus only the source swaths involved in matches.
   - **All**: all planned swaths. Useful for debugging, but visually dense.
8. Click a result row to highlight the related source swaths on the map.

## UI/UX principle

The map is intentionally **overlap-first**.

Showing all S2A/S2B/S2C planned swaths at once can quickly hide the basemap and make the analytical result hard to read. The default view is therefore clean: it shows the computed overlap geometries first, then reveals source swaths only when the user asks for more context.

This follows a progressive-disclosure pattern:

```text
Clean      → answer the question directly
Context    → explain where the match came from
All        → inspect/debug the full input data
```

## API overview

### Health check

```http
GET /health
```

### List downloaded plans

```http
GET /api/plans
```

### Refresh acquisition plans

```http
POST /api/refresh
```

Example:

```json
{
  "platforms": ["S2A", "S2B", "S2C"],
  "max_files_per_platform": 1
}
```

### Get acquisition footprints

```http
GET /api/acquisitions?satellites=S2A,S2B,S2C&modes=Nominal&start=2026-06-01T00:00:00Z&end=2026-06-15T23:59:59Z
```

### Compute overlaps

```http
POST /api/overlaps
```

Pairwise example:

```json
{
  "satellites": ["S2A", "S2B", "S2C"],
  "modes": ["Nominal"],
  "start": "2026-06-01T00:00:00Z",
  "end": "2026-06-15T23:59:59Z",
  "max_time_delta_minutes": 60,
  "match_kind": "pairwise",
  "require_spatial_intersection": true,
  "min_intersection_area_km2": 0,
  "return_intersection_geometry": true
}
```

Triple-overlap example:

```json
{
  "satellites": ["S2A", "S2B", "S2C"],
  "modes": ["Nominal"],
  "start": "2026-06-01T00:00:00Z",
  "end": "2026-06-15T23:59:59Z",
  "max_time_delta_minutes": 60,
  "match_kind": "triple",
  "require_spatial_intersection": true,
  "min_intersection_area_km2": 0,
  "return_intersection_geometry": true
}
```

In triple mode, `time_delta_minutes` is the full span between the earliest and latest of the three acquisition start times. The response also includes pairwise deltas as `delta_ab_minutes`, `delta_ac_minutes`, and `delta_bc_minutes`.

## Configuration

Backend environment variables:

```bash
S2PLANS_DATA_DIR=/absolute/path/to/data
S2PLANS_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Frontend environment variable:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

Example files are included at:

```text
backend/.env.example
frontend/.env.example
```

## Development

Run backend tests:

```bash
cd backend
pytest
```

Common commands from the repository root:

```bash
make backend    # run FastAPI backend
make frontend   # run Vite frontend
make refresh    # download and parse latest plans
make demo       # create synthetic demo data
make test       # run backend tests
```

## Known limitations

- KML metadata can vary between files, so the parser is deliberately tolerant.
- Antimeridian handling is basic. Production use should add explicit geometry normalization around ±180°.
- The MVP returns GeoJSON. For large historical archives, use bbox filtering, pagination, or vector tiles.
- Intersection area is estimated after reprojection to EPSG:6933. This is useful for filtering and comparison, but not a substitute for mission-grade geometric analysis.
- The app currently stores data locally. Multi-user deployments should move storage to PostGIS or object storage plus a catalog/index.

## Suggested next steps

- Add a date-aware plan archive instead of only using the latest files.
- Add bbox filtering to reduce payload size.
- Add export buttons for GeoJSON and CSV.
- Add a small timeline panel showing when the selected matches occur.
- Add a GitHub Actions workflow for backend tests and frontend build.

