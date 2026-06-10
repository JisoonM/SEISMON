import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

import httpx
from sqlalchemy import select

from app.config import Settings, get_settings
from app.database import async_session
from app.models.earthquake import AlertLog, Earthquake
from app.schemas.earthquake import AlertLevel, EarthquakeRead, IslandGroup, Source

AlertChannel = Literal["push", "sms", "telegram", "email"]
AlertStatus = Literal["sent", "failed"]
Dispatcher = Callable[[AlertChannel, EarthquakeRead, Settings], Awaitable["DispatchResult"]]
RecentAlertChecker = Callable[[Any, EarthquakeRead], bool | Awaitable[bool]]

DUPLICATE_WINDOW = timedelta(minutes=30)
SEMAPHORE_URL = "https://api.semaphore.co/api/v4/messages"
RESEND_URL = "https://api.resend.com/emails"


@dataclass(frozen=True)
class DispatchResult:
    channel: AlertChannel
    recipient: str
    status: AlertStatus
    error_message: str | None = None


@dataclass(frozen=True)
class AlertRuleEvaluation:
    should_alert: bool
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AlertRunResult:
    triggered: bool
    suppressed: bool
    reasons: list[str]
    channels: list[AlertChannel] = field(default_factory=list)
    dispatch_results: list[DispatchResult] = field(default_factory=list)


def evaluate_alert_rules(earthquake: EarthquakeRead) -> AlertRuleEvaluation:
    reasons: list[str] = []

    if earthquake.magnitude >= 4.5:
        reasons.append("magnitude >= 4.5")
    if earthquake.magnitude >= 3.5 and earthquake.depth_km < 20:
        reasons.append("shallow magnitude >= 3.5")
    if earthquake.magnitude >= 6.0:
        reasons.append("magnitude >= 6.0")
    if earthquake.tsunami_warning:
        reasons.append("tsunami warning")

    return AlertRuleEvaluation(should_alert=bool(reasons), reasons=reasons)


def alert_channels_for(earthquake: EarthquakeRead) -> list[AlertChannel]:
    channels: list[AlertChannel] = ["push", "telegram"]
    if earthquake.magnitude >= 5.0:
        channels.insert(1, "sms")
    if earthquake.magnitude >= 6.0:
        channels.append("email")
    return channels


def format_sms_message(earthquake: EarthquakeRead) -> str:
    occurred = earthquake.occurred_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
    province = earthquake.province or earthquake.place
    message = f"PH quake alert: M{earthquake.magnitude:.1f}, {earthquake.depth_km:.0f}km deep, {province}, {occurred}."
    return message[:160]


def format_telegram_message(earthquake: EarthquakeRead) -> str:
    province = earthquake.province or "Philippines"
    return (
        f"*PH Earthquake Alert*\n"
        f"Magnitude: *M{earthquake.magnitude:.1f}* ({earthquake.magnitude_type})\n"
        f"Depth: {earthquake.depth_km:.1f} km\n"
        f"Location: {earthquake.place}\n"
        f"Province: {province}\n"
        f"Time: {earthquake.occurred_at.astimezone(UTC).isoformat()}"
    )


def island_topic(earthquake: EarthquakeRead) -> str | None:
    if earthquake.island_group in {IslandGroup.LUZON, IslandGroup.VISAYAS, IslandGroup.MINDANAO}:
        return f"island_{earthquake.island_group.value.lower()}"
    return None


