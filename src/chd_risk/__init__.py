"""Community CHD risk assessment and closed-loop management prototype."""

from .assessment import RiskAssessment, assess_patient
from .schema import PatientSnapshot

__all__ = ["PatientSnapshot", "RiskAssessment", "assess_patient"]

