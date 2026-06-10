from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.redis_client import create_redis_client
from app.routers import earthquakes as earthquakes_router
from app.routers import websocket as websocket_router
from app.schemas.earthquake import AlertLevel, IslandGroup, Source


def earthquake_payload(**overrides):
    base = {
        "id": uuid4(),
        "event_id": "us7000abcd",
        "source": Source.USGS,
        "magnitude": 5.4,
        "magnitude_type": "Mw",
        "depth_km": 18.0,
        "latitude": 14.5,
        "longitude": 121.0,
        "place": "Metro Manila",
        "province": "Metro Manila",
        "region": "NCR",
        "island_group": IslandGroup.LUZON,
        "felt": False,
        "tsunami_warning": False,
        "alert_level": AlertLevel.RED,
        "occurred_at": datetime(2026, 6, 10, 2, 30, tzinfo=UTC),
        "ingested_at": datetime(2026, 6, 10, 2, 31, tzinfo=UTC),
        "raw_data": {},
    }
    base.update(overrides)
    return base


class FakeRedis:
    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        return None


async def fake_db():
    yield object()


def test_earthquake_rest_endpoints(monkeypatch) -> None:
    item = earthquake_payload()

    async def fake_list_earthquakes(db, filters):  # noqa: ANN001
        return {"items": [item], "total": 1, "page": filters.page, "page_size": filters.page_size}

    async def fake_get_earthquake(db, earthquake_id):  # noqa: ANN001
        return item if str(earthquake_id) == str(item["id"]) else None

    async def fake_summary(db):  # noqa: ANN001
        return {
            "total_today": 1,
            "total_this_week": 3,
            "max_magnitude_today": 5.4,
            "avg_depth_today": 18.0,
            "most_affected_province": "Metro Manila",
            "counts_by_alert_level": {"red": 1},
            "counts_by_island_group": {"Luzon": 1},
            "hourly_counts": [],
        }

    async def fake_heatmap(db):  # noqa: ANN001
        return [{"lat": 14.5, "lon": 121.0, "magnitude": 5.4}]

    async def fake_provinces(db):  # noqa: ANN001
        return [{"province": "Metro Manila", "count": 1}]

    monkeypatch.setattr(earthquakes_router, "list_earthquakes", fake_list_earthquakes)
    monkeypatch.setattr(earthquakes_router, "get_earthquake_by_id", fake_get_earthquake)
    monkeypatch.setattr(earthquakes_router, "get_summary_stats", fake_summary)
    monkeypatch.setattr(earthquakes_router, "get_heatmap_points", fake_heatmap)
    monkeypatch.setattr(earthquakes_router, "get_province_counts", fake_provinces)

    app.dependency_overrides[get_db] = fake_db
    try:
        client = TestClient(app)
        response = client.get("/api/v1/earthquakes?min_magnitude=5.0")
        assert response.status_code == 200
        assert response.json()["total"] == 1

        detail = client.get(f"/api/v1/earthquakes/{item['id']}")
        assert detail.status_code == 200
        assert detail.json()["event_id"] == "us7000abcd"

        missing = client.get(f"/api/v1/earthquakes/{uuid4()}")
        assert missing.status_code == 404

        assert client.get("/api/v1/earthquakes/stats/summary").json()["total_today"] == 1
        assert client.get("/api/v1/earthquakes/stats/heatmap").json()[0]["lat"] == 14.5
        assert client.get("/api/v1/provinces").json()[0]["province"] == "Metro Manila"
    finally:
        app.dependency_overrides.clear()


def test_health_endpoint_reports_db_and_redis_ok(monkeypatch) -> None:
    async def fake_check_db() -> bool:
        return True

    monkeypatch.setattr("app.main.check_database", fake_check_db)
    app.dependency_overrides[create_redis_client] = lambda: FakeRedis()
    try:
        response = TestClient(app).get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["db"] == "ok"
        assert body["redis"] == "ok"
        assert "timestamp" in body
    finally:
        app.dependency_overrides.clear()


def test_health_endpoint_reports_degraded_instead_of_500(monkeypatch) -> None:
    async def failing_check_db() -> bool:
        raise RuntimeError("database unavailable")

    class FailingRedis:
        async def ping(self) -> bool:
            raise RuntimeError("redis unavailable")

        async def aclose(self) -> None:
            return None

    monkeypatch.setattr("app.main.check_database", failing_check_db)
    app.dependency_overrides[create_redis_client] = lambda: FailingRedis()
    try:
        response = TestClient(app).get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "degraded"
        assert body["db"] == "error"
        assert body["redis"] == "error"
    finally:
        app.dependency_overrides.clear()


def test_websocket_helpers_filter_rooms_and_broadcast_messages() -> None:
    event = {"event_id": "x", "province": "Metro Manila"}

    assert websocket_router.should_emit_to_room(event, "province:Metro Manila")
    assert not websocket_router.should_emit_to_room(event, "province:Cebu")
    assert websocket_router.should_emit_to_room(event, None)


@pytest.mark.asyncio
async def test_redis_listener_cleanup_does_not_raise_when_redis_is_down(monkeypatch) -> None:
    class FailingPubSub:
        async def subscribe(self, channel):  # noqa: ANN001
            raise RuntimeError("redis unavailable")

        async def listen(self):
            if False:
                yield {}

        async def unsubscribe(self, channel):  # noqa: ANN001
            raise RuntimeError("redis unavailable")

        async def aclose(self) -> None:
            raise RuntimeError("redis unavailable")

    class FailingRedis:
        def pubsub(self):
            return FailingPubSub()

        async def aclose(self) -> None:
            raise RuntimeError("redis unavailable")

    monkeypatch.setattr(websocket_router, "create_redis_client", lambda: FailingRedis())

    await websocket_router.redis_listener()
