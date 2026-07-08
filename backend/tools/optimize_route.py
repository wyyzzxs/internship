"""optimize_route 工具 - 真实实现:N≤10 贪心 TSP,Haversine 球面距离。"""
from __future__ import annotations

import json
import logging
import math

from langchain_core.tools import tool

logger = logging.getLogger("backend.tools.optimize_route")

# 模式 -> 估算时速(km/h)
_MODE_PROFILE = {
    "walking": 5.0,
    "driving": 30.0,
    "transit": 20.0,
}


def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """两点 (lat, lng) 球面距离,单位 km。"""
    lat1, lng1 = a
    lat2, lng2 = b
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def _optimize_impl(
    attractions: list[dict],
    start_point: dict | None = None,
    mode: str = "walking",
) -> dict:
    """贪心 TSP:每步选距离当前最近的下一个点。"""
    if not attractions:
        return {"ordered": [], "total_distance_km": 0.0, "mode": mode}

    valid = []
    for idx, a in enumerate(attractions):
        lat, lng = a.get("lat"), a.get("lng")
        if lat is None or lng is None:
            logger.warning("景点 %s 缺坐标,跳过", a.get("name"))
            continue
        valid.append({**a, "_idx": idx, "_coord": (float(lat), float(lng))})

    if not valid:
        return {
            "ordered": [a.get("name") for a in attractions],
            "total_distance_km": 0.0,
            "mode": mode,
            "note": "no valid coordinates",
        }

    if start_point and start_point.get("lat") is not None and start_point.get("lng") is not None:
        start_coord = (float(start_point["lat"]), float(start_point["lng"]))
        start_name = start_point.get("name", "起点")
    else:
        start_coord = valid[0]["_coord"]
        start_name = valid[0].get("name", "起点")

    remaining = valid[:]
    ordered: list[dict] = [{"name": start_name, "_coord": start_coord}]
    current = start_coord
    total_km = 0.0
    while remaining:
        nxt = min(remaining, key=lambda a: _haversine_km(current, a["_coord"]))
        seg = _haversine_km(current, nxt["_coord"])
        total_km += seg
        ordered.append({k: v for k, v in nxt.items() if not k.startswith("_")})
        current = nxt["_coord"]
        remaining.remove(nxt)

    km_per_hour = _MODE_PROFILE.get(mode, _MODE_PROFILE["walking"])
    return {
        "ordered": ordered,
        "total_distance_km": round(total_km, 3),
        "estimated_minutes": round(total_km / km_per_hour * 60, 1),
        "mode": mode,
    }


@tool
def optimize_route(
    attractions: list[dict],
    start_point: dict | None = None,
    mode: str = "walking",
) -> str:
    """根据景点坐标和起点,贪心算法重排顺序(就近原则)。

    Args:
        attractions: 景点列表,每个含 name/lat/lng
        start_point: 起点坐标 {name, lat, lng},默认第一个景点
        mode: walking / driving / transit,影响耗时估算

    Returns:
        JSON 字符串,排序后的景点列表 + 总距离 + 耗时。
    """
    result = _optimize_impl(attractions, start_point, mode)
    return json.dumps(result, ensure_ascii=False)


__all__ = ["optimize_route", "_optimize_impl"]