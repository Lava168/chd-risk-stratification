from __future__ import annotations

from .assessment import assess_patient
from .schema import PatientSnapshot


try:
    from fastapi import FastAPI
except ModuleNotFoundError:  # pragma: no cover
    FastAPI = None


def create_app():
    if FastAPI is None:
        raise RuntimeError("Install API dependencies with: pip install -e '.[api]'")

    app = FastAPI(title="CHD Risk Closed-Loop Prototype", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/assess")
    def assess(payload: dict) -> dict:
        snapshot = PatientSnapshot.from_mapping(payload)
        return assess_patient(snapshot).to_dict()

    return app


app = create_app() if FastAPI is not None else None