def _split_recipients(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _public_map_url(settings: Settings, earthquake: EarthquakeRead) -> str:
    return f"{settings.frontend_url.rstrip('/')}/?event={earthquake.id}"


def _safe_error(exc: Exception | str, settings: Settings | None = None) -> str:
    message = str(exc)
    active_settings = settings or get_settings()
    for secret in (
        active_settings.firebase_credentials_json,
        active_settings.telegram_bot_token,
        active_settings.semaphore_api_key,
        active_settings.resend_api_key,
    ):
        if secret and secret in message:
            message = message.replace(secret, "[redacted]")
    return message[:500]


async def has_recent_alert(session: Any, earthquake: EarthquakeRead) -> bool:
    cutoff = datetime.now(UTC) - DUPLICATE_WINDOW
    stmt = (
        select(AlertLog.id)
        .join(Earthquake, AlertLog.earthquake_id == Earthquake.id)
        .where(Earthquake.event_id == earthquake.event_id, AlertLog.sent_at >= cutoff)
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def send_push_notification(channel: AlertChannel, earthquake: EarthquakeRead, settings: Settings) -> DispatchResult:
    if not settings.firebase_credentials_json:
        return DispatchResult(channel=channel, recipient="topic:all", status="failed", error_message="Firebase not configured")

    try:
        import firebase_admin
        from firebase_admin import credentials, messaging

        if not firebase_admin._apps:
            credential_data = settings.firebase_credentials_json
            credential = (
                credentials.Certificate(json.loads(credential_data))
                if credential_data.strip().startswith("{")
                else credentials.Certificate(str(Path(credential_data)))
            )
            firebase_admin.initialize_app(credential)

        topics = ["all"]
        topic = island_topic(earthquake)
        if topic:
            topics.append(topic)

        for topic_name in topics:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=f"M{earthquake.magnitude:.1f} Earthquake Alert",
                    body=f"{earthquake.place} - depth {earthquake.depth_km:.1f} km",
                ),
                data={"event_id": earthquake.event_id, "earthquake_id": str(earthquake.id)},
                topic=topic_name,
            )
            messaging.send(message)

        return DispatchResult(channel=channel, recipient=",".join(f"topic:{topic}" for topic in topics), status="sent")
    except Exception as exc:  # pragma: no cover - real SDK path is exercised only with credentials.
        return DispatchResult(channel=channel, recipient="topic:all", status="failed", error_message=_safe_error(exc, settings))


async def send_sms(channel: AlertChannel, earthquake: EarthquakeRead, settings: Settings) -> DispatchResult:
    recipients = _split_recipients(settings.alert_phone_numbers)
    if not settings.semaphore_api_key or not recipients:
        return DispatchResult(channel=channel, recipient="sms:configured-recipients", status="failed", error_message="Semaphore SMS not configured")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            for recipient in recipients:
                response = await client.post(
                    SEMAPHORE_URL,
                    data={
                        "apikey": settings.semaphore_api_key,
                        "number": recipient,
                        "message": format_sms_message(earthquake),
                    },
                )
                response.raise_for_status()
        return DispatchResult(channel=channel, recipient=",".join(recipients), status="sent")
    except Exception as exc:
        return DispatchResult(channel=channel, recipient=",".join(recipients), status="failed", error_message=_safe_error(exc, settings))


async def send_telegram(channel: AlertChannel, earthquake: EarthquakeRead, settings: Settings) -> DispatchResult:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return DispatchResult(channel=channel, recipient="telegram:configured-chat", status="failed", error_message="Telegram not configured")

    try:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import ExtBot

        bot = ExtBot(settings.telegram_bot_token)
        await bot.send_message(
            chat_id=settings.telegram_chat_id,
            text=format_telegram_message(earthquake),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("View on Map", url=_public_map_url(settings, earthquake))]]
            ),
        )
        return DispatchResult(channel=channel, recipient=settings.telegram_chat_id, status="sent")
    except Exception as exc:
        return DispatchResult(channel=channel, recipient=settings.telegram_chat_id, status="failed", error_message=_safe_error(exc, settings))


async def send_email(channel: AlertChannel, earthquake: EarthquakeRead, settings: Settings) -> DispatchResult:
    recipients = _split_recipients(settings.alert_email_recipients)
    if not settings.resend_api_key or not recipients:
        return DispatchResult(channel=channel, recipient="email:configured-recipients", status="failed", error_message="Resend email not configured")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                RESEND_URL,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": "Philippines Earthquake Monitor <alerts@resend.dev>",
                    "to": recipients,
                    "subject": f"M{earthquake.magnitude:.1f} Philippines Earthquake Alert",
                    "html": (
                        f"<h1>M{earthquake.magnitude:.1f} Earthquake Alert</h1>"
                        f"<p>{earthquake.place}</p>"
                        f"<p>Depth: {earthquake.depth_km:.1f} km</p>"
                        f"<p><a href='{_public_map_url(settings, earthquake)}'>View on Map</a></p>"
                    ),
                },
            )
            response.raise_for_status()
        return DispatchResult(channel=channel, recipient=",".join(recipients), status="sent")
    except Exception as exc:
        return DispatchResult(channel=channel, recipient=",".join(recipients), status="failed", error_message=_safe_error(exc, settings))


DEFAULT_DISPATCHERS: dict[AlertChannel, Dispatcher] = {
    "push": send_push_notification,
    "sms": send_sms,
    "telegram": send_telegram,
    "email": send_email,
}


