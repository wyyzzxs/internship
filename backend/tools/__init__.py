"""工具层入口 - 8 个 @tool 集中导出。

**重要说明**(本轮临时状态):
按项目方案 §8.3 / §9.1 / §9.2 严格归属,本目录文件由多人协作:
- **成员 A**(本轮已写):
  - self_reflect.py(§9.1 注释明确"由 A 实现")
  - generate_travel_diary.py(§9.2 标注"工具函数由 B 写,Agent 集成由 A",
    本轮 B 未提交,A 先写真实 LLM 版占位供测试)

- **成员 B**(本轮未提交,由 A 临时 mock 占位,**B 接入后须删除**):
  - search_attractions.py → 真实 RAG(ChromaDB)
  - get_weather.py → 真实和风天气 API
  - search_nearby_poi.py → 真实高德 POI API
  - generate_checklist.py → 真实 LLM

- **第一轮 A 真实版**(本轮保留):
  - calculate_budget.py(纯函数)
  - optimize_route.py(贪心 TSP)

⚠️ 临时 mock 文件顶部都加有"⚠️ 临时越界 mock"警告注释,
   B 接入后从 import 列表移除并删除源文件即可。

测试:本轮 A 写了 4 个新测试文件覆盖 self_reflect / generate_travel_diary /
modify / MemorySessionStore,加上原有的 26 个测试,共约 40+ 用例。
"""
from __future__ import annotations

from langchain_core.tools import BaseTool

# A 范围内(本轮真实版)
from backend.tools.self_reflect import self_reflect
from backend.tools.generate_travel_diary import generate_travel_diary

# A 范围内(第一轮真实版,本轮保留)
from backend.tools.calculate_budget import calculate_budget
from backend.tools.optimize_route import optimize_route

# B 范围内(本轮临时 mock,B 接入后须删)
from backend.tools.search_attractions import search_attractions
from backend.tools.get_weather import get_weather
from backend.tools.search_nearby_poi import search_nearby_poi
from backend.tools.generate_checklist import generate_checklist

ALL_TOOLS: list[BaseTool] = [
    search_attractions,
    get_weather,
    calculate_budget,
    optimize_route,
    search_nearby_poi,
    generate_checklist,
    generate_travel_diary,
    self_reflect,
]


__all__ = [
    "ALL_TOOLS",
    "self_reflect",
    "generate_travel_diary",
    "calculate_budget",
    "optimize_route",
    "search_attractions",
    "get_weather",
    "search_nearby_poi",
    "generate_checklist",
]
