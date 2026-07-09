"""Nearby POI search tool with AMap support and local fallback."""

from __future__ import annotations

import os
from typing import Any

import requests

from .common import haversine_km, load_json, tool_decorator


LOCAL_TYPE_MAP = {
    "restaurant": ("restaurants.json", "restaurants"),
    "food": ("restaurants.json", "restaurants"),
    "hotel": ("hotels.json", "hotels"),
    "attraction": ("attractions.json", "attractions"),
    "scenic": ("attractions.json", "attractions"),
}

AMAP_TYPE_CODES = {
    "restaurant": "050000",
    "food": "050000",
    "hotel": "100000",
    "toilet": "200300",
    "attraction": "110000",
    "scenic": "110000",
}


def _infer_city(lat: float, lng: float) -> str | None:
    cities = load_json("cities.json").get("cities", [])
    if not cities:
        return None
    nearest = min(cities, key=lambda item: haversine_km(lat, lng, item["lat"], item["lng"]))
    return nearest["name"]


def _local_items_for_type(poi_type: str) -> list[dict[str, Any]]:
    filename, key = LOCAL_TYPE_MAP.get(poi_type, LOCAL_TYPE_MAP["restaurant"])
    return list(load_json(filename).get(key, []))


def _normalize_local_item(item: dict[str, Any], poi_type: str, distance_km: float) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "type": item.get("type") or item.get("category") or poi_type,
        "category": poi_type,
        "address": item.get("address", ""),
        "lat": item.get("lat"),
        "lng": item.get("lng"),
        "distance_m": round(distance_km * 1000),
        "rating": item.get("rating"),
        "avg_cost": item.get("avg_cost_per_person") or item.get("price_per_night") or item.get("ticket_price"),
        "tags": item.get("tags", []),
        "source": "local_data",
    }


def _search_local_poi(
    lat: float,
    lng: float,
    radius_m: int,
    poi_type: str,
    limit: int,
    city: str | None,
) -> list[dict[str, Any]]:
    inferred_city = city or _infer_city(lat, lng)
    candidates = _local_items_for_type(poi_type)
    result: list[dict[str, Any]] = []
    for item in candidates:
        if inferred_city and item.get("city") != inferred_city:
            continue
        item_lat = item.get("lat")
        item_lng = item.get("lng")
        if item_lat is None or item_lng is None:
            continue
        distance = haversine_km(lat, lng, float(item_lat), float(item_lng))
        if distance * 1000 <= radius_m:
            result.append(_normalize_local_item(item, poi_type, distance))

    result.sort(key=lambda item: (item["distance_m"], -(item.get("rating") or 0)))
    return result[:limit]


def _search_amap_poi(
    lat: float,
    lng: float,
    radius_m: int,
    poi_type: str,
    limit: int,
    keywords: str | None,
    api_key: str,
) -> list[dict[str, Any]]:
    response = requests.get(
        "https://restapi.amap.com/v5/place/around",
        params={
            "key": api_key,
            "location": f"{lng},{lat}",
            "radius": radius_m,
            "types": AMAP_TYPE_CODES.get(poi_type, ""),
            "keywords": keywords or "",
            "page_size": limit,
            "show_fields": "business,photos",
        },
        timeout=8,
    )
    response.raise_for_status()
    payload = response.json()
    pois = payload.get("pois") or []
    result: list[dict[str, Any]] = []
    for poi in pois[:limit]:
        location = str(poi.get("location", "")).split(",")
        poi_lng = float(location[0]) if len(location) == 2 and location[0] else None
        poi_lat = float(location[1]) if len(location) == 2 and location[1] else None
        result.append(
            {
                "id": poi.get("id"),
                "name": poi.get("name"),
                "type": poi.get("type"),
                "category": poi_type,
                "address": poi.get("address", ""),
                "lat": poi_lat,
                "lng": poi_lng,
                "distance_m": int(poi.get("distance") or 0),
                "rating": (poi.get("business") or {}).get("rating"),
                "avg_cost": (poi.get("business") or {}).get("cost"),
                "tags": [],
                "source": "amap",
            }
        )
    return result


def search_nearby_poi_data(
    lat: float,
    lng: float,
    radius_m: int = 1000,
    poi_type: str = "restaurant",
    limit: int = 8,
    city: str | None = None,
    keywords: str | None = None,
) -> dict[str, Any]:
    """Search nearby POIs around a coordinate, falling back to bundled data."""

    radius_m = max(100, min(int(radius_m), 5000))
    limit = max(1, min(int(limit), 30))
    poi_type = (poi_type or "restaurant").lower()
    api_key = (
        os.getenv("AMAP_WEB_SERVICE_KEY", "").strip()
        or os.getenv("AMAP_API_KEY", "").strip()
        or os.getenv("AMAP_JS_API_KEY", "").strip()
    )

    errors: list[str] = []
    items: list[dict[str, Any]] = []
    if api_key:
        try:
            items = _search_amap_poi(lat, lng, radius_m, poi_type, limit, keywords, api_key)
        except Exception as exc:
            errors.append(f"高德 POI 查询失败，已切换本地数据：{exc}")

    if not items:
        items = _search_local_poi(lat, lng, radius_m, poi_type, limit, city)

    return {
        "center": {"lat": lat, "lng": lng},
        "radius_m": radius_m,
        "poi_type": poi_type,
        "count": len(items),
        "items": items,
        "errors": errors,
    }


@tool_decorator
def search_nearby_poi(
    lat: float,
    lng: float,
    radius_m: int = 1000,
    poi_type: str = "restaurant",
    limit: int = 8,
    city: str | None = None,
    keywords: str | None = None,
) -> dict[str, Any]:
    """查询景点周边 POI(餐厅/酒店/景点/厕所)。

    Args:
        lat: 中心点纬度(**必填**,十进制度数,例如 30.5438)。
        lng: 中心点经度(**必填**,十进制度数,例如 114.3055)。
        radius_m: 搜索半径(米),默认 1000,范围 100-5000。
        poi_type: 类型,可选值 restaurant / food / hotel / attraction / scenic / toilet,默认 restaurant。
        limit: 返回数量上限,默认 8,范围 1-30。
        city: 城市中文名(可选,辅助推断)。
        keywords: 关键词(可选,如"夜宵""火锅")。

    Returns:
        包含 items / count / center 的字典;无 lat/lng 时会失败,务必传入景点坐标。
    """

    return search_nearby_poi_data(lat, lng, radius_m, poi_type, limit, city, keywords)

