"""后端 API 客户端 — Mock 模式 + 真实 API 统一入口。"""

from __future__ import annotations

import os
from typing import Any

import requests

from utils.data_loader import enrich_plan
from utils.mock_data import get_mock_chat_response, get_mock_plan

USE_MOCK = os.getenv("USE_MOCK", "true").lower() == "true"
BACKEND_URL = os.getenv("BACKEND_URL") or os.getenv("API_BASE_URL", "http://localhost:8000")


def _url(path: str) -> str:
    return f"{BACKEND_URL.rstrip('/')}/{path.lstrip('/')}"


def _post(path: str, payload: dict) -> dict:
    resp = requests.post(_url(path), json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def _get(path: str, params: dict | None = None) -> dict:
    resp = requests.get(_url(path), params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_plan(request: dict) -> dict:
    if USE_MOCK:
        resp = get_mock_plan(**request)
        resp["plan"] = enrich_plan(resp["plan"])
        return resp
    return _post("/api/plan", request)


def fetch_chat(session_id: str, message: str, current_plan: dict | None = None) -> dict:
    if USE_MOCK:
        return get_mock_chat_response(message, current_plan)
    return _post(
        "/api/chat",
        {
            "session_id": session_id,
            "message": message,
            "current_plan": current_plan,
        },
    )


def get_weather(city: str, start_date: str, days: int) -> dict[str, Any]:
    return _get("/api/weather", {"city": city, "start_date": start_date, "days": days})


def get_nearby_poi(
    lat: float,
    lng: float,
    city: str,
    poi_type: str = "restaurant",
    radius_m: int = 1000,
    limit: int = 8,
) -> dict[str, Any]:
    return _get(
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
    return _post("/api/checklist", payload).get("content", "")


def check_health() -> dict:
    if USE_MOCK:
        return {"status": "ok", "mode": "mock"}
    return _get("/api/health")
