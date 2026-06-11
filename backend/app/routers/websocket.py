from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import socketio
from fastapi import APIRouter
from sqlalchemy import desc, select

from app.config import get_settings
from app.database import async_session
from app.models.earthquake import Earthquake
from app.redis_client import create_redis_client
from app.schemas.earthquake import EarthquakeRead

router = APIRouter()
settings = get_settings()
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
)
socket_app = socketio.ASGIApp(sio)
logger = logging.getLogger(__name__)


def should_emit_to_room(event: dict[str, Any], room: str | None) -> bool:
    if room is None:
        return True
    if room.startswith("province:"):
        return event.get("province") == room.split(":", 1)[1]
    return True


@sio.event
async def connect(sid, environ):  # noqa: ANN001
    await hydrate_recent_events(sid)
    await sio.emit("heartbeat", {"status": "connected"}, to=sid)


@sio.event
async def join(sid, data):  # noqa: ANN001
    room = data.get("room") if isinstance(data, dict) else None
    if room:
        await sio.enter_room(sid, room)


@sio.event
async def disconnect(sid):  # noqa: ANN001
    return None


async def broadcast_redis_message(message: str) -> None:
    event = json.loads(message)
    await sio.emit("earthquake:new", event)
    province = event.get("province")
    if province:
        await sio.emit("earthquake:new", event, room=f"province:{province}")


async def redis_listener() -> None:
    redis = create_redis_client()
    pubsub = redis.pubsub()
    try:
        await pubsub.subscribe("eq:new_event")
        async for message in pubsub.listen():
            if message.get("type") == "message":
                await broadcast_redis_message(str(message.get("data")))
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.warning("Redis Socket.IO listener disabled because Redis is unavailable: %s", exc)
    finally:
        try:
            await pubsub.unsubscribe("eq:new_event")
        except Exception as exc:
            logger.warning("Redis Socket.IO listener unsubscribe skipped: %s", exc)
        try:
            await pubsub.aclose()
        except Exception as exc:
            logger.warning("Redis Socket.IO listener pubsub cleanup skipped: %s", exc)
        try:
            await redis.aclose()
        except Exception as exc:
            logger.warning("Redis Socket.IO listener client cleanup skipped: %s", exc)


async def heartbeat_loop() -> None:
    while True:
        await sio.emit("heartbeat", {"status": "ok"})
        await asyncio.sleep(30)


async def hydrate_recent_events(sid: str) -> None:
    try:
        async with async_session() as session:
            result = await session.execute(select(Earthquake).order_by(desc(Earthquake.occurred_at)).limit(20))
            events = [
                EarthquakeRead.model_validate(event).model_dump(mode="json")
                for event in result.scalars().all()
            ]
    except Exception as exc:
        logger.warning("Socket.IO hydrate returned empty events because database is unavailable: %s", exc)
        events = []
    await sio.emit("earthquake:hydrate", events, to=sid)
