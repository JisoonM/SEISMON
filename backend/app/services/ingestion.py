from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.schemas.earthquake import EarthquakeCreate, Source
from app.services.normalizer import normalize_and_save

logger = logging.getLogger(__name__)
PHT = timezone(timedelta(hours=8))


def _first_float(value: Any, default: float = 0.0) -> float:
    match = re.search(r"-?\d+(?:\.\d+)?", str(value or ""))
    return float(match.group(0)) if match else default


def _utc_from_epoch_ms(value: int | float) -> datetime:
    return datetime.fromtimestamp(float(value) / 1000, tz=UTC)


def _parse_emsc_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def parse_usgs_feature_collection(payload: dict[str, Any]) -> list[EarthquakeCreate]:
    events: list[EarthquakeCreate] = []
    for feature in payload.get("features", []):
        properties = feature.get("properties") or {}
        coordinates = (feature.get("geometry") or {}).get("coordinates") or []
        if len(coordinates) < 3 or properties.get("mag") is None or properties.get("time") is None:
            continue
        events.append(
            EarthquakeCreate(
                event_id=str(feature.get("id") or properties.get("code")),
                source=Source.USGS,
                magnitude=float(properties["mag"]),
                magnitude_type=str(properties.get("magType") or "unknown"),
                depth_km=float(coordinates[2]),
                latitude=float(coordinates[1]),
                longitude=float(coordinates[0]),
                place=str(properties.get("place") or "Unknown location"),
                felt=bool(properties.get("felt")),
                tsunami_warning=bool(properties.get("tsunami")),
                occurred_at=_utc_from_epoch_ms(properties["time"]),
                raw_data=feature,
            )
        )
    return events


def _parse_phivolcs_datetime(value: str) -> datetime:
    cleaned = " ".join(value.replace("\xa0", " ").replace("–", "-").split())
    for fmt in ("%d %B %Y - %I:%M %p", "%d %B %Y %I:%M %p", "%Y-%m-%d %H:%M:%S", "%d %b %Y - %I:%M %p"):
        try:
            return datetime.strptime(cleaned, fmt).replace(tzinfo=PHT).astimezone(UTC)
        except ValueError:
            continue
    raise ValueError(f"Unsupported PHIVOLCS datetime: {value}")


def parse_phivolcs_events(html: str) -> list[EarthquakeCreate]:
    soup = BeautifulSoup(html, "html.parser")
    events: list[EarthquakeCreate] = []
    for row in soup.select("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
        if len(cells) < 6 or any("date" in cell.lower() for cell in cells[:1]):
            continue
        try:
            occurred_at = _parse_phivolcs_datetime(cells[0])
            latitude = _first_float(cells[1])
            longitude = _first_float(cells[2])
            depth_km = _first_float(cells[3])
            magnitude = _first_float(cells[4])
            place = cells[5]
        except (ValueError, IndexError):
            logger.exception("Failed to parse PHIVOLCS row", extra={"row": cells})
            continue
        event_hash = hashlib.sha1(f"{occurred_at.isoformat()}|{latitude}|{longitude}|{magnitude}".encode()).hexdigest()[:10]
        events.append(
            EarthquakeCreate(
                event_id=f"phivolcs-{occurred_at.strftime('%Y%m%dT%H%M%S')}-{event_hash}",
                source=Source.PHIVOLCS,
                magnitude=magnitude,
                magnitude_type="ML",
                depth_km=depth_km,
                latitude=latitude,
                longitude=longitude,
                place=place,
                felt="felt" in place.lower(),
                occurred_at=occurred_at,
                raw_data={"row": cells},
            )
        )
    return events


def parse_emsc_events(payload: dict[str, Any]) -> list[EarthquakeCreate]:
    events: list[EarthquakeCreate] = []
    for feature in payload.get("features", []):
        properties = feature.get("properties") or {}
        coordinates = (feature.get("geometry") or {}).get("coordinates") or []
        if len(coordinates) < 3 or properties.get("mag") is None or properties.get("time") is None:
            continue
        events.append(
            EarthquakeCreate(
                event_id=str(feature.get("id") or properties.get("unid")),
                source=Source.EMSC,
                magnitude=float(properties["mag"]),
                magnitude_type=str(properties.get("magtype") or properties.get("magType") or "unknown"),
                depth_km=float(coordinates[2]),
                latitude=float(coordinates[1]),
                longitude=float(coordinates[0]),
                place=str(properties.get("flynn_region") or properties.get("place") or "Unknown location"),
                occurred_at=_parse_emsc_time(str(properties["time"])),
                raw_data=feature,
            )
        )
    return events


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
async def _get_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
async def _get_text(url: str) -> str:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


async def ingest_usgs(session, redis, geocoder, *, backfill: bool = False) -> int:  # noqa: ANN001
    settings = get_settings()
    url = str(settings.usgs_backfill_url if backfill else settings.usgs_feed_url)
    payload = await _get_json(url)
    return await _normalize_many(parse_usgs_feature_collection(payload), session, redis, geocoder)


async def ingest_phivolcs(session, redis, geocoder) -> int:  # noqa: ANN001
    html = await _get_text(str(get_settings().phivolcs_url))
    return await _normalize_many(parse_phivolcs_events(html), session, redis, geocoder)


async def ingest_emsc(session, redis, geocoder) -> int:  # noqa: ANN001
    settings = get_settings()
    payload = await _get_json(
        str(settings.emsc_api_url),
        params={
            "format": "json",
            "limit": 50,
            "minlatitude": 4,
            "maxlatitude": 21,
            "minlongitude": 116,
            "maxlongitude": 127,
        },
    )
    return await _normalize_many(parse_emsc_events(payload), session, redis, geocoder)


async def ingest_all_sources(session, redis, geocoder) -> int:  # noqa: ANN001
    results = await asyncio.gather(
        ingest_phivolcs(session, redis, geocoder),
        ingest_usgs(session, redis, geocoder),
        ingest_emsc(session, redis, geocoder),
        return_exceptions=True,
    )
    total = 0
    for result in results:
        if isinstance(result, Exception):
            logger.exception("Earthquake source ingestion failed", exc_info=result)
            continue
        total += result
    return total


async def _normalize_many(events: list[EarthquakeCreate], session, redis, geocoder) -> int:  # noqa: ANN001
    saved = 0
    for event in events:
        if await normalize_and_save(event, session=session, redis=redis, geocoder=geocoder) is not None:
            saved += 1
    return saved
