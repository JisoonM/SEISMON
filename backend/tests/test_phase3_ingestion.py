from datetime import UTC, datetime

import pytest

from app.schemas.earthquake import Source
from app.services.ingestion import (
    parse_emsc_events,
    parse_phivolcs_events,
    parse_usgs_feature_collection,
)


def test_parse_usgs_feature_collection_maps_geojson_to_create_schema() -> None:
    payload = {
        "features": [
            {
                "id": "us7000abcd",
                "properties": {
                    "mag": 5.4,
                    "magType": "Mw",
                    "place": "12 km W of Batangas, Philippines",
                    "time": 1_780_000_000_000,
                    "felt": 12,
                    "tsunami": 1,
                },
                "geometry": {"coordinates": [121.0, 14.0, 21.5]},
            }
        ]
    }

    events = parse_usgs_feature_collection(payload)

    assert len(events) == 1
    event = events[0]
    assert event.event_id == "us7000abcd"
    assert event.source == Source.USGS
    assert event.magnitude == 5.4
    assert event.depth_km == 21.5
    assert event.longitude == 121.0
    assert event.latitude == 14.0
    assert event.felt is True
    assert event.tsunami_warning is True
    assert event.occurred_at.tzinfo == UTC


def test_parse_phivolcs_events_converts_pht_table_rows_to_utc() -> None:
    html = """
    <table>
      <tr><th>Date - Time</th><th>Latitude</th><th>Longitude</th><th>Depth</th><th>Magnitude</th><th>Location</th></tr>
      <tr>
        <td>10 June 2026 - 10:30 AM</td>
        <td>14.50</td>
        <td>121.00</td>
        <td>18</td>
        <td>4.6</td>
        <td>Metro Manila felt</td>
      </tr>
    </table>
    """

    events = parse_phivolcs_events(html)

    assert len(events) == 1
    event = events[0]
    assert event.source == Source.PHIVOLCS
    assert event.event_id.startswith("phivolcs-20260610T023000")
    assert event.occurred_at == datetime(2026, 6, 10, 2, 30, tzinfo=UTC)
    assert event.magnitude == 4.6
    assert event.depth_km == 18
    assert event.felt is True


def test_parse_emsc_events_maps_fdsn_json_to_create_schema() -> None:
    payload = {
        "features": [
            {
                "id": "20260610_000001",
                "properties": {
                    "mag": 4.8,
                    "flynn_region": "Mindanao, Philippines",
                    "time": "2026-06-10T04:15:00.000Z",
                },
                "geometry": {"coordinates": [125.0, 7.0, 35.0]},
            }
        ]
    }

    events = parse_emsc_events(payload)

    assert len(events) == 1
    event = events[0]
    assert event.event_id == "20260610_000001"
    assert event.source == Source.EMSC
    assert event.place == "Mindanao, Philippines"
    assert event.occurred_at == datetime(2026, 6, 10, 4, 15, tzinfo=UTC)

