from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.earthquake import Earthquake
from app.schemas.earthquake import EarthquakeFilter


def _apply_filters(statement, filters: EarthquakeFilter):  # noqa: ANN001
    if filters.min_magnitude is not None:
        statement = statement.where(Earthquake.magnitude >= filters.min_magnitude)
    if filters.max_magnitude is not None:
        statement = statement.where(Earthquake.magnitude <= filters.max_magnitude)
    if filters.province:
        statement = statement.where(Earthquake.province == filters.province)
    if filters.island_group:
        statement = statement.where(Earthquake.island_group == filters.island_group.value)
    if filters.source:
        statement = statement.where(Earthquake.source == filters.source.value)
    if filters.start_date:
        statement = statement.where(Earthquake.occurred_at >= filters.start_date)
    if filters.end_date:
        statement = statement.where(Earthquake.occurred_at <= filters.end_date)
    if not filters.start_date and not filters.end_date:
        statement = statement.where(Earthquake.occurred_at >= datetime.now(UTC) - timedelta(hours=24))
    return statement


async def list_earthquakes(db: AsyncSession, filters: EarthquakeFilter) -> dict[str, Any]:
    base = _apply_filters(select(Earthquake), filters)
    total = await db.scalar(select(func.count()).select_from(base.subquery()))
    result = await db.execute(
        base.order_by(desc(Earthquake.occurred_at))
        .offset((filters.page - 1) * filters.page_size)
        .limit(min(filters.limit, filters.page_size))
    )
    return {
        "items": list(result.scalars().all()),
        "total": int(total or 0),
        "page": filters.page,
        "page_size": filters.page_size,
    }


async def get_earthquake_by_id(db: AsyncSession, earthquake_id: UUID) -> Earthquake | None:
    return await db.get(Earthquake, earthquake_id)


async def get_summary_stats(db: AsyncSession) -> dict[str, Any]:
    now = datetime.now(UTC)
    day_start = now - timedelta(days=1)
    week_start = now - timedelta(days=7)

    total_today = await db.scalar(select(func.count()).where(Earthquake.occurred_at >= day_start))
    total_this_week = await db.scalar(select(func.count()).where(Earthquake.occurred_at >= week_start))
    max_magnitude_today = await db.scalar(select(func.max(Earthquake.magnitude)).where(Earthquake.occurred_at >= day_start))
    avg_depth_today = await db.scalar(select(func.avg(Earthquake.depth_km)).where(Earthquake.occurred_at >= day_start))

    province_result = await db.execute(
        select(Earthquake.province, func.count().label("count"))
        .where(Earthquake.occurred_at >= day_start, Earthquake.province.is_not(None))
        .group_by(Earthquake.province)
        .order_by(desc("count"))
        .limit(1)
    )
    province_row = province_result.first()

    alert_result = await db.execute(
        select(Earthquake.alert_level, func.count()).where(Earthquake.occurred_at >= day_start).group_by(Earthquake.alert_level)
    )
    island_result = await db.execute(
        select(Earthquake.island_group, func.count())
        .where(Earthquake.occurred_at >= day_start, Earthquake.island_group.is_not(None))
        .group_by(Earthquake.island_group)
    )
    hourly_result = await db.execute(
        select(
            func.date_trunc("hour", Earthquake.occurred_at).label("hour"),
            func.count().label("count"),
            func.max(Earthquake.magnitude).label("max_magnitude"),
        )
        .where(Earthquake.occurred_at >= day_start)
        .group_by("hour")
        .order_by("hour")
    )

    return {
        "total_today": int(total_today or 0),
        "total_this_week": int(total_this_week or 0),
        "max_magnitude_today": float(max_magnitude_today or 0),
        "avg_depth_today": float(avg_depth_today or 0),
        "most_affected_province": province_row[0] if province_row else None,
        "counts_by_alert_level": {str(level): int(count) for level, count in alert_result.all()},
        "counts_by_island_group": {str(group): int(count) for group, count in island_result.all()},
        "hourly_counts": [
            {"hour": hour.isoformat(), "count": int(count), "max_magnitude": float(max_magnitude or 0)}
            for hour, count, max_magnitude in hourly_result.all()
        ],
    }


async def get_heatmap_points(db: AsyncSession) -> list[dict[str, float]]:
    result = await db.execute(
        select(Earthquake.latitude, Earthquake.longitude, Earthquake.magnitude).where(
            Earthquake.occurred_at >= datetime.now(UTC) - timedelta(days=30)
        )
    )
    return [{"lat": lat, "lon": lon, "magnitude": magnitude} for lat, lon, magnitude in result.all()]


async def get_province_counts(db: AsyncSession) -> list[dict[str, Any]]:
    result = await db.execute(
        select(Earthquake.province, func.count().label("count"))
        .where(Earthquake.occurred_at >= datetime.now(UTC) - timedelta(days=30), Earthquake.province.is_not(None))
        .group_by(Earthquake.province)
        .order_by(desc("count"))
    )
    return [{"province": province, "count": int(count)} for province, count in result.all()]

