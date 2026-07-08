"""search_nearby_poi 工具 - mock 实现(B 后续接入高德 API)。"""
from __future__ import annotations

import json

from langchain_core.tools import tool


_MOCK_POI = [
    {"name": "户部巷老通城豆皮", "type": "餐厅", "distance": 220, "address": "武昌区解放路", "tel": ""},
    {"name": "蔡林记热干面", "type": "餐厅", "distance": 450, "address": "江汉区中山大道", "tel": ""},
    {"name": "如家酒店江汉路店", "type": "酒店", "distance": 800, "address": "江汉区江汉路", "tel": ""},
    {"name": "中国工商银行 ATM", "type": "ATM", "distance": 120, "address": "黄鹤楼东门", "tel": ""},
    {"name": "中百超市", "type": "购物", "distance": 600, "address": "武昌区中山路", "tel": ""},
]


@tool
def search_nearby_poi(lat: float, lng: float, poi_type: str = "餐厅", radius: int = 1000) -> str:
    """查询景点周边 POI(B 后续接入高德 API,本轮 mock)。

    Args:
        lat: 中心纬度
        lng: 中心经度
        poi_type: POI 类型,餐厅/酒店/厕所/ATM/购物
        radius: 半径(米)

    Returns:
        JSON 字符串,POI 列表。
    """
    rows = [p for p in _MOCK_POI if p["type"] == poi_type]
    if not rows:
        rows = _MOCK_POI[:3]
    return json.dumps({"pois": rows, "source": "mock"}, ensure_ascii=False)


__all__ = ["search_nearby_poi"]