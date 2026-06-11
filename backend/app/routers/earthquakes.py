import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.rate_limit import limiter
from app.schemas.earthquake import EarthquakeFilter, EarthquakeListResponse, EarthquakeRead
from app.services.queries import (
    get_earthquake_by_id,
    get_heatmap_points,
    get_province_counts,
    get_summary_stats,
    list_earthquakes,
)

router = APIRouter(prefix="/earthquakes")
logger = logging.getLogger(__name__)


def _empty_earthquake_list(page: int, page_size: int) -> dict:
    return {"items": [], "total": 0, "page": page, "page_size": page_size}


def _empty_summary_stats() -> dict:
    return {
        "total_today": 0,
        "total_this_week": 0,
        "max_magnitude_today": None,
        "avg_depth_today": None,
        "most_affected_province": None,
        "counts_by_alert_level": {},
        "counts_by_island_group": {},
        "hourly_counts": [],
    }


def _is_database_unavailable(exc: Exception) -> bool:
    return isinstance(exc, (OSError, OperationalError, DBAPIError, ConnectionError))


def _log_degraded_database_response(endpoint: str, exc: Exception) -> None:
    logger.warning("%s returning degraded response because database is unavailable: %s", endpoint, exc)


@router.get("", response_model=EarthquakeListResponse, summary="List earthquakes", description="Return paginated earthquake events ordered by most recent occurrence.")
@limiter.limit("60/minute")
async def list_earthquake_events(
    request: Request,
    min_magnitude: Annotated[float | None, Query(ge=0, le=10)] = None,
    max_magnitude: Annotated[float | None, Query(ge=0, le=10)] = None,
    province: str | None = None,
    island_group: str | None = None,
    source: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 100,
    db: AsyncSession = Depends(get_db),
):
    filters = EarthquakeFilter(
        min_magnitude=min_magnitude,
        max_magnitude=max_magnitude,
        province=province,
        island_group=island_group,
        source=source,
        limit=limit,
        page=page,
        page_size=page_size,
    )
    try:
        return await list_earthquakes(db, filters)
    except Exception as exc:
        if not _is_database_unavailable(exc):
            raise
        _log_degraded_database_response("earthquake list", exc)
        return _empty_earthquake_list(filters.page, filters.page_size)


@router.get("/stats/summary", summary="Get earthquake summary stats", description="Return count, depth, magnitude, province, island group, and hourly stats for dashboard panels.")
@limiter.limit("5/minute")
async def summary_stats(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        return await get_summary_stats(db)
    except Exception as exc:
        if not _is_database_unavailable(exc):
            raise
        _log_degraded_database_response("earthquake summary stats", exc)
        return _empty_summary_stats()


@router.get("/stats/heatmap", summary="Get heatmap points", description="Return latitude, longitude, and magnitude values for events in the last 30 days.")
@limiter.limit("5/minute")
async def heatmap_points(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        return await get_heatmap_points(db)
    except Exception as exc:
        if not _is_database_unavailable(exc):
            raise
        _log_degraded_database_response("earthquake heatmap", exc)
        return []


@router.get("/{earthquake_id}", response_model=EarthquakeRead, summary="Get earthquake by ID", description="Return one earthquake event by UUID, or 404 if it does not exist.")
@limiter.limit("60/minute")
async def get_earthquake(earthquake_id: UUID, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        earthquake = await get_earthquake_by_id(db, earthquake_id)
    except Exception as exc:
        if not _is_database_unavailable(exc):
            raise
        _log_degraded_database_response("earthquake detail", exc)
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    if earthquake is None:
        raise HTTPException(status_code=404, detail="Earthquake not found")
    return earthquake


provinces_router = APIRouter()


@provinces_router.get("/provinces", summary="List province event counts", description="Return Philippine provinces with earthquake counts in the last 30 days.")
@limiter.limit("60/minute")
async def province_counts(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        return await get_province_counts(db)
    except Exception as exc:
        if not _is_database_unavailable(exc):
            raise
        _log_degraded_database_response("province counts", exc)
        return []
