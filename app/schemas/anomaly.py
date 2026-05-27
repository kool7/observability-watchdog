from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.anomaly import Severity


class AnomalyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_name: str
    detected_at: datetime
    window_start: datetime
    window_end: datetime
    error_count: int
    z_score: float
    threshold_breached: float
    ai_narrative: str | None
    severity: Severity
    webhook_fired: bool
    baseline_mean: float | None = None
    top_errors: list[dict] = []
    trend_direction: str | None = None
