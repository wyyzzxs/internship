"""Function-calling tools used by the travel planner agent.

Merge policy after integrating member B's branch:
- Keep member A's agent-facing ALL_TOOLS registry and core planning tools.
- Use member B's concrete weather, POI, and checklist implementations.
- Keep member A's temporary mock modules in the tree for compatibility until later cleanup.
"""
from __future__ import annotations

from langchain_core.tools import BaseTool

from backend.tools.calculate_budget import calculate_budget
from backend.tools.checklist import generate_checklist, generate_checklist_text
from backend.tools.generate_travel_diary import generate_travel_diary
from backend.tools.optimize_route import optimize_route
from backend.tools.poi import search_nearby_poi, search_nearby_poi_data
from backend.tools.search_attractions import search_attractions
from backend.tools.self_reflect import self_reflect
from backend.tools.weather import get_weather, get_weather_forecast

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
    "generate_checklist_text",
    "generate_travel_diary",
    "get_weather",
    "get_weather_forecast",
    "optimize_route",
    "search_attractions",
    "search_nearby_poi",
    "search_nearby_poi_data",
    "self_reflect",
]
