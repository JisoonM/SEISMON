from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shapely.geometry import Point, shape
from shapely.errors import ShapelyError
from shapely.geometry.base import BaseGeometry

from app.schemas.earthquake import IslandGroup


@dataclass(frozen=True)
class ProvinceMatch:
    province: str
    region: str
    island_group: IslandGroup


def island_group_for_region(region: str | None) -> IslandGroup:
    normalized = (region or "").lower()
    if any(token in normalized for token in ["ncr", "car", "iloc", "cagayan", "central luzon", "calabarzon", "mimaropa", "bicol"]):
        return IslandGroup.LUZON
    if any(token in normalized for token in ["western visayas", "central visayas", "eastern visayas", "negros"]):
        return IslandGroup.VISAYAS
    if any(token in normalized for token in ["zamboanga", "northern mindanao", "davao", "soccsksargen", "caraga", "barmm", "mindanao"]):
        return IslandGroup.MINDANAO
    return IslandGroup.OUTSIDE_PH


def _normalize_province_name(province: str) -> str:
    if province.lower() == "metropolitan manila":
        return "Metro Manila"
    return province


def _normalize_region_name(region: str) -> str:
    if region.lower() == "metropolitan manila":
        return "NCR"
    return region


class PhilippineGeocoder:
    def __init__(self, boundaries: list[tuple[BaseGeometry, ProvinceMatch]]) -> None:
        self.boundaries = boundaries

    @classmethod
    def from_geojson(cls, payload: dict[str, Any]) -> "PhilippineGeocoder":
        boundaries: list[tuple[BaseGeometry, ProvinceMatch]] = []
        for feature in payload.get("features", []):
            geometry_payload = feature.get("geometry")
            if not geometry_payload:
                continue
            properties = feature.get("properties") or {}
            province = _normalize_province_name(str(
                properties.get("name")
                or properties.get("NAME_1")
                or properties.get("province")
                or properties.get("PROVINCE")
                or properties.get("ADM2_EN")
                or "Unknown"
            ))
            region = _normalize_region_name(str(properties.get("region") or properties.get("REGION") or properties.get("adm1_en") or ""))
            try:
                geometry = shape(geometry_payload)
            except (TypeError, ValueError, ShapelyError):
                continue
            boundaries.append((geometry, ProvinceMatch(province=province, region=region, island_group=island_group_for_region(region))))
        return cls(boundaries)

    @classmethod
    def from_path(cls, path: str | Path) -> "PhilippineGeocoder":
        with Path(path).open("r", encoding="utf-8") as handle:
            return cls.from_geojson(json.load(handle))

    def point_in_province(self, lat: float, lon: float) -> ProvinceMatch | None:
        point = Point(lon, lat)
        for geometry, match in self.boundaries:
            if geometry.contains(point) or geometry.touches(point):
                return match
        return None


def point_in_province(lat: float, lon: float, geocoder: PhilippineGeocoder) -> ProvinceMatch | None:
    return geocoder.point_in_province(lat, lon)
