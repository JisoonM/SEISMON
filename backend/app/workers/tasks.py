from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from app.database import async_session
from app.config import get_settings
from app.redis_client import create_redis_client
from app.services.geocoder import PhilippineGeocoder
from app.services.ingestion import ingest_phivolcs
from app.services.ingestion import ingest_all_sources as ingest_all_sources_async
from app.services.normalizer import cleanup_old_events as cleanup_old_events_async
from celery_app import celery_app


def _load_geocoder() -> PhilippineGeocoder:
    path = get_settings().ph_province_geojson_path
    return PhilippineGeocoder.from_path(path)


@celery_app.task(name="app.workers.tasks.ingest_all_sources")
def ingest_all_sources() -> int:
    async def run() -> int:
        redis = create_redis_client()
        async with async_session() as session:
            try:
                return await ingest_all_sources_async(session, redis, _load_geocoder())
            finally:
                await redis.aclose()

    return asyncio.run(run())


@celery_app.task(name="app.workers.tasks.backfill_phivolcs")
def backfill_phivolcs() -> int:
    async def run() -> int:
        redis = create_redis_client()
        async with async_session() as session:
            try:
                return await ingest_phivolcs(session, redis, _load_geocoder())
            finally:
                await redis.aclose()

    return asyncio.run(run())


@celery_app.task(name="app.workers.tasks.cleanup_old_events")
def cleanup_old_events() -> int:
    async def run() -> int:
        cutoff = datetime.now(UTC) - timedelta(days=90)
        async with async_session() as session:
            return await cleanup_old_events_async(session, older_than=cutoff)

    return asyncio.run(run())
