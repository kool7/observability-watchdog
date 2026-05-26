from datetime import datetime

from pydantic import BaseModel


class TrendBucketResponse(BaseModel):
    bucket: datetime
    service_name: str
    error_count: int
    warn_count: int
    info_count: int
