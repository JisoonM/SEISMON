from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


def compute_alert_level(magnitude: float, depth_km: float) -> AlertLevel:
    if magnitude < 4.0:
        base_index = 0
    elif magnitude < 5.0:
        base_index = 1
    elif magnitude < 6.0:
        base_index = 2
    else:
        base_index = 3

    if depth_km < 30:
        base_index = min(base_index + 1, 3)

    return [AlertLevel.GREEN, AlertLevel.YELLOW, AlertLevel.ORANGE, AlertLevel.RED][base_index]


class EarthquakeBase(BaseModel):
    event_id: str = Field(min_length=1, max_length=128)
    source: Source
    magnitude: float = Field(ge=0, le=10)
    magnitude_type: str = Field(min_length=1, max_length=24)
    depth_km: float = Field(ge=0)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    place: str = Field(min_length=1, max_length=512)
    province: str | None = Field(default=None, max_length=128)
    region: str | None = Field(default=None, max_length=128)
    island_group: IslandGroup | None = None
    felt: bool = False
    tsunami_warning: bool = False
    alert_level: AlertLevel | None = None
    occurred_at: datetime
    raw_data: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def fill_alert_level(self) -> "EarthquakeBase":
        if self.alert_level is None:
            self.alert_level = compute_alert_level(self.magnitude, self.depth_km)
        return self


class EarthquakeCreate(EarthquakeBase):
    pass


class EarthquakeRead(EarthquakeBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    alert_level: AlertLevel
    ingested_at: datetime


class EarthquakeListResponse(BaseModel):
    items: list[EarthquakeRead]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=500)


class EarthquakeFilter(BaseModel):
    min_magnitude: float | None = Field(default=None, ge=0, le=10)
    max_magnitude: float | None = Field(default=None, ge=0, le=10)
    province: str | None = None
    island_group: IslandGroup | None = None
    source: Source | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    limit: int = Field(default=100, ge=1, le=500)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1, le=500)

    @model_validator(mode="after")
    def validate_magnitude_range(self) -> "EarthquakeFilter":
        if (
            self.min_magnitude is not None
            and self.max_magnitude is not None
            and self.min_magnitude > self.max_magnitude
        ):
            raise ValueError("min_magnitude cannot be greater than max_magnitude")
        return self


class RealtimeEvent(BaseModel):
    id: UUID
    event_id: str
    source: Source
    magnitude: float
    magnitude_type: str
    depth_km: float
    latitude: float
    longitude: float
    place: str
    province: str | None
    region: str | None
    island_group: IslandGroup | None
    felt: bool
    tsunami_warning: bool
    alert_level: AlertLevel
    occurred_at: datetime
