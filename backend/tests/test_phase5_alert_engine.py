from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.config import Settings
from app.schemas.earthquake import AlertLevel, EarthquakeRead, IslandGroup, Source
from app.services.alert_engine import (
    DispatchResult,
    alert_channels_for,
    evaluate_alert_rules,
    evaluate_and_alert,
    format_sms_message,
    test_alerts as run_test_alerts,
)


def quake(**overrides):
    base = {
        "id": uuid4(),
        "event_id": "phivolcs-20260610-001",
        "source": Source.PHIVOLCS,
        "magnitude": 4.5,
        "magnitude_type": "ML",
        "depth_km": 35.0,
        "latitude": 14.5,
        "longitude": 121.0,
        "place": "Metro Manila",
        "province": "Metro Manila",
        "region": "NCR",
        "island_group": IslandGroup.LUZON,
        "felt": False,
        "tsunami_warning": False,
        "alert_level": AlertLevel.YELLOW,
        "occurred_at": datetime(2026, 6, 10, 2, 30, tzinfo=UTC),
        "ingested_at": datetime(2026, 6, 10, 2, 31, tzinfo=UTC),
        "raw_data": {},
    }
    base.update(overrides)
    return EarthquakeRead(**base)


class FakeSession:
    def __init__(self, recent_alert: bool = False):
        self.recent_alert = recent_alert
        self.added = []
        self.commits = 0

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1


@pytest.mark.parametrize(
    ("event", "should_alert", "expected_reason"),
    [
        (quake(magnitude=4.4, depth_km=35.0), False, None),
        (quake(magnitude=4.5, depth_km=35.0), True, "magnitude >= 4.5"),
        (quake(magnitude=3.4, depth_km=12.0), False, None),
        (quake(magnitude=3.5, depth_km=12.0), True, "shallow magnitude >= 3.5"),
        (quake(magnitude=6.0, depth_km=80.0), True, "magnitude >= 6.0"),
        (quake(magnitude=2.8, depth_km=80.0, tsunami_warning=True), True, "tsunami warning"),
    ],
)
def test_alert_rules_match_phase_5_thresholds(event, should_alert, expected_reason) -> None:
    evaluation = evaluate_alert_rules(event)

    assert evaluation.should_alert is should_alert
    if expected_reason:
        assert expected_reason in evaluation.reasons
    else:
        assert evaluation.reasons == []


def test_alert_channels_are_gated_by_magnitude() -> None:
    assert alert_channels_for(quake(magnitude=4.5)) == ["push", "telegram"]
    assert alert_channels_for(quake(magnitude=5.0)) == ["push", "sms", "telegram"]
    assert alert_channels_for(quake(magnitude=6.0)) == ["push", "sms", "telegram", "email"]


def test_sms_message_stays_within_semaphore_limit() -> None:
    message = format_sms_message(quake(magnitude=6.5, place="A very long offshore earthquake location near the Philippine Trench"))

    assert len(message) <= 160
    assert "M6.5" in message


@pytest.mark.asyncio
async def test_evaluate_and_alert_dispatches_allowed_channels_and_logs_results() -> None:
    event = quake(magnitude=6.2)
    session = FakeSession()
    calls = []

    async def fake_dispatch(channel, earthquake, settings):  # noqa: ANN001
        calls.append((channel, earthquake.event_id))
        status = "failed" if channel == "telegram" else "sent"
        return DispatchResult(channel=channel, recipient=f"{channel}:target", status=status, error_message=None)

    result = await evaluate_and_alert(
        event,
        session=session,
        dispatchers={"push": fake_dispatch, "sms": fake_dispatch, "telegram": fake_dispatch, "email": fake_dispatch},
        recent_alert_checker=lambda _session, _event: False,
    )

    assert result.triggered is True
    assert calls == [
        ("push", event.event_id),
        ("sms", event.event_id),
        ("telegram", event.event_id),
        ("email", event.event_id),
    ]
    assert len(session.added) == 4
    assert {log.status for log in session.added} == {"sent", "failed"}
    assert session.commits == 1


@pytest.mark.asyncio
async def test_evaluate_and_alert_suppresses_recent_duplicates() -> None:
    event = quake(magnitude=6.2)
    session = FakeSession(recent_alert=True)

    async def should_not_dispatch(channel, earthquake, settings):  # noqa: ANN001
        raise AssertionError("duplicate events must not dispatch alerts")

    result = await evaluate_and_alert(
        event,
        session=session,
        dispatchers={"push": should_not_dispatch},
        recent_alert_checker=lambda _session, _event: True,
    )

    assert result.triggered is False
    assert result.suppressed is True
    assert result.reasons == ["duplicate alert within 30 minutes"]
    assert session.added == []
    assert session.commits == 0


@pytest.mark.asyncio
async def test_dispatch_errors_redact_active_runtime_secrets() -> None:
    event = quake(magnitude=4.5)
    session = FakeSession()
    settings = Settings(RESEND_API_KEY="phase5-secret-token")

    async def exploding_dispatch(channel, earthquake, active_settings):  # noqa: ANN001
        raise RuntimeError(f"provider rejected token {active_settings.resend_api_key}")

    result = await evaluate_and_alert(
        event,
        session=session,
        settings=settings,
        dispatchers={"push": exploding_dispatch},
        recent_alert_checker=lambda _session, _event: False,
    )

    assert result.dispatch_results[0].status == "failed"
    assert "phase5-secret-token" not in result.dispatch_results[0].error_message
    assert "[redacted]" in result.dispatch_results[0].error_message
    assert "phase5-secret-token" not in session.added[0].error_message


@pytest.mark.asyncio
async def test_test_alerts_uses_mock_magnitude_6_5_event() -> None:
    session = FakeSession()

    async def fake_dispatch(channel, earthquake, settings):  # noqa: ANN001
        assert earthquake.magnitude == 6.5
        assert earthquake.event_id == "mock-m6.5-test-alert"
        return DispatchResult(channel=channel, recipient=f"{channel}:dry-run", status="sent")

    result = await run_test_alerts(
        session=session,
        dispatchers={"push": fake_dispatch, "sms": fake_dispatch, "telegram": fake_dispatch, "email": fake_dispatch},
        recent_alert_checker=lambda _session, _event: False,
    )

    assert result.triggered is True
    assert len(session.added) == 4


@pytest.mark.asyncio
async def test_test_alerts_defaults_to_safe_dry_run_dispatchers() -> None:
    session = FakeSession()

    result = await run_test_alerts(
        session=session,
        recent_alert_checker=lambda _session, _event: False,
    )

    assert result.triggered is True
    assert {dispatch.status for dispatch in result.dispatch_results} == {"sent"}
    assert {dispatch.recipient for dispatch in result.dispatch_results} == {
        "push:dry-run",
        "sms:dry-run",
        "telegram:dry-run",
        "email:dry-run",
    }
