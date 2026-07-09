"""Attraction search tool backed by member C's RAG retriever.

The public tool contract stays compatible with PlanAgent:
(city, tags=None, top_k=8) -> JSON string with attractions/source fields.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger("backend.tools.search_attractions")


_FALLBACK_ATTRACTIONS: list[dict[str, Any]] = [
    {
        "id": "wuhan_huanghelou",
        "name": "黄鹤楼",
        "city": "武汉",
        "category": "历史",
        "tags": ["历史", "文化", "地标", "夜景"],
        "description": "江南三大名楼之一，适合登楼俯瞰长江和武汉三镇。",
        "best_duration_hours": 2,
        "ticket_price": 80,
        "lat": 30.5438,
        "lng": 114.3055,
        "emoji": "🏯",
        "rating": 4.7,
    },
    {
        "id": "wuhan_donghu",
        "name": "东湖风景区",
        "city": "武汉",
        "category": "自然",
        "tags": ["自然", "休闲", "骑行"],
        "description": "武汉代表性湖泊风景区，适合骑行、散步和亲子游。",
        "best_duration_hours": 4,
        "ticket_price": 0,
        "lat": 30.5505,
        "lng": 114.3708,
        "emoji": "🌿",
        "rating": 4.6,
    },
    {
        "id": "wuhan_hubei_museum",
        "name": "湖北省博物馆",
        "city": "武汉",
        "category": "历史",
        "tags": ["历史", "文化", "亲子", "室内"],
        "description": "曾侯乙编钟等镇馆之宝所在地，雨天和亲子场景都很适合。",
        "best_duration_hours": 2,
        "ticket_price": 0,
        "lat": 30.5647,
        "lng": 114.3396,
        "emoji": "🏛️",
        "rating": 4.8,
    },
]


def _fallback_search(city: str, tags: list[str] | None, top_k: int) -> list[dict[str, Any]]:
    rows = [row for row in _FALLBACK_ATTRACTIONS if row.get("city") == city] or _FALLBACK_ATTRACTIONS
    if tags:
        matched = [row for row in rows if any(tag in row.get("tags", []) for tag in tags)]
        rows = matched or rows
    return rows[:top_k]


def _search_attractions_impl(city: str, tags: list[str] | None = None, top_k: int = 8) -> list[dict[str, Any]]:
    """Search attractions through RAG/Chroma, falling back to bundled JSON/mock data."""

    top_k = max(1, min(int(top_k), 30))
    try:
        from backend.rag.retriever import TouristRetriever

        results = TouristRetriever().search(city=city, tags=tags or [], top_k=top_k)
        if results:
            return results
    except Exception as exc:  # noqa: BLE001
        logger.warning("RAG attraction search failed, using fallback: %s", exc)

    return _fallback_search(city, tags, top_k)


@tool
def search_attractions(city: str, tags: list[str] | None = None, top_k: int = 8) -> str:
    """根据城市和偏好标签检索景点，优先使用 ChromaDB RAG，失败时使用本地数据兜底。"""

    rows = _search_attractions_impl(city, tags, top_k)
    source = "rag_or_json" if rows else "empty"
    return json.dumps({"attractions": rows, "source": source}, ensure_ascii=False)


__all__ = ["search_attractions", "_search_attractions_impl"]
