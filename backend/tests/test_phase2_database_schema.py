from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import ForeignKey, JSON, inspect

from app.database import make_async_database_url
from app.models.earthquake import AlertLog, Earthquake
from app.schemas.earthquake import (
    AlertLevel,
    EarthquakeCreate,
    EarthquakeFilter,
    EarthquakeListResponse,
    EarthquakeRead,
    IslandGroup,
    RealtimeEvent,
    Source,
    compute_alert_level,
)


def test_compute_alert_level_uses_magnitude_thresholds_and_shallow_upgrade() -> None:
    assert compute_alert_level(3.9, 50) == AlertLevel.GREEN
    assert compute_alert_level(4.0, 50) == AlertLevel.YELLOW
    assert compute_alert_level(5.0, 50) == AlertLevel.ORANGE
    assert compute_alert_level(6.0, 50) == AlertLevel.RED
    assert compute_alert_level(4.2, 10) == AlertLevel.ORANGE
    assert compute_alert_level(5.4, 10) == AlertLevel.RED
    assert compute_alert_level(7.1, 10) == AlertLevel.RED


def test_earthquake_create_defaults_and_read_serialization() -> None:
    occurred_at = datetime(2026, 6, 10, 2, 30, tzinfo=UTC)
    payload = EarthquakeCreate(
        event_id="us7000abcd",
        source=Source.USGS,
        magnitude=5.2,
        magnitude_type="Mw",
        depth_km=18.5,
        latitude=14.5,
        longitude=121.0,
        place="Metro Manila, Philippines",
        occurred_at=occurred_at,
        raw_data={"source": "fixture"},
    )

    assert payload.alert_level == AlertLevel.RED
    assert payload.felt is False
    assert payload.tsunami_warning is False

    read_model = EarthquakeRead(
        id=uuid4(),
        ingested_at=occurred_at,
        province="Metro Manila",
        region="NCR",
        island_group=IslandGroup.LUZON,
        **payload.model_dump(exclude={"province", "region", "island_group"}),
    )

    encoded = read_model.model_dump(mode="json")
    assert encoded["source"] == "USGS"
    assert encoded["alert_level"] == "red"
    assert encoded["occurred_at"] == "2026-06-10T02:30:00Z"


def test_list_filter_and_realtime_schemas_have_expected_shape() -> None:
    filters = EarthquakeFilter(min_magnitude=4.5, province="Cebu", limit=250)
    assert filters.page == 1
    assert filters.page_size == 100
    assert filters.limit == 250

    response = EarthquakeListResponse(items=[], total=0, page=1, page_size=100)
    assert response.model_dump() == {"items": [], "total": 0, "page": 1, "page_size": 100}

    event = RealtimeEvent(
        id=uuid4(),
        event_id="phivolcs-20260610-001",
        source=Source.PHIVOLCS,
        magnitude=4.7,
        magnitude_type="ML",
        depth_km=42.0,
        latitude=12.0,
        longitude=122.5,
        place="Sibuyan Sea",
        province=None,
        region=None,
        island_group=IslandGroup.VISAYAS,
        felt=False,
        tsunami_warning=False,
        alert_level=AlertLevel.YELLOW,
        occurred_at=datetime(2026, 6, 10, 4, 0, tzinfo=UTC),
    )
    assert event.model_dump(mode="json")["event_id"] == "phivolcs-20260610-001"


def test_earthquake_orm_table_contract() -> None:
    table = Earthquake.__table__

    expected_columns = {
        "id",
        "event_id",
        "source",
        "magnitude",
        "magnitude_type",
        "depth_km",
        "latitude",
        "longitude",
        "place",
        "province",
        "region",
        "island_group",
        "felt",
        "tsunami_warning",
        "alert_level",
        "occurred_at",
        "ingested_at",
        "raw_data",
    }

    assert expected_columns.issubset(table.columns.keys())
    assert table.c.id.primary_key
    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("source", "event_id") in unique_columns
    assert not table.c.occurred_at.nullable
    assert isinstance(table.c.raw_data.type, JSON)

    indexes = {tuple(index.expressions) for index in table.indexes}
    assert (table.c.occurred_at,) in indexes
    assert (table.c.magnitude,) in indexes
    assert (table.c.province,) in indexes
    assert (table.c.source,) in indexes


def test_alert_log_orm_links_to_earthquake() -> None:
    mapper = inspect(AlertLog)
    columns = AlertLog.__table__.columns

    assert columns.id.primary_key
    assert isinstance(next(iter(columns.earthquake_id.foreign_keys)), ForeignKey)
    assert columns.channel.type.enums == ["push", "sms", "telegram", "email"]
    assert columns.status.type.enums == ["sent", "failed"]
    assert "earthquake" in mapper.relationships


def test_database_url_helper_converts_supabase_pooler_urls_to_asyncpg() -> None:
    assert (
        make_async_database_url("postgresql://postgres:pass@db.example.com:5432/postgres")
        == "postgresql+asyncpg://postgres:pass@db.example.com:5432/postgres"
    )
    assert (
        make_async_database_url("postgresql+asyncpg://postgres:pass@db.example.com/postgres")
        == "postgresql+asyncpg://postgres:pass@db.example.com/postgres"
    )
