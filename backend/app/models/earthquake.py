from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Source(str, Enum):
    PHIVOLCS = "PHIVOLCS"
    USGS = "USGS"
    EMSC = "EMSC"


class IslandGroup(str, Enum):
    LUZON = "Luzon"
    VISAYAS = "Visayas"
    MINDANAO = "Mindanao"
    OUTSIDE_PH = "Outside PH"


class AlertLevel(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    ORANGE = "orange"
    RED = "red"


class AlertChannel(str, Enum):
    PUSH = "push"
    SMS = "sms"
    TELEGRAM = "telegram"
    EMAIL = "email"


class AlertStatus(str, Enum):
    SENT = "sent"
    FAILED = "failed"


class Earthquake(Base):
    __tablename__ = "earthquakes"
    __table_args__ = (
        UniqueConstraint("source", "event_id", name="uq_earthquakes_source_event_id"),
        Index("ix_earthquakes_occurred_at", "occurred_at"),
        Index("ix_earthquakes_magnitude", "magnitude"),
        Index("ix_earthquakes_province", "province"),
        Index("ix_earthquakes_source", "source"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source: Mapped[Source] = mapped_column(
        SQLEnum(Source, name="earthquake_source", values_callable=lambda values: [item.value for item in values]),
        nullable=False,
    )
    magnitude: Mapped[float] = mapped_column(Float, nullable=False)
    magnitude_type: Mapped[str] = mapped_column(String(24), nullable=False)
    depth_km: Mapped[float] = mapped_column(Float, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    place: Mapped[str] = mapped_column(String(512), nullable=False)
    province: Mapped[str | None] = mapped_column(String(128), nullable=True)
    region: Mapped[str | None] = mapped_column(String(128), nullable=True)
    island_group: Mapped[IslandGroup | None] = mapped_column(
        SQLEnum(
            IslandGroup,
            name="island_group",
            values_callable=lambda values: [item.value for item in values],
        ),
        nullable=True,
    )
    felt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    tsunami_warning: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    alert_level: Mapped[AlertLevel] = mapped_column(
        SQLEnum(AlertLevel, name="alert_level", values_callable=lambda values: [item.value for item in values]),
        nullable=False,
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    alert_logs: Mapped[list["AlertLog"]] = relationship(
        back_populates="earthquake",
        cascade="all, delete-orphan",
    )


class AlertLog(Base):
    __tablename__ = "alert_log"
    __table_args__ = (Index("ix_alert_log_earthquake_id", "earthquake_id"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    earthquake_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("earthquakes.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(
        SQLEnum("push", "sms", "telegram", "email", name="alert_channel"),
        nullable=False,
    )
    recipient: Mapped[str] = mapped_column(String(320), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    status: Mapped[str] = mapped_column(SQLEnum("sent", "failed", name="alert_status"), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    earthquake: Mapped[Earthquake] = relationship(back_populates="alert_logs")
