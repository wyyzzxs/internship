"""中英双语 — P2-1 简化版。"""

from __future__ import annotations

TEXTS = {
    "zh": {
        "title": "AI 智能旅游规划师",
        "subtitle": "输入目的地 · 天数 · 预算，Agent 自动生成可交互攻略",
        "tab_itinerary": "行程",
        "tab_map": "地图",
        "tab_chat": "对话",
        "tab_budget": "预算",
        "tab_export": "导出",
        "tab_compare": "对比",
        "generate": "生成行程",
        "demo_mode": "演示预设",
        "travel_needs": "旅行需求",
        "empty_hint": "在左侧填写需求并点击「生成行程」，或加载演示预设。",
        "mock_mode": "Mock 模式",
        "api_mode": "API 模式",
        "section_attractions": "精选景点",
        "section_tips": "旅行贴士",
        "heatmap": "显示路线热力图",
    },
    "en": {
        "title": "AI Travel Planner",
        "subtitle": "Destination · days · budget → interactive itinerary",
        "tab_itinerary": "Itinerary",
        "tab_map": "Map",
        "tab_chat": "Chat",
        "tab_budget": "Budget",
        "tab_export": "Export",
        "tab_compare": "Compare",
        "generate": "Generate Plan",
        "demo_mode": "Demo Presets",
        "travel_needs": "Trip Request",
        "empty_hint": "Fill the sidebar and click Generate, or load a demo preset.",
        "mock_mode": "Mock Mode",
        "api_mode": "API Mode",
        "section_attractions": "Attractions",
        "section_tips": "Travel Tips",
        "heatmap": "Show route heatmap",
    },
}


def t(key: str, lang: str = "zh") -> str:
    return TEXTS.get(lang, TEXTS["zh"]).get(key, key)
