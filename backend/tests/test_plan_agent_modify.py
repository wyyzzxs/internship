"""PlanAgent.modify() 多轮对话修改测试 - 3 个用例覆盖核心场景。

依赖:PlanAgent / MemorySessionStore(成员 A 临时实现)
测试模式:MOCK_LLM=true(规则版,无 LLM 也能跑)
"""
from __future__ import annotations

import pytest

from backend.agents.plan_agent import PlanAgent
from backend.db.memory_store import MemorySessionStore
from backend.llm.llm_client import LLMClient
from backend.tools import ALL_TOOLS


# --------------------------------------------------------------------------- #
# 准备:一个"标准 3 天 1500 武汉"plan,供 modify 改
# --------------------------------------------------------------------------- #
def _sample_plan() -> dict:
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
            {"date": "2025-07-08", "weather": "晴", "temp_high": 33, "temp_low": 26, "suggestion": "适合户外"},
            {"date": "2025-07-09", "weather": "多云", "temp_high": 34, "temp_low": 27, "suggestion": "适合户外"},
            {"date": "2025-07-10", "weather": "阵雨", "temp_high": 30, "temp_low": 25, "suggestion": "建议安排室内活动"},
        ],
        "days": [
            {
                "day": 1, "date": "2025-07-08",
                "items": [
                    {"time": "09:00", "type": "景点", "name": "黄鹤楼",
                     "duration_hours": 2, "cost": 80, "lat": 30.5438, "lng": 114.3055,
                     "description": "江南三大名楼之首", "emoji": "🏯"},
                    {"time": "12:00", "type": "餐饮", "name": "户部巷午餐",
                     "duration_hours": 1, "cost": 50, "lat": 30.5472, "lng": 114.3061,
                     "description": "武汉特色小吃一条街", "emoji": "🍜"},
                    {"time": "14:00", "type": "景点", "name": "武汉长江大桥",
                     "duration_hours": 1.5, "cost": 0, "lat": 30.5538, "lng": 114.3125,
                     "description": "万里长江第一桥", "emoji": "🌉"},
                ],
                "day_cost": 130,
            },
            {
                "day": 2, "date": "2025-07-09",
                "items": [
                    {"time": "09:30", "type": "景点", "name": "东湖风景区",
                     "duration_hours": 4, "cost": 0, "lat": 30.5505, "lng": 114.3708,
                     "description": "中国第二大城中湖", "emoji": "🌸"},
                    {"time": "14:00", "type": "景点", "name": "汉口江滩",
                     "duration_hours": 2, "cost": 0, "lat": 30.6000, "lng": 114.2800,
                     "description": "老汉口风情", "emoji": "🌊"},
                ],
                "day_cost": 0,
            },
            {
                "day": 3, "date": "2025-07-10",
                "items": [
                    {"time": "09:30", "type": "景点", "name": "江汉路步行街",
                     "duration_hours": 2, "cost": 0, "lat": 30.5905, "lng": 114.2720,
                     "description": "百年商业街", "emoji": "🛍️"},
                ],
                "day_cost": 0,
            },
        ],
        "budget_breakdown": {"交通": 200, "住宿": 600, "门票": 80, "餐饮": 330, "其他": 60},
        "tips": ["周一黄鹤楼闭馆,本次行程周二开始不受影响"],
    }


@pytest.fixture
def agent_with_store():
    """建一个带 session_store 的 PlanAgent(MOCK_LLM 模式)。"""
    store = MemorySessionStore()
    agent = PlanAgent(llm=LLMClient(), tools=list(ALL_TOOLS), session_store=store)
    return agent, store


# --------------------------------------------------------------------------- #
# 用例 1:"把第 2 天下午改成湖北省博物馆" → updated_plan.days[1] 含"湖北省博物馆"
# --------------------------------------------------------------------------- #
def test_modify_replace_attraction(agent_with_store):
    agent, store = agent_with_store
    plan = _sample_plan()
    session_id = "ses_replace"

    result = agent.modify(
        session_id=session_id,
        message="把第 2 天下午改成湖北省博物馆",
        current_plan=plan,
    )

    assert "reply" in result
    assert "updated_plan" in result
    assert "diff" in result
    # days[1] 末项应是"湖北省博物馆"
    day2_items = result["updated_plan"]["days"][1]["items"]
    assert any("湖北省博物馆" in it.get("name", "") for it in day2_items)
    # diff 字段
    assert result["diff"]["day"] == 2
    assert result["diff"]["added"] == "湖北省博物馆"
    assert "汉口江滩" in (result["diff"]["removed"] or "")


# --------------------------------------------------------------------------- #
# 用例 2:"预算砍到 1200" → budget_breakdown 求和 = 1200 ± 50
# --------------------------------------------------------------------------- #
def test_modify_reduce_budget(agent_with_store):
    agent, store = agent_with_store
    plan = _sample_plan()
    session_id = "ses_budget"

    result = agent.modify(
        session_id=session_id,
        message="预算砍到 1200 元",
        current_plan=plan,
    )

    bd = result["updated_plan"]["budget_breakdown"]
    total = sum(float(v or 0) for v in bd.values())
    # 允许 50 元误差
    assert abs(total - 1200) <= 50, f"预算应为 ~1200,实际 {total}"
    # reply 提到预算调整
    assert "预算" in result["reply"] or "1200" in result["reply"]


# --------------------------------------------------------------------------- #
# 用例 3:history 累积 11 条后 get_history 只返回 10 条(截断)
# --------------------------------------------------------------------------- #
def test_modify_history_truncated_to_10(agent_with_store):
    agent, store = agent_with_store
    plan = _sample_plan()
    session_id = "ses_truncate"

    # 累积 11 条消息(每轮 modify 写 2 条:user + assistant)
    for i in range(6):
        agent.modify(
            session_id=session_id,
            message=f"第 {i+1} 轮修改",
            current_plan=plan,
        )

    history = store.get_history(session_id, last_n=10)
    # 6 轮 × 2 = 12 条,截断到 10
    assert len(history) == 10
    # 最后一条应是 assistant
    assert history[-1]["role"] == "assistant"
    # 第一条应该是 user(截断后最早一条)
    assert history[0]["role"] == "user"
