"""Small HTTP client for the Streamlit frontend."""

from __future__ import annotations

import os
from typing import Any

import requests


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def _url(path: str) -> str:
    return f"{API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"


def get_json(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.get(_url(path), params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(_url(path), json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def get_weather(city: str, start_date: str, days: int) -> dict[str, Any]:
    return get_json("/api/weather", {"city": city, "start_date": start_date, "days": days})


def get_nearby_poi(
    lat: float,
    lng: float,
    city: str,
    poi_type: str = "restaurant",
    radius_m: int = 1000,
    limit: int = 8,
) -> dict[str, Any]:
    return get_json(
        "/api/nearby-poi",
        {
            "lat": lat,
            "lng": lng,
            "city": city,
            "poi_type": poi_type,
            "radius_m": radius_m,
            "limit": limit,
        },
    )


def generate_checklist(plan: dict[str, Any], weather: dict[str, Any], people_type: str) -> str:
    payload = {"plan": plan, "weather": weather, "people_type": people_type}
    return post_json("/api/checklist", payload).get("content", "")

