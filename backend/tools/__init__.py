"""工具层入口 - 8 个 @tool 集中导出。

B 负责真实实现;本轮由 A 写 mock 桩:
  - 真实版:calculate_budget / optimize_route
  - mock  版:search_attractions / get_weather / search_nearby_poi / generate_checklist
              / generate_travel_diary / self_reflect
"""
from __future__ import annotations

from langchain_core.tools import BaseTool

from backend.tools.calculate_budget import calculate_budget
from backend.tools.generate_checklist import generate_checklist
from backend.tools.generate_travel_diary import generate_travel_diary
from backend.tools.get_weather import get_weather
from backend.tools.optimize_route import optimize_route
from backend.tools.search_attractions import search_attractions
from backend.tools.search_nearby_poi import search_nearby_poi
from backend.tools.self_reflect import self_reflect

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
    "calculate_budget",
    "generate_checklist",
    "generate_travel_diary",
    "get_weather",
    "optimize_route",
    "search_attractions",
    "search_nearby_poi",
    "self_reflect",
]