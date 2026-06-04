.PHONY: backend frontend refresh demo test zip

backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

refresh:
	cd backend && python -m app.cli refresh --platforms S2A S2B S2C --max-files-per-platform 1

demo:
	cd backend && python -m app.cli demo-data

test:
	cd backend && pytest

zip:
	cd .. && zip -r s2-acquisition-overlap.zip s2-acquisition-overlap -x "*/.venv/*" "*/node_modules/*" "*/__pycache__/*" "*/.pytest_cache/*"
