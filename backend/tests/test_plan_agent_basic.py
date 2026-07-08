"""PlanAgent 集成测试 - 全 mock,3 个用例覆盖主流程 + 兜底。"""
from __future__ import annotations

import json

import pytest

from backend.agents.plan_agent import PlanAgent
from backend.llm.llm_client import LLMUnavailable


def _mock_plan_dict() -> dict:
    return {
        "trip_summary": {
            "city": "武汉",
            "days": 3,
            "start_date": "2025-07-08",
            "end_date": "2025-07-10",
            "total_budget": 1500,
            "people": "情侣",
        },
        "weather": [
            {
                "date": "2025-07-08",
                "weather": "晴",
                "temp_high": 33,
                "temp_low": 26,
                "suggestion": "适合户外",
            }
        ],
        "days": [
            {
                "day": 1,
                "date": "2025-07-08",
                "items": [
                    {
                        "time": "09:00",
                        "type": "景点",
                        "name": "黄鹤楼",
                        "duration_hours": 2,
                        "cost": 80,
                        "lat": 30.5438,
                        "lng": 114.3055,
                        "description": "江南三大名楼之首",
                        "emoji": "🏯",
                    }
                ],
                "day_cost": 80,
            }
        ],
        "budget_breakdown": {"交通": 200, "住宿": 600, "门票": 80, "餐饮": 330, "其他": 60},
        "tips": ["周一黄鹤楼闭馆"],
    }


@pytest.fixture
def mock_llm_ok(monkeypatch):
    """替换 LLMClient.chat:返回合法 JSON。"""

    def fake_chat(self, messages, tools=None, temperature=0.3, max_retries=None):
        return {
            "role": "assistant",
            "content": json.dumps(_mock_plan_dict(), ensure_ascii=False),
            "tool_calls": None,
            "raw": None,
        }

    monkeypatch.setattr("backend.llm.llm_client.LLMClient.chat", fake_chat)


@pytest.fixture
def mock_tools(monkeypatch):
    """8 个工具全部替换为无副作用 mock。"""
    import backend.tools as tools_pkg

    def _noop_factory(name):
        def _fn(**kwargs):
            return json.dumps({"mock": name, "kwargs": kwargs}, ensure_ascii=False)

        _fn.name = name
        _fn.description = f"mock {name}"
        return _fn

    new_tools = [_noop_factory(t.name) for t in tools_pkg.ALL_TOOLS]
    monkeypatch.setattr(tools_pkg, "ALL_TOOLS", new_tools)
    return new_tools


# --------------------------------------------------------------------------- #
# 用例 1:武汉 3 天 1500 历史美食 → 返回 Plan
# --------------------------------------------------------------------------- #
def test_wuhan_3day_1500_returns_plan(mock_llm_ok, mock_tools):
    agent = PlanAgent()
    result = agent.plan(
        {
            "city": "武汉",
            "days": 3,
            "start_date": "2025-07-08",
            "budget": 1500,
            "preferences": ["历史", "美食"],
            "people": "情侣",
            "departure": "武汉",
        }
    )
    assert result["success"] is True
    assert result["plan"]["trip_summary"]["city"] == "武汉"
    assert result["plan"]["trip_summary"]["days"] == 3
    assert result["plan"]["trip_summary"]["total_budget"] == 1500
    assert result["plan"]["trip_summary"]["people"] == "情侣"
    # 第二轮 reflect-loop 会检测"天数不足"并补到 3 天,所以最终 days 数 == 3
    assert len(result["plan"]["days"]) == 3
    # 第一个 day 首项仍是 LLM mock 返回的黄鹤楼
    assert result["plan"]["days"][0]["items"][0]["name"] == "黄鹤楼"


# --------------------------------------------------------------------------- #
# 用例 2:days=10 → AgentRequest 校验失败,fallback
# --------------------------------------------------------------------------- #
def test_day_10_triggers_validation_fallback(mock_llm_ok, mock_tools):
    """days 超过 7,触发 AgentRequest 校验失败,PlanAgent 走 fallback。"""
    agent = PlanAgent()
    result = agent.plan(
        {
            "city": "武汉",
            "days": 10,  # 违反 AgentRequest.days <= 7
            "start_date": "2025-07-08",
            "budget": 1500,
            "preferences": ["历史"],
            "people": "情侣",
        }
    )
    assert result["success"] is False  # 主流程失败
    assert result["fallback"] is True  # 走了 fallback
    assert result["plan"]["trip_summary"]["city"] == "武汉"
    assert "validation" in (result.get("error") or "").lower()


# --------------------------------------------------------------------------- #
# 用例 3:mock LLM 抛 LLMUnavailable → fallback 成功
# --------------------------------------------------------------------------- #
def test_llm_unavailable_triggers_fallback(mock_tools, monkeypatch):
    """LLM 抛 LLMUnavailable 时,PlanAgent 必须兜底返回 Plan。"""

    def boom(self, messages, tools=None, temperature=0.3, max_retries=None):
        raise LLMUnavailable("模拟 LLM 不可用")

    monkeypatch.setattr("backend.llm.llm_client.LLMClient.chat", boom)
    agent = PlanAgent()
    result = agent.plan(
        {
            "city": "武汉",
            "days": 3,
            "start_date": "2025-07-08",
            "budget": 1500,
            "preferences": ["历史"],
            "people": "情侣",
        }
    )
    assert result["fallback"] is True
    assert "plan" in result
    assert result["plan"]["trip_summary"]["city"] == "武汉"
    assert "模拟 LLM 不可用" in (result.get("error") or "")


# --------------------------------------------------------------------------- #
# Bonus:tools_called 记录 + reflect 不报错
# --------------------------------------------------------------------------- #
def test_tools_called_recorded(mock_llm_ok, mock_tools, monkeypatch):
    """主循环里如果 LLM 调过工具,tools_called 应记录。"""
    call_log = {"i": 0}

    def fake_chat(self, messages, tools=None, temperature=0.3, max_retries=None):
        call_log["i"] += 1
        if call_log["i"] == 1:
            # 第一次:返回一个 tool_call
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "name": "search_attractions",
                        "arguments": {"city": "武汉"},
                    }
                ],
                "raw": None,
            }
        # 第二次:返回最终 JSON
        return {
            "role": "assistant",
            "content": json.dumps(_mock_plan_dict(), ensure_ascii=False),
            "tool_calls": None,
            "raw": None,
        }

    monkeypatch.setattr("backend.llm.llm_client.LLMClient.chat", fake_chat)
    agent = PlanAgent()
    result = agent.plan(
        {
            "city": "武汉",
            "days": 3,
            "start_date": "2025-07-08",
            "budget": 1500,
            "people": "情侣",
        }
    )
    assert result["success"] is True
    assert "search_attractions" in result["tools_called"]


def test_reflect_method_does_not_raise(mock_llm_ok, mock_tools):
    agent = PlanAgent()
    out = agent.reflect(plan=_mock_plan_dict(), request={"city": "武汉", "days": 3})
    assert "is_satisfied" in out