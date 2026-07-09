"""self_reflect 工具 + PlanAgent.reflect-loop 测试 - 3 个用例。

覆盖:
1. 超支 plan → is_satisfied=False + suggestion 含"calculate_budget"
2. 合理 plan → is_satisfied=True
3. reflect-loop:plan() 主循环遇到超支场景,3 次反射后强制返回
"""
from __future__ import annotations

import json

from backend.agents.plan_agent import PlanAgent
from backend.tools.self_reflect import _self_reflect_impl, self_reflect


# --------------------------------------------------------------------------- #
# 用例 1:budget=100,plan 总花费 2000 → 触发超支
# --------------------------------------------------------------------------- #
def test_reflect_detects_over_budget():
    plan = {
        "trip_summary": {"city": "武汉", "days": 1, "budget": 100},
        "days": [
            {"day": 1, "date": "2025-07-08", "items": [
                {"name": "某景点", "type": "景点", "cost": 1500, "duration_hours": 2},
                {"name": "某住宿", "type": "住宿", "cost": 500, "duration_hours": 8},
            ]},
        ],
        "budget_breakdown": {"交通": 100, "住宿": 500, "门票": 1500, "餐饮": 0, "其他": 0},
        "weather": [],
    }
    request = {"city": "武汉", "days": 1, "budget": 100}

    result = _self_reflect_impl(plan, request)

    assert result["is_satisfied"] is False
    assert any("超支" in issue for issue in result["issues"])
    # suggestion 应该提及重新调用 calculate_budget
    assert "calculate_budget" in (result["suggestion"] or "").lower()


def test_reflect_tool_invoke_returns_json():
    """通过 @tool invoke 调用,验证返 JSON 字符串契约。"""
    plan = {
        "trip_summary": {"city": "武汉", "days": 1},
        "days": [{"day": 1, "items": []}],
        "budget_breakdown": {"交通": 0, "住宿": 0, "门票": 0, "餐饮": 0, "其他": 0},
    }
    request = {"city": "武汉", "days": 1, "budget": 1000}
    raw = self_reflect.invoke({"plan": plan, "request": request})
    data = json.loads(raw)
    assert "is_satisfied" in data
    assert "issues" in data
    assert "suggestion" in data


# --------------------------------------------------------------------------- #
# 用例 2:合理 plan → is_satisfied=True
# --------------------------------------------------------------------------- #
def test_reflect_passes_for_reasonable_plan():
    plan = {
        "trip_summary": {"city": "武汉", "days": 3, "budget": 1500},
        "days": [
            {"day": 1, "items": [{"name": "黄鹤楼", "cost": 80, "duration_hours": 2}] * 3},
            {"day": 2, "items": [{"name": "东湖", "cost": 0, "duration_hours": 3}] * 2},
            {"day": 3, "items": [{"name": "江汉路", "cost": 0, "duration_hours": 2}] * 2},
        ],
        "budget_breakdown": {"交通": 200, "住宿": 600, "门票": 80, "餐饮": 300, "其他": 60},
        "weather": [
            {"date": "2025-07-08", "weather": "晴", "temp_high": 33, "temp_low": 26},
        ],
    }
    request = {"city": "武汉", "days": 3, "budget": 1500}

    result = _self_reflect_impl(plan, request)

    assert result["is_satisfied"] is True
    assert result["issues"] == []
    # 通过时 suggestion 应该是"行程合理"或类似
    assert "合理" in (result["suggestion"] or "") or result["suggestion"] == "OK"


# --------------------------------------------------------------------------- #
# 用例 3:reflect-loop 集成测试(plan() 主循环 + reflect-loop 触发)
# --------------------------------------------------------------------------- #
def test_reflect_loop_triggers_in_plan(monkeypatch):
    """构造一个 LLM 返超支 plan 的场景,验证 plan() 内部 reflect-loop 触发修复。

    策略:monkeypatch LLMClient.chat,让它返一个 budget_breakdown 求和 = 2000
    的 plan(超预算 1500),看 reflect-loop 是否能修复到预算内。
    """
    # 构造超支 plan
    over_budget_plan = {
        "trip_summary": {"city": "武汉", "days": 3, "start_date": "2025-07-08",
                          "end_date": "2025-07-10", "total_budget": 1500, "people": "情侣"},
        "weather": [
            {"date": "2025-07-08", "weather": "晴", "temp_high": 33, "temp_low": 26, "suggestion": "适合户外"},
        ],
        "days": [
            {"day": 1, "date": "2025-07-08", "items": [
                {"time": "09:00", "type": "景点", "name": "黄鹤楼",
                 "duration_hours": 2, "cost": 80, "emoji": "🏯"},
            ], "day_cost": 80},
        ],
        "budget_breakdown": {"交通": 200, "住宿": 600, "门票": 80, "餐饮": 330, "其他": 60},
        # 上面的 breakdown 求和 = 1270,实际不超,这里临时把它改超
        "tips": [],
    }
    # 让 breakdown 超支
    over_budget_plan["budget_breakdown"] = {
        "交通": 200, "住宿": 600, "门票": 800, "餐饮": 300, "其他": 200,  # 求和 = 2100
    }

    def fake_chat(self, messages, tools=None, temperature=0.3, max_retries=None):
        return {
            "role": "assistant",
            "content": json.dumps(over_budget_plan, ensure_ascii=False),
            "tool_calls": None,
            "raw": None,
        }

    monkeypatch.setattr("backend.llm.llm_client.LLMClient.chat", fake_chat)

    agent = PlanAgent()
    result = agent.plan({
        "city": "武汉", "days": 3, "start_date": "2025-07-08",
        "budget": 1500, "preferences": ["历史"], "people": "情侣",
    })

    # 修复后 budget_breakdown 总和应在预算 105% 内
    bd = result["plan"]["budget_breakdown"]
    total = sum(float(v or 0) for v in bd.values())
    assert total <= 1500 * 1.05, f"reflect-loop 未修复超支: total={total}, budget=1500"
    # 计划仍然成功
    assert result["success"] is True
