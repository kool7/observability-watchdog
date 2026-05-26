from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.anomaly import AnomalyResponse
from app.services.anomaly_list_service import get_anomaly, list_anomalies

router = APIRouter(tags=["anomalies"])


@router.get("/anomalies", response_model=list[AnomalyResponse])
async def get_anomalies(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    return await list_anomalies(db, limit=limit)


@router.get("/anomalies/{anomaly_id}", response_model=AnomalyResponse)
async def get_anomaly_by_id(
    anomaly_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await get_anomaly(db, anomaly_id)
