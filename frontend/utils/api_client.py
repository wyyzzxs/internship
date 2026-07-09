"""后端 API 客户端 — Mock 模式 + 真实 API 统一入口。"""

from __future__ import annotations

import os
from typing import Any

import requests

from utils.data_loader import enrich_plan
from utils.mock_chat import get_mock_chat_response
from utils.mock_data import get_mock_plan

# 关键:默认调真实后端。之前默认 "true" 导致前端永远走本地 mock,
# 改 "false" 后只要 .env 显式设 USE_MOCK=true 才退化到 mock。
USE_MOCK = os.getenv("USE_MOCK", "false").lower() == "true"
BACKEND_URL = os.getenv("BACKEND_URL") or os.getenv("API_BASE_URL", "http://localhost:8000")

# 前端表单文案 → 后端 AgentRequest PeopleType
PEOPLE_MAP = {
    "情侣出游": "情侣",
    "亲子家庭": "亲子",
    "独自旅行": "独自",
    "朋友结伴": "朋友",
    "爸妈长辈": "朋友",
}


def _normalize_request(request: dict) -> dict:
    payload = dict(request)
    people = payload.get("people", "情侣")
    payload["people"] = PEOPLE_MAP.get(people, people)
    if payload.get("special") is None and "special" in payload:
        payload.pop("special", None)
    return payload


def _unwrap_plan_response(data: dict) -> dict:
    """PlanAgent 可能返回嵌套 PlanResponse，解包为前端可用的 plan。"""
    plan = data.get("plan")
    if isinstance(plan, dict) and "trip_summary" not in plan:
        inner = plan.get("plan")
        if isinstance(inner, dict) and "trip_summary" in inner:
            data["plan"] = inner
            if plan.get("session_id") and not data.get("session_id"):
                data["session_id"] = plan["session_id"]
            if plan.get("error") and not data.get("warning"):
                data["warning"] = plan["error"]
    return data


def _url(path: str) -> str:
    return f"{BACKEND_URL.rstrip('/')}/{path.lstrip('/')}"


def _post(path: str, payload: dict) -> dict:
    # LLM 多轮 + reflect-loop 最坏情况能跑到 2~3 分钟,60 秒不够
    resp = requests.post(_url(path), json=payload, timeout=180)
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
    data = _post("/api/plan", _normalize_request(request))
    data = _unwrap_plan_response(data)
    if data.get("plan"):
        data["plan"] = enrich_plan(data["plan"])
    return data


def fetch_chat(session_id: str, message: str, current_plan: dict | None = None) -> dict:
    if USE_MOCK:
        return get_mock_chat_response(message, current_plan)
    try:
        result = _post(
            "/api/chat",
            {
                "session_id": session_id,
                "message": message,
                "current_plan": current_plan,
            },
        )
        if result.get("updated_plan"):
            result["updated_plan"] = enrich_plan(result["updated_plan"])
        result.setdefault("success", True)
        return result
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            return {
                "success": False,
                "reply": "后端尚未提供 /api/chat 接口，请确认朱(D) 的 API 路由已合并，或暂时保持 USE_MOCK=true。",
            }
        raise


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
