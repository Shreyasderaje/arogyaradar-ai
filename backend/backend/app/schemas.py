from pydantic import BaseModel


class DistrictMonthAssessmentInput(BaseModel):
    """Request body for the district-month assessment endpoint."""

    district_id: str
    current_month: str
