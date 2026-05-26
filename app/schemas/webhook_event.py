from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WebhookEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    anomaly_id: UUID
    fired_at: datetime
    payload: dict
    response_status: int