async def send_dry_run(channel: AlertChannel, earthquake: EarthquakeRead, settings: Settings) -> DispatchResult:
    return DispatchResult(channel=channel, recipient=f"{channel}:dry-run", status="sent")


DRY_RUN_DISPATCHERS: dict[AlertChannel, Dispatcher] = {
    "push": send_dry_run,
    "sms": send_dry_run,
    "telegram": send_dry_run,
    "email": send_dry_run,
}


async def _maybe_await(value: bool | Awaitable[bool]) -> bool:
    if asyncio.iscoroutine(value) or isinstance(value, Awaitable):
        return bool(await value)
    return bool(value)


async def _dispatch_safely(
    channel: AlertChannel,
    earthquake: EarthquakeRead,
    settings: Settings,
    dispatcher: Dispatcher,
) -> DispatchResult:
    try:
        return await dispatcher(channel, earthquake, settings)
    except Exception as exc:
        return DispatchResult(channel=channel, recipient=f"{channel}:unknown", status="failed", error_message=_safe_error(exc, settings))


async def _run_evaluation(
    earthquake: EarthquakeRead,
    session: Any,
    settings: Settings,
    dispatchers: dict[AlertChannel, Dispatcher],
    recent_alert_checker: RecentAlertChecker,
) -> AlertRunResult:
    evaluation = evaluate_alert_rules(earthquake)
    if not evaluation.should_alert:
        return AlertRunResult(triggered=False, suppressed=False, reasons=evaluation.reasons)

    if await _maybe_await(recent_alert_checker(session, earthquake)):
        return AlertRunResult(triggered=False, suppressed=True, reasons=["duplicate alert within 30 minutes"])

    channels = alert_channels_for(earthquake)
    results = await asyncio.gather(
        *[
            _dispatch_safely(channel, earthquake, settings, dispatchers[channel])
            for channel in channels
            if channel in dispatchers
        ]
    )

    for result in results:
        session.add(
            AlertLog(
                earthquake_id=earthquake.id,
                channel=result.channel,
                recipient=result.recipient,
                status=result.status,
                error_message=result.error_message,
            )
        )
    await session.commit()

    return AlertRunResult(
        triggered=True,
        suppressed=False,
        reasons=evaluation.reasons,
        channels=channels,
        dispatch_results=list(results),
    )


async def evaluate_and_alert(
    earthquake: EarthquakeRead,
    *,
    session: Any | None = None,
    settings: Settings | None = None,
    dispatchers: dict[AlertChannel, Dispatcher] | None = None,
    recent_alert_checker: RecentAlertChecker = has_recent_alert,
) -> AlertRunResult:
    active_settings = settings or get_settings()
    active_dispatchers = dispatchers or DEFAULT_DISPATCHERS

    if session is not None:
        return await _run_evaluation(earthquake, session, active_settings, active_dispatchers, recent_alert_checker)

    async with async_session() as db:
        return await _run_evaluation(earthquake, db, active_settings, active_dispatchers, recent_alert_checker)


async def test_alerts(
    *,
    session: Any | None = None,
    settings: Settings | None = None,
    dispatchers: dict[AlertChannel, Dispatcher] | None = None,
    recent_alert_checker: RecentAlertChecker = has_recent_alert,
    dry_run: bool = True,
) -> AlertRunResult:
    now = datetime.now(UTC)
    mock_event = EarthquakeRead(
        id=UUID("00000000-0000-0000-0000-000000000065"),
        event_id="mock-m6.5-test-alert",
        source=Source.PHIVOLCS,
        magnitude=6.5,
        magnitude_type="Mw",
        depth_km=12.0,
        latitude=14.5,
        longitude=121.0,
        place="Mock Phase 5 Alert Drill, Philippines",
        province="Metro Manila",
        region="NCR",
        island_group=IslandGroup.LUZON,
        felt=True,
        tsunami_warning=False,
        alert_level=AlertLevel.RED,
        occurred_at=now,
        ingested_at=now,
        raw_data={"mock": True},
    )
    return await evaluate_and_alert(
        mock_event,
        session=session,
        settings=settings,
        dispatchers=dispatchers or (DRY_RUN_DISPATCHERS if dry_run else DEFAULT_DISPATCHERS),
        recent_alert_checker=recent_alert_checker,
    )


test_alerts.__test__ = False
