from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "PH Earthquake Monitor API"
    app_version: str = "0.1.0"
    environment: str = "development"
    secret_key: str = "change-me"

    database_url: Annotated[str, Field(alias="DATABASE_URL")] = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/earthquakes"
    )
    redis_url: Annotated[str, Field(alias="REDIS_URL")] = "redis://localhost:6379/0"

    phivolcs_url: Annotated[AnyUrl, Field(alias="PHIVOLCS_URL")] = (
        "https://www.phivolcs.dost.gov.ph/index.php/earthquake/earthquake-information3"
    )
    usgs_feed_url: Annotated[AnyUrl, Field(alias="USGS_FEED_URL")] = (
        "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
    )
    usgs_backfill_url: Annotated[AnyUrl, Field(alias="USGS_BACKFILL_URL")] = (
        "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
    )
    emsc_api_url: Annotated[AnyUrl, Field(alias="EMSC_API_URL")] = (
        "https://www.seismicportal.eu/fdsnws/event/1/query"
    )

    cors_origins: Annotated[str, Field(alias="CORS_ORIGINS")] = "http://localhost:3000"
    frontend_url: Annotated[str, Field(alias="FRONTEND_URL")] = "http://localhost:3000"

    firebase_credentials_json: Annotated[str | None, Field(alias="FIREBASE_CREDENTIALS_JSON")] = None
    telegram_bot_token: Annotated[str | None, Field(alias="TELEGRAM_BOT_TOKEN")] = None
    telegram_chat_id: Annotated[str | None, Field(alias="TELEGRAM_CHAT_ID")] = None
    semaphore_api_key: Annotated[str | None, Field(alias="SEMAPHORE_API_KEY")] = None
    alert_phone_numbers: Annotated[str, Field(alias="ALERT_PHONE_NUMBERS")] = ""
    resend_api_key: Annotated[str | None, Field(alias="RESEND_API_KEY")] = None
    alert_email_recipients: Annotated[str, Field(alias="ALERT_EMAIL_RECIPIENTS")] = ""
    mapbox_token: Annotated[str | None, Field(alias="MAPBOX_TOKEN")] = None
    sentry_dsn: Annotated[str | None, Field(alias="SENTRY_DSN")] = None
    ph_province_geojson_path: Annotated[str, Field(alias="PH_PROVINCE_GEOJSON_PATH")] = str(
        Path(__file__).resolve().parents[1] / "data" / "provinces.geojson"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
