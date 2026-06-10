from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.models.earthquake import Earthquake
from app.schemas.earthquake import EarthquakeCreate, IslandGroup, Source
from app.config import get_settings
from app.services.geocoder import PhilippineGeocoder
from app.services.normalizer import normalize_and_save


SIMPLE_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Metro Manila", "region": "NCR"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [120.9, 14.3],
                        [121.2, 14.3],
                        [121.2, 14.8],
                        [120.9, 14.8],
                        [120.9, 14.3],
                    ]
                ],
            },
        }
    ],
}


class ExistingResult:
    def __init__(self, existing: Earthquake | None) -> None:
        self.existing = existing

    def scalar_one_or_none(self) -> Earthquake | None:
        return self.existing


class FakeSession:
    def __init__(self, existing: Earthquake | None = None) -> None:
        self.existing = existing
        self.added: list[Earthquake] = []
        self.commits = 0

    async def execute(self, statement):  # noqa: ANN001
        return ExistingResult(self.existing)

    def add(self, instance: Earthquake) -> None:
        self.added.append(instance)

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, instance: Earthquake) -> None:
        if instance.id is None:
            instance.id = uuid4()


class FakeRedis:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    async def publish(self, channel: str, message: str) -> None:
        self.messages.append((channel, message))


def test_geocoder_returns_province_region_and_island_group() -> None:
    geocoder = PhilippineGeocoder.from_geojson(SIMPLE_GEOJSON)

    result = geocoder.point_in_province(14.5, 121.0)

    assert result is not None
    assert result.province == "Metro Manila"
    assert result.region == "NCR"
    assert result.island_group == IslandGroup.LUZON
    assert geocoder.point_in_province(0.0, 0.0) is None


def test_default_dataset_resolves_known_philippine_coordinates() -> None:
    geocoder = PhilippineGeocoder.from_path(get_settings().ph_province_geojson_path)

    metro_manila = geocoder.point_in_province(14.5, 121.0)
    assert metro_manila is not None
    assert metro_manila.province == "Metro Manila"
    assert metro_manila.region == "NCR"
    assert metro_manila.island_group == IslandGroup.LUZON

    mindanao = geocoder.point_in_province(7.0, 125.0)
    assert mindanao is not None
    assert mindanao.island_group == IslandGroup.MINDANAO

    assert geocoder.point_in_province(0.0, 0.0) is None


@pytest.mark.asyncio
async def test_normalize_and_save_enriches_persists_and_publishes_new_event() -> None:
    session = FakeSession()
    redis = FakeRedis()
    geocoder = PhilippineGeocoder.from_geojson(SIMPLE_GEOJSON)
    raw_event = EarthquakeCreate(
        event_id="us7000abcd",
        source=Source.USGS,
        magnitude=5.2,
        magnitude_type="Mw",
        depth_km=18.0,
        latitude=14.5,
        longitude=121.0,
        place="Metro Manila",
        occurred_at=datetime(2026, 6, 10, 2, 30, tzinfo=UTC),
        raw_data={"fixture": True},
    )

    saved = await normalize_and_save(raw_event, session=session, redis=redis, geocoder=geocoder)

    assert saved is not None
    assert saved.province == "Metro Manila"
    assert saved.region == "NCR"
    assert saved.island_group == IslandGroup.LUZON.value
    assert session.added == [saved]
    assert session.commits == 1
    assert redis.messages[0][0] == "eq:new_event"
    assert '"event_id":"us7000abcd"' in redis.messages[0][1]


@pytest.mark.asyncio
async def test_normalize_and_save_skips_duplicate_non_phivolcs_event() -> None:
    existing = Earthquake(
        event_id="us7000abcd",
        source=Source.USGS.value,
        magnitude=4.8,
        magnitude_type="Mw",
        depth_km=40.0,
        latitude=14.5,
        longitude=121.0,
        place="Metro Manila",
        alert_level="yellow",
        occurred_at=datetime(2026, 6, 10, 2, 0, tzinfo=UTC),
        raw_data={},
    )
    session = FakeSession(existing=existing)
    redis = FakeRedis()

    result = await normalize_and_save(
        EarthquakeCreate(
            event_id="us7000abcd",
            source=Source.USGS,
            magnitude=5.8,
            magnitude_type="Mw",
            depth_km=12.0,
            latitude=14.5,
            longitude=121.0,
            place="Metro Manila",
            occurred_at=datetime(2026, 6, 10, 2, 30, tzinfo=UTC),
            raw_data={},
        ),
        session=session,
        redis=redis,
        geocoder=PhilippineGeocoder.from_geojson(SIMPLE_GEOJSON),
    )

    assert result is existing
    assert session.added == []
    assert session.commits == 0
    assert redis.messages == []
