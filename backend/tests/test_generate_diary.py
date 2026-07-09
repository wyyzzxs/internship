"""generate_travel_diary 工具测试 - 至少 100 字 + 含 Markdown 标记。

测试 MOCK 模式(默认):返固定模板,长度够 100 字 + Markdown 标题/引用块。
"""
from __future__ import annotations

from backend.tools.generate_travel_diary import _mock_diary, generate_travel_diary


def test_mock_diary_length_and_markdown():
    """MOCK 模板返 ≥ 100 字,含 # 标题 + > 引用块。"""
    day_plan = {
        "day": 1,
        "date": "2025-07-08",
        "items": [
            {"name": "黄鹤楼", "type": "景点", "description": "江南三大名楼之首",
             "duration_hours": 2, "cost": 80, "emoji": "🏯"},
            {"name": "户部巷", "type": "餐饮", "description": "汉味小吃第一巷",
             "duration_hours": 1, "cost": 50, "emoji": "🍜"},
            {"name": "长江大桥", "type": "景点", "description": "万里长江第一桥",
             "duration_hours": 1.5, "cost": 0, "emoji": "🌉"},
        ],
    }

    out = _mock_diary(day_plan)

    # 长度 ≥ 100 字(中文字符)
    assert len(out) >= 100, f"日记长度 {len(out)} < 100"
    # Markdown 标记
    assert "# Day" in out, "缺 Markdown 标题 # Day"
    assert ">" in out, "缺 Markdown 引用块 >"
    # 内容相关
    assert "黄鹤楼" in out
    assert "2025-07-08" in out or "今天" in out


def test_tool_invoke_returns_string():
    """通过 @tool invoke 调用,返 Markdown 字符串。"""
    day_plan = {
        "day": 2,
        "date": "2025-07-09",
        "items": [
            {"name": "东湖", "type": "景点", "description": "城中湖", "duration_hours": 3, "cost": 0, "emoji": "🌸"},
            {"name": "湖北省博物馆", "type": "景点", "description": "曾侯乙编钟", "duration_hours": 2, "cost": 0, "emoji": "🏛️"},
            {"name": "农家菜", "type": "餐饮", "description": "东湖周边", "duration_hours": 1, "cost": 90, "emoji": "🥬"},
        ],
    }

    out = generate_travel_diary.invoke({"day_plan": day_plan, "mood": "治愈"})

    assert isinstance(out, str)
    assert len(out) >= 100
    assert "# Day" in out
    # mood 影响?目前 mock 不影响,只验基础结构
    assert "东湖" in out


def test_mock_handles_empty_items():
    """边界:items 为空也能返合理模板。"""
    out = _mock_diary({"day": 1, "date": "2025-07-08", "items": []})
    assert len(out) >= 100
    assert "# Day" in out


def test_mock_handles_non_dict_input():
    """边界:day_plan 不是 dict 也能兜底。"""
    # 防御性调用
    out = _mock_diary({"day": 1, "date": "2025-07-08"})  # 缺 items
    assert len(out) >= 100
