"""后端 API 客户端 — Mock 模式下直接返回本地假数据。"""

from __future__ import annotations

import os

import requests

from utils.data_loader import enrich_plan
from utils.mock_data import get_mock_chat_response, get_mock_plan

USE_MOCK = os.getenv("USE_MOCK", "true").lower() == "true"
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def _post(path: str, payload: dict) -> dict:
    resp = requests.post(f"{BACKEND_URL}{path}", json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def _get(path: str, params: dict | None = None) -> dict:
    resp = requests.get(f"{BACKEND_URL}{path}", params=params, timeout=30)
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


def check_health() -> dict:
    if USE_MOCK:
        return {"status": "ok", "mode": "mock"}
    return _get("/api/health")
