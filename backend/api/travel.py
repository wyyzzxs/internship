"""API routes for travel planning helper capabilities."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from backend.tools import generate_checklist_text, get_weather_forecast, search_nearby_poi_data
from backend.tools.common import load_json


router = APIRouter(prefix="/api", tags=["travel"])


class ChecklistRequest(BaseModel):
    plan: dict[str, Any] | None = Field(default=None, description="Current itinerary JSON")
    weather: dict[str, Any] | list[dict[str, Any]] | None = Field(
        default=None, description="Weather payload returned by /api/weather"
    )
    people_type: str = Field(default="朋友", description="独自/情侣/亲子/朋友/商务")


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "ai-travel-planner"}


@router.get("/cities")
def list_cities() -> dict[str, Any]:
    return load_json("cities.json")


@router.get("/tags")
def list_tags() -> dict[str, Any]:
    return load_json("tags.json")


@router.get("/weather")
def get_weather_api(
    city: str = Query(..., description="城市中文名，例如：武汉"),
    start_date: str | None = Query(default=None, description="YYYY-MM-DD"),
    days: int = Query(default=3, ge=1, le=7),
) -> dict[str, Any]:
    return get_weather_forecast(city=city, start_date=start_date, days=days)


@router.get("/nearby-poi")
def nearby_poi_api(
    lat: float = Query(..., description="中心点纬度"),
    lng: float = Query(..., description="中心点经度"),
    radius_m: int = Query(default=1000, ge=100, le=5000),
    poi_type: str = Query(default="restaurant", description="restaurant/hotel/toilet/attraction"),
    limit: int = Query(default=8, ge=1, le=30),
    city: str | None = Query(default=None, description="城市中文名，可选"),
    keywords: str | None = Query(default=None, description="搜索关键词，可选"),
) -> dict[str, Any]:
    return search_nearby_poi_data(
        lat=lat,
        lng=lng,
        radius_m=radius_m,
        poi_type=poi_type,
        limit=limit,
        city=city,
        keywords=keywords,
    )


@router.post("/checklist")
def checklist_api(request: ChecklistRequest) -> dict[str, str]:
    return {
        "format": "markdown",
        "content": generate_checklist_text(
            plan=request.plan,
            weather=request.weather,
            people_type=request.people_type,
        ),
    }

