"""中英双语 — P2-1 简化版。"""

from __future__ import annotations

TEXTS = {
    "zh": {
        "title": "AI 智能旅游规划师",
        "subtitle": "输入目的地 + 天数 + 预算，Agent 自动生成可交互攻略",
        "tab_itinerary": "📅 行程",
        "tab_map": "🗺️ 地图",
        "tab_chat": "💬 对话",
        "tab_budget": "📊 预算",
        "generate": "🚀 生成行程",
        "demo_mode": "🎬 演示模式",
        "travel_needs": "✈️ 旅行需求",
        "empty_hint": "在左侧填写需求，点击「生成行程」，或选择演示模式一键加载。",
        "mock_mode": "🟡 Mock 模式",
        "api_mode": "🟢 真实 API",
    },
    "en": {
        "title": "AI Travel Planner",
        "subtitle": "Destination + days + budget → Agent builds your interactive itinerary",
        "tab_itinerary": "📅 Itinerary",
        "tab_map": "🗺️ Map",
        "tab_chat": "💬 Chat",
        "tab_budget": "📊 Budget",
        "generate": "🚀 Generate Plan",
        "demo_mode": "🎬 Demo Mode",
        "travel_needs": "✈️ Trip Request",
        "empty_hint": "Fill the sidebar, click Generate, or load a demo preset.",
        "mock_mode": "🟡 Mock Mode",
        "api_mode": "🟢 Live API",
    },
}


def t(key: str, lang: str = "zh") -> str:
    return TEXTS.get(lang, TEXTS["zh"]).get(key, key)
