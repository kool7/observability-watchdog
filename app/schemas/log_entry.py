from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.log_entry import LogLevel


class LogEntryCreate(BaseModel):
    service_name: str
    level: LogLevel
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict | None = None


class LogEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    service_name: str
    level: LogLevel
    message: str
    timestamp: datetime
    metadata: dict | None = Field(None, alias="metadata_")
