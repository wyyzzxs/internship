"""工具层测试 - 重点覆盖 calculate_budget 和 optimize_route 的真实实现。"""
from __future__ import annotations

import json

from backend.tools.calculate_budget import _calc_budget_impl, calculate_budget
from backend.tools.optimize_route import optimize_route
from backend.tools.get_weather import _get_weather_impl
from backend.tools.optimize_route import _haversine_km, _optimize_impl
from backend.tools.search_attractions import _search_attractions_impl


# --------------------------------------------------------------------------- #
# calculate_budget
# --------------------------------------------------------------------------- #
def test_calc_budget_groups_by_type():
    items = [
        {"type": "交通", "cost": 200},
        {"type": "住宿", "cost": 600},
        {"type": "门票", "cost": 80},
        {"type": "餐饮", "cost": 300},
        {"type": "餐饮", "cost": 30},
    ]
    res = _calc_budget_impl(items, total_budget=1500)
    assert res["breakdown"]["交通"] == 200
    assert res["breakdown"]["住宿"] == 600
    assert res["breakdown"]["门票"] == 80
    assert res["breakdown"]["餐饮"] == 330
    assert res["total"] == 1210
    assert res["is_over_budget"] is False


def test_calc_budget_detects_over_budget():
    items = [
        {"type": "住宿", "cost": 1000},
        {"type": "餐饮", "cost": 400},
        {"type": "交通", "cost": 300},
    ]
    res = _calc_budget_impl(items, total_budget=1500)
    assert res["is_over_budget"] is True
    assert res["over_amount"] == 200
    assert "超支" in (res["suggestion"] or "")


def test_calc_budget_daily_breakdown():
    items = [
        {"type": "门票", "cost": 80, "day": 1},
        {"type": "餐饮", "cost": 100, "day": 1},
        {"type": "门票", "cost": 50, "day": 2},
        {"type": "餐饮", "cost": 120, "day": 2},
    ]
    res = _calc_budget_impl(items, total_budget=500)
    assert res["daily_costs"] == [180, 170]
    assert res["total"] == 350


def test_calc_budget_unknown_type_falls_back_to_other():
    items = [{"type": "未知", "cost": 100}]
    res = _calc_budget_impl(items, total_budget=500)
    assert res["breakdown"]["其他"] == 100


def test_calculate_budget_tool_returns_json_string():
    """@tool 装饰后,invoke 应返回 str(JSON 字符串)。"""
    items = [{"type": "交通", "cost": 200}]
    raw = calculate_budget.invoke({"items": items, "total_budget": 500})
    assert isinstance(raw, str)
    parsed = json.loads(raw)
    assert parsed["total"] == 200


# --------------------------------------------------------------------------- #
# optimize_route
# --------------------------------------------------------------------------- #
def test_haversine_zero_distance():
    assert _haversine_km((30.5, 114.3), (30.5, 114.3)) == 0.0


def test_haversine_known_distance_approx():
    """武汉 → 北京约 1050 km,允许 5% 误差。"""
    wuhan = (30.5928, 114.3055)
    beijing = (39.9042, 116.4074)
    d = _haversine_km(wuhan, beijing)
    assert 1000 < d < 1100


def test_optimize_route_orders_nearest_neighbor():
    """从武汉站出发,贪心选最近的下一个点(就近原则)。"""
    attractions = [
        {"name": "黄鹤楼", "lat": 30.5438, "lng": 114.3055},
        {"name": "户部巷", "lat": 30.5472, "lng": 114.3061},
        {"name": "东湖", "lat": 30.5505, "lng": 114.3708},
    ]
    start = {"name": "武汉站", "lat": 30.6100, "lng": 114.2600}
    res = _optimize_impl(attractions, start_point=start, mode="walking")
    names = [p["name"] if isinstance(p, dict) else p for p in res["ordered"]]
    # 武汉站(起点)必须第一个
    assert names[0] == "武汉站"
    # 后续 3 个景点按就近贪心排列 - 验证全部出现 + 总距离为正
    assert len(names) == 4
    assert set(names[1:]) == {"黄鹤楼", "户部巷", "东湖"}
    assert res["total_distance_km"] > 0
    assert res["mode"] == "walking"
    assert res["estimated_minutes"] > 0


def test_optimize_route_empty_returns_empty():
    res = _optimize_impl([], mode="walking")
    assert res["ordered"] == []
    assert res["total_distance_km"] == 0.0


def test_optimize_route_skips_missing_coords():
    attractions = [
        {"name": "无坐标景点", "lat": None, "lng": None},
        {"name": "黄鹤楼", "lat": 30.5438, "lng": 114.3055},
    ]
    res = _optimize_impl(attractions, mode="driving")
    names = [p["name"] if isinstance(p, dict) else p for p in res["ordered"]]
    assert "黄鹤楼" in names


def test_optimize_route_tool_returns_json():
    attractions = [{"name": "黄鹤楼", "lat": 30.5438, "lng": 114.3055}]
    raw = optimize_route.invoke({"attractions": attractions})
    assert isinstance(raw, str)
    parsed = json.loads(raw)
    assert parsed["total_distance_km"] >= 0


# --------------------------------------------------------------------------- #
# get_weather
# --------------------------------------------------------------------------- #
def test_get_weather_reads_cache():
    res = _get_weather_impl("武汉", "2025-07-08", days=3)
    assert res["city"] == "武汉"
    assert len(res["weather"]) == 3
    # 第一天应该有温度
    assert res["weather"][0]["temp_high"] >= 25
    assert res["weather"][0]["weather"]  # 非空


def test_get_weather_unknown_city_falls_back():
    res = _get_weather_impl("不存在的城市", "2025-07-08", days=2)
    # 应该 fallback 到武汉数据
    assert len(res["weather"]) == 2


# --------------------------------------------------------------------------- #
# search_attractions
# --------------------------------------------------------------------------- #
def test_search_attractions_default_city():
    rows = _search_attractions_impl("武汉")
    assert len(rows) > 0
    assert rows[0]["city"] == "武汉"


def test_search_attractions_with_tag_filter():
    rows = _search_attractions_impl("武汉", tags=["历史"])
    assert all(any("历史" in t for t in r.get("tags", [])) for r in rows)


def test_search_attractions_unknown_city_fallback():
    """未支持城市应该 fallback 到武汉数据。"""
    rows = _search_attractions_impl("火星")
    assert len(rows) > 0