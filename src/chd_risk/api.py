from __future__ import annotations

from .assessment import assess_patient, assess_with_bundle
from .model_registry import load_bundle
from .schema import PatientSnapshot

try:
    from fastapi import FastAPI
except ModuleNotFoundError:  # pragma: no cover
    FastAPI = None


def create_app():
    if FastAPI is None:
        raise RuntimeError("Install API dependencies with: pip install -e '.[api]'")

    from fastapi import HTTPException
    from pydantic import BaseModel, Field

    app = FastAPI(title="CHD Risk Closed-Loop Prototype", version="0.1.0")

    class AssessRequest(BaseModel):
        patient_id: str | None = Field(default=None, description="De-identified patient id")
        age: int = Field(..., ge=18, le=110, description="Age in years")
        sex: str = Field(..., description="男/女 or male/female")
        bmi: float | None = Field(default=None, ge=10, le=80)
        sbp: float | None = Field(default=None, ge=50, le=300)
        dbp: float | None = Field(default=None, ge=30, le=200)
        total_chol: float | None = None
        ldl_c: float | None = None
        hdl_c: float | None = None
        fasting_glucose: float | None = None
        smoker: bool | None = None
        diabetes: bool | None = None
        hypertension: bool | None = None
        ckd: bool | None = None
        atrial_fibrillation: bool | None = None
        family_history_chd: bool | None = None
        chest_pain_visit_last_year: bool | None = None
        ecg_abnormal: bool | None = None
        carotid_ultrasound_abnormal: bool | None = None
        antihypertensive_use: bool | None = None
        lipid_lowering_use: bool | None = None
        antiplatelet_use: bool | None = None
        statin_adherence_gap: bool | None = None
        follow_up_interrupted: bool | None = None
        outpatient_visits_12m: int | None = None
        emergency_visits_12m: int | None = None
        sbp_trend_6m: float | None = None
        ldl_trend_6m: float | None = None
        medication_adherence_rate: float | None = Field(default=None, ge=0, le=1)
        china_par_score: float | None = None
        reference_date: str | None = None

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/assess")
    def assess(payload: AssessRequest) -> dict:
        try:
            snapshot = PatientSnapshot.from_mapping(payload.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        bundle = load_bundle()
        if bundle is None:
            return assess_patient(snapshot).to_dict()
        return assess_with_bundle(snapshot, bundle).to_dict()

    return app


app = create_app() if FastAPI is not None else None
