"""search_attractions 工具 - mock 实现(B 后续替换为 RAG 真实实现)。

返回硬编码的武汉景点列表,字段和真实 RAG 返回的 Attraction 结构兼容,
这样 Agent 拿到字段后不会困惑。
"""
from __future__ import annotations

import json

from langchain_core.tools import tool


_MOCK_ATTRACTIONS = [
    {
        "id": "wuhan_huanghelou",
        "name": "黄鹤楼",
        "city": "武汉",
        "category": "历史",
        "tags": ["历史", "文化", "地标", "夜景"],
        "description": "江南三大名楼之首,始建于三国,登楼俯瞰长江和武汉三镇。",
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
        "description": "中国第二大城中湖,绿道全长 101 公里。",
        "best_duration_hours": 4,
        "ticket_price": 0,
        "lat": 30.5505,
        "lng": 114.3708,
        "emoji": "🌸",
        "rating": 4.6,
    },
    {
        "id": "wuhan_hubuxiang",
        "name": "户部巷",
        "city": "武汉",
        "category": "美食",
        "tags": ["美食", "小吃", "夜市"],
        "description": "汉味小吃第一巷,热干面豆皮汤包鸭脖云集。",
        "best_duration_hours": 2,
        "ticket_price": 0,
        "lat": 30.5472,
        "lng": 114.3061,
        "emoji": "🍜",
        "rating": 4.5,
    },
    {
        "id": "wuhan_hubeibowuguan",
        "name": "湖北省博物馆",
        "city": "武汉",
        "category": "历史",
        "tags": ["历史", "文化", "亲子"],
        "description": "曾侯乙编钟所在地,免费参观。",
        "best_duration_hours": 2,
        "ticket_price": 0,
        "lat": 30.5647,
        "lng": 114.3396,
        "emoji": "🏛️",
        "rating": 4.8,
    },
    {
        "id": "wuhan_jianghanlu",
        "name": "江汉路步行街",
        "city": "武汉",
        "category": "美食",
        "tags": ["美食", "购物", "夜景"],
        "description": "百年商业街,武汉夜生活地标。",
        "best_duration_hours": 2,
        "ticket_price": 0,
        "lat": 30.5905,
        "lng": 114.2720,
        "emoji": "🛍️",
        "rating": 4.4,
    },
    {
        "id": "wuhan_jieqingjie",
        "name": "吉庆街",
        "city": "武汉",
        "category": "美食",
        "tags": ["美食", "夜市", "文化"],
        "description": "武汉老字号美食街。",
        "best_duration_hours": 1.5,
        "ticket_price": 0,
        "lat": 30.5880,
        "lng": 114.2705,
        "emoji": "🥘",
        "rating": 4.3,
    },
    {
        "id": "wuhan_changjiangdaqiao",
        "name": "武汉长江大桥",
        "city": "武汉",
        "category": "历史",
        "tags": ["历史", "地标", "夜景"],
        "description": "万里长江第一桥。",
        "best_duration_hours": 1.5,
        "ticket_price": 0,
        "lat": 30.5538,
        "lng": 114.3125,
        "emoji": "🌉",
        "rating": 4.6,
    },
    {
        "id": "wuhan_wuhandaxue",
        "name": "武汉大学",
        "city": "武汉",
        "category": "自然",
        "tags": ["自然", "文化", "亲子"],
        "description": "樱花城堡,雨天可改室内博物馆。",
        "best_duration_hours": 2,
        "ticket_price": 0,
        "lat": 30.5418,
        "lng": 114.3650,
        "emoji": "🎓",
        "rating": 4.7,
    },
]


def _search_attractions_impl(city: str, tags: list[str] | None = None, top_k: int = 8) -> list[dict]:
    rows = [a for a in _MOCK_ATTRACTIONS if a.get("city") == city]
    if not rows:
        # mock 兜底:任何未支持城市都返回武汉数据(避免空结果)
        rows = _MOCK_ATTRACTIONS
    if tags:
        rows = [a for a in rows if any(t in a.get("tags", []) for t in tags)] or rows
    return rows[:top_k]


@tool
def search_attractions(city: str, tags: list[str] | None = None, top_k: int = 8) -> str:
    """根据城市和偏好标签检索景点(B 后续替换为 RAG 真实实现)。

    Args:
        city: 城市名,如"武汉"
        tags: 偏好标签列表,如["历史","美食"]
        top_k: 返回数量

    Returns:
        JSON 字符串,景点列表。
    """
    rows = _search_attractions_impl(city, tags, top_k)
    return json.dumps({"attractions": rows, "source": "mock"}, ensure_ascii=False)


__all__ = ["search_attractions", "_search_attractions_impl"]