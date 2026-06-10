from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select

from app.models.earthquake import Earthquake
from app.schemas.earthquake import EarthquakeCreate, EarthquakeRead, Source, compute_alert_level

PH_LAT_MIN = 4.0
PH_LAT_MAX = 21.0
PH_LON_MIN = 116.0
PH_LON_MAX = 127.0
APPROX_200KM_DEGREES = 2.0
REDIS_NEW_EVENT_CHANNEL = "eq:new_event"


def is_near_philippines(lat: float, lon: float) -> bool:
    return (
        PH_LAT_MIN - APPROX_200KM_DEGREES
        <= lat
        <= PH_LAT_MAX + APPROX_200KM_DEGREES
        and PH_LON_MIN - APPROX_200KM_DEGREES
        <= lon
        <= PH_LON_MAX + APPROX_200KM_DEGREES
    )


async def normalize_and_save(
    raw_event: EarthquakeCreate | dict[str, Any],
    *,
    session,
    redis,
    geocoder,
) -> Earthquake | None:
    event = raw_event if isinstance(raw_event, EarthquakeCreate) else EarthquakeCreate.model_validate(raw_event)
    if not is_near_philippines(event.latitude, event.longitude):
        return None

    result = await session.execute(
        select(Earthquake).where(Earthquake.source == event.source.value, Earthquake.event_id == event.event_id)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        if event.source == Source.PHIVOLCS:
            existing.magnitude = event.magnitude
            existing.depth_km = event.depth_km
            existing.alert_level = compute_alert_level(event.magnitude, event.depth_km).value
            existing.raw_data = event.raw_data
            await session.commit()
        return existing

    match = geocoder.point_in_province(event.latitude, event.longitude) if geocoder is not None else None
    earthquake = Earthquake(
        event_id=event.event_id,
        source=event.source.value,
        magnitude=event.magnitude,
        magnitude_type=event.magnitude_type,
        depth_km=event.depth_km,
        latitude=event.latitude,
        longitude=event.longitude,
        place=event.place,
        province=match.province if match else event.province,
        region=match.region if match else event.region,
        island_group=(match.island_group.value if match else (event.island_group.value if event.island_group else None)),
        felt=event.felt,
        tsunami_warning=event.tsunami_warning,
        alert_level=compute_alert_level(event.magnitude, event.depth_km).value,
        occurred_at=event.occurred_at,
        ingested_at=datetime.now(UTC),
        raw_data=event.raw_data,
    )
    session.add(earthquake)
    await session.commit()
    await session.refresh(earthquake)

    read_model = EarthquakeRead.model_validate(earthquake)
    await redis.publish(REDIS_NEW_EVENT_CHANNEL, read_model.model_dump_json())
    return earthquake


async def cleanup_old_events(session, *, older_than: datetime) -> int:  # noqa: ANN001
    result = await session.execute(delete(Earthquake).where(Earthquake.occurred_at < older_than))
    await session.commit()
    return int(result.rowcount or 0)
