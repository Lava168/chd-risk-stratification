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

    from typing import Optional

    from fastapi import HTTPException
    from pydantic import BaseModel, Field

    app = FastAPI(title="CHD Risk Closed-Loop Prototype", version="0.1.0")

    class AssessRequest(BaseModel):
        patient_id: Optional[str] = Field(default=None, description="De-identified patient id")
        age: int = Field(..., ge=18, le=110, description="Age in years")
        sex: str = Field(..., description="男/女 or male/female")
        bmi: Optional[float] = Field(default=None, ge=10, le=80)
        sbp: Optional[float] = Field(default=None, ge=50, le=300)
        dbp: Optional[float] = Field(default=None, ge=30, le=200)
        total_chol: Optional[float] = None
        ldl_c: Optional[float] = None
        hdl_c: Optional[float] = None
        fasting_glucose: Optional[float] = None
        smoker: Optional[bool] = None
        diabetes: Optional[bool] = None
        hypertension: Optional[bool] = None
        ckd: Optional[bool] = None
        atrial_fibrillation: Optional[bool] = None
        family_history_chd: Optional[bool] = None
        chest_pain_visit_last_year: Optional[bool] = None
        ecg_abnormal: Optional[bool] = None
        carotid_ultrasound_abnormal: Optional[bool] = None
        antihypertensive_use: Optional[bool] = None
        lipid_lowering_use: Optional[bool] = None
        antiplatelet_use: Optional[bool] = None
        statin_adherence_gap: Optional[bool] = None
        follow_up_interrupted: Optional[bool] = None
        outpatient_visits_12m: Optional[int] = None
        emergency_visits_12m: Optional[int] = None
        sbp_trend_6m: Optional[float] = None
        ldl_trend_6m: Optional[float] = None
        medication_adherence_rate: Optional[float] = Field(default=None, ge=0, le=1)
        china_par_score: Optional[float] = None
        reference_date: Optional[str] = None

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/assess")
    def assess(payload: AssessRequest) -> dict:
        try:
            snapshot = PatientSnapshot.from_mapping(payload.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        try:
            bundle = load_bundle()
        except Exception as exc:  # model exists but cannot load (e.g. missing libomp)
            bundle = None
            print(f"[chd-risk] trained model unavailable ({type(exc).__name__}: {exc}); "
                  "falling back to weighted prototype")
        if bundle is None:
            return assess_patient(snapshot).to_dict()
        return assess_with_bundle(snapshot, bundle).to_dict()

    # Serve the doctor-friendly UI from ./ui when present.
    import sys as _sys
    from pathlib import Path

    from fastapi.responses import RedirectResponse
    from fastapi.staticfiles import StaticFiles

    if getattr(_sys, "frozen", False):  # PyInstaller bundle
        ui_dir = Path(_sys._MEIPASS) / "ui"
    else:
        ui_dir = Path(__file__).resolve().parents[2] / "ui"
    if ui_dir.exists():
        app.mount("/ui", StaticFiles(directory=str(ui_dir), html=True), name="ui")

        @app.get("/", include_in_schema=False)
        def root() -> RedirectResponse:
            return RedirectResponse(url="/ui/")

    return app


app = create_app() if FastAPI is not None else None
