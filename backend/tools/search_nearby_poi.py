"""search_nearby_poi 工具 - 临时 mock 实现。

⚠️ **临时越界 mock** - 方案 §8.3 / §9.2 P1-2 此工具由**成员 B**负责接入高德 POI 搜索 API。
   本文件由成员 A 在第二轮临时编写,仅供测试。
   B 接入真实实现后,本文件应被删除。

签名严格对齐方案 §3.3 Tool 5:`(lat, lng, poi_type="餐厅", radius=1000) -> str(JSON)`
返回值字段:`name/address/distance/tel`。
"""
from __future__ import annotations

import json

from langchain_core.tools import tool


_MOCK_POI: list[dict] = [
    {"name": "户部巷老通城豆皮", "type": "餐厅", "distance": 220,
     "address": "武昌区解放路司门口户部巷", "tel": "027-88888888"},
    {"name": "蔡林记热干面(江汉路店)", "type": "餐厅", "distance": 450,
     "address": "江汉区中山大道818号", "tel": "027-82777777"},
    {"name": "如家酒店江汉路店", "type": "酒店", "distance": 800,
     "address": "江汉区江汉路118号", "tel": "027-82222222"},
    {"name": "中国工商银行 ATM(黄鹤楼东门)", "type": "ATM", "distance": 120,
     "address": "黄鹤楼东门广场", "tel": ""},
    {"name": "中百超市(武昌店)", "type": "购物", "distance": 600,
     "address": "武昌区中山路256号", "tel": "027-88899999"},
    {"name": "武汉大学校医院", "type": "其他", "distance": 350,
     "address": "武昌区珞珈山武汉大学内", "tel": "027-68766666"},
]


@tool
def search_nearby_poi(lat: float, lng: float, poi_type: str = "餐厅", radius: int = 1000) -> str:
    """查询景点周边 POI(mock,B 接高德 API 后替换)。

    Args:
        lat: 中心纬度
        lng: 中心经度
        poi_type: POI 类型(餐厅/酒店/厕所/ATM/购物)
        radius: 半径(米)

    Returns:
        JSON 字符串,POI 列表。
    """
    rows = [p for p in _MOCK_POI if p["type"] == poi_type]
    if not rows:
        rows = _MOCK_POI[:3]  # 兜底:返前 3 个
    return json.dumps({"pois": rows, "source": "mock"}, ensure_ascii=False)


__all__ = ["search_nearby_poi"]
