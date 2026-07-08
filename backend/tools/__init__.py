"""工具层入口 - 只导出成员 A 负责的 self_reflect 工具。

按项目方案 §8.3 / §9.1:
- 7 个 FC 工具(search_attractions / get_weather / calculate_budget /
  optimize_route / search_nearby_poi / generate_checklist /
  generate_travel_diary)由**成员 B**负责实现,本轮尚未提交。
- self_reflect 反思工具由**成员 A**实现(§9.1 注释明确)。

B 同学接入真实实现后,在本 __init__.py 补充 7 个工具的导入 + ALL_TOOLS 列表,
Agent 侧无需改动。
"""
from __future__ import annotations

from langchain_core.tools import BaseTool

from backend.tools.self_reflect import self_reflect

# 当前仅 1 个工具(成员 A 负责)。B 接入后扩展为 8 个。
ALL_TOOLS: list[BaseTool] = [self_reflect]


__all__ = ["ALL_TOOLS", "self_reflect"]
