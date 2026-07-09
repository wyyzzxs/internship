"""第三轮集成测试 - 端到端跑 plan + modify + reflect。

3 个用例对应方案 §13.6 的 3 个演示用例(武汉 / 西安 / 成都)。

依赖:
- PlanAgent(本仓库) + LLMClient mock
- MemorySessionStore(A 临时版)
- 8 个工具(本轮临时 mock,B 接管后替换)
"""
from __future__ import annotations

import json

import pytest

from backend.agents.plan_agent import PlanAgent
from backend.llm.llm_client import LLMClient
from backend.tools import ALL_TOOLS


# --------------------------------------------------------------------------- #
# 工具:build_mock_agent(用一个固定 plan 当 LLM 输出)
# --------------------------------------------------------------------------- #
def _build_mock_agent(sample_plan: dict, monkeypatch=None) -> PlanAgent:
    """构造一个 PlanAgent,LLM 永远返 sample_plan(模拟 LLM 已生成行程)。

    推荐用 monkeypatch 传进来,测试结束自动还原(避免污染 test_llm_client 等其他测试)。
    """
    agent = PlanAgent(llm=LLMClient(), tools=list(ALL_TOOLS))

    def fake_chat(self, messages, tools=None, temperature=0.3, max_retries=None):
        return {
            "role": "assistant",
            "content": json.dumps(sample_plan, ensure_ascii=False),
            "tool_calls": None,
            "raw": None,
        }

    if monkeypatch is not None:
        monkeypatch.setattr("backend.llm.llm_client.LLMClient.chat", fake_chat)
    else:
        # 不传 monkeypatch 时警告(只用于单测,不要在集合测试里用)
        import warnings
        warnings.warn(
            "_build_mock_agent without monkeypatch may leak LLMClient.chat patch",
            stacklevel=2,
        )
        import backend.llm.llm_client
        backend.llm.llm_client.LLMClient.chat = fake_chat
    return agent


# --------------------------------------------------------------------------- #
# 工具:assert_plan_quality
# --------------------------------------------------------------------------- #
def _assert_plan_quality(plan: dict, *, expected_days: int, expected_budget: int) -> None:
    """校验 plan 字段齐全 + 数量合理。

    Args:
        plan: plan 字段(PlanResponse.plan.model_dump)
        expected_days: 期望天数
        expected_budget: 期望预算(用于校验 budget_breakdown 总和)
    """
    # 1. 顶层字段
    for field in ("trip_summary", "weather", "days", "budget_breakdown", "tips"):
        assert field in plan, f"plan 缺字段: {field}"

    # 2. days 数对
    assert len(plan["days"]) == expected_days, (
        f"days={len(plan['days'])} != expected {expected_days}"
    )

    # 3. budget_breakdown 总和 在 budget 50% ~ 110% 之间
    bd_total = sum(float(v or 0) for v in plan["budget_breakdown"].values())
    lo, hi = expected_budget * 0.5, expected_budget * 1.1
    assert lo <= bd_total <= hi, (
        f"budget_breakdown 总和 {bd_total} 超出范围 [{lo}, {hi}]"
    )

    # 4. 每天 3-5 个 item(允许 ±1,给 reflect-loop 修复留余地)
    for d in plan["days"]:
        items = d.get("items") or []
        assert 2 <= len(items) <= 6, f"Day {d.get('day')} items={len(items)} 超出 2-6"

    # 5. trip_summary 字段齐全
    summary = plan["trip_summary"]
    for k in ("city", "days", "start_date", "end_date", "total_budget", "people"):
        assert k in summary, f"trip_summary 缺字段: {k}"


# --------------------------------------------------------------------------- #
# 3 个 demo 用例(方案 §13.6)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "city,days,budget,prefs,people,sample",
    [
        # 用例 1:武汉 2 天 800 独自穷游(学生党)
        (
            "武汉", 2, 800, ["历史", "美食"], "独自",
            {
                "trip_summary": {
                    "city": "武汉", "days": 2, "start_date": "2025-07-08",
                    "end_date": "2025-07-09", "total_budget": 800, "people": "独自",
                },
                "weather": [
                    {"date": "2025-07-08", "weather": "晴", "temp_high": 33,
                     "temp_low": 26, "suggestion": "适合户外"},
                    {"date": "2025-07-09", "weather": "多云", "temp_high": 34,
                     "temp_low": 27, "suggestion": "适合户外"},
                ],
                "days": [
                    {
                        "day": 1, "date": "2025-07-08",
                        "items": [
                            {"time": "09:00", "type": "景点", "name": "武汉大学",
                             "duration_hours": 2, "cost": 0, "lat": 30.5418, "lng": 114.3650,
                             "description": "樱花城堡,免费", "emoji": "🎓"},
                            {"time": "12:00", "type": "餐饮", "name": "户部巷午餐",
                             "duration_hours": 1, "cost": 30, "lat": 30.5472, "lng": 114.3061,
                             "description": "汉味小吃", "emoji": "🍜"},
                            {"time": "14:00", "type": "景点", "name": "东湖绿道",
                             "duration_hours": 3, "cost": 0, "lat": 30.5505, "lng": 114.3708,
                             "description": "免费骑行", "emoji": "🌸"},
                            {"time": "19:00", "type": "餐饮", "name": "青旅晚餐",
                             "duration_hours": 1, "cost": 25, "lat": 30.5850, "lng": 114.2720,
                             "description": "经济型晚餐", "emoji": "🥘"},
                        ],
                        "day_cost": 55,
                    },
                    {
                        "day": 2, "date": "2025-07-09",
                        "items": [
                            {"time": "09:00", "type": "景点", "name": "湖北省博物馆",
                             "duration_hours": 2, "cost": 0, "lat": 30.5647, "lng": 114.3396,
                             "description": "曾侯乙编钟,免费", "emoji": "🏛️"},
                            {"time": "12:00", "type": "餐饮", "name": "粮道街午餐",
                             "duration_hours": 1, "cost": 30, "lat": 30.5500, "lng": 114.3300,
                             "description": "学生党最爱", "emoji": "🍜"},
                            {"time": "14:00", "type": "景点", "name": "江汉路步行街",
                             "duration_hours": 2, "cost": 0, "lat": 30.5905, "lng": 114.2720,
                             "description": "免费逛街", "emoji": "🛍️"},
                        ],
                        "day_cost": 30,
                    },
                ],
                "budget_breakdown": {"交通": 100, "住宿": 200, "门票": 0, "餐饮": 110, "其他": 30},
                "tips": ["学生党 800 元够玩 2 天", "已避开收费景点主推免费文化地标"],
            },
        ),
        # 用例 2:西安 3 天 3500 亲子
        (
            "西安", 3, 3500, ["历史", "亲子"], "亲子",
            {
                "trip_summary": {
                    "city": "西安", "days": 3, "start_date": "2025-07-08",
                    "end_date": "2025-07-10", "total_budget": 3500, "people": "亲子",
                },
                "weather": [
                    {"date": "2025-07-08", "weather": "晴", "temp_high": 35,
                     "temp_low": 24, "suggestion": "高温注意防晒"},
                ],
                "days": [
                    {
                        "day": 1, "date": "2025-07-08",
                        "items": [
                            {"time": "09:00", "type": "景点", "name": "秦始皇兵马俑",
                             "duration_hours": 3, "cost": 120, "lat": 34.3853, "lng": 109.2733,
                             "description": "世界八大奇迹之一", "emoji": "🏛️"},
                            {"time": "13:00", "type": "餐饮", "name": "农家菜",
                             "duration_hours": 1.5, "cost": 80, "lat": 34.3800, "lng": 109.2700,
                             "description": "亲子", "emoji": "🍜"},
                            {"time": "15:00", "type": "景点", "name": "秦始皇陵",
                             "duration_hours": 1.5, "cost": 0, "lat": 34.3845, "lng": 109.2650,
                             "description": "免费外围", "emoji": "⛰️"},
                        ],
                        "day_cost": 200,
                    },
                    {
                        "day": 2, "date": "2025-07-09",
                        "items": [
                            {"time": "09:30", "type": "景点", "name": "陕西历史博物馆",
                             "duration_hours": 2.5, "cost": 0, "lat": 34.2216, "lng": 108.9537,
                             "description": "免费需预约", "emoji": "🏛️"},
                            {"time": "13:00", "type": "餐饮", "name": "永兴坊",
                             "duration_hours": 1.5, "cost": 90, "lat": 34.2300, "lng": 108.9480,
                             "description": "陕西小吃", "emoji": "🍲"},
                            {"time": "15:30", "type": "景点", "name": "大雁塔",
                             "duration_hours": 1.5, "cost": 50, "lat": 34.2196, "lng": 108.9637,
                             "description": "登塔看西安", "emoji": "🗼"},
                        ],
                        "day_cost": 140,
                    },
                    {
                        "day": 3, "date": "2025-07-10",
                        "items": [
                            {"time": "09:00", "type": "景点", "name": "华清宫",
                             "duration_hours": 3, "cost": 120, "lat": 34.3580, "lng": 109.2090,
                             "description": "长恨歌实景", "emoji": "🏯"},
                            {"time": "13:00", "type": "餐饮", "name": "华清御膳",
                             "duration_hours": 1.5, "cost": 120, "lat": 34.3585, "lng": 109.2085,
                             "description": "宫廷菜", "emoji": "🥢"},
                            {"time": "15:00", "type": "景点", "name": "骊山",
                             "duration_hours": 1.5, "cost": 75, "lat": 34.3600, "lng": 109.2150,
                             "description": "缆车上山", "emoji": "⛰️"},
                        ],
                        "day_cost": 315,
                    },
                ],
                "budget_breakdown": {"交通": 800, "住宿": 1500, "门票": 365, "餐饮": 390, "其他": 445},
                "tips": ["兵马俑建议请讲解员", "已避开周一博物馆闭馆"],
            },
        ),
        # 用例 3:成都 2 天 2000 朋友美食
        (
            "成都", 2, 2000, ["美食"], "朋友",
            {
                "trip_summary": {
                    "city": "成都", "days": 2, "start_date": "2025-07-08",
                    "end_date": "2025-07-09", "total_budget": 2000, "people": "朋友",
                },
                "weather": [
                    {"date": "2025-07-08", "weather": "多云", "temp_high": 31,
                     "temp_low": 23, "suggestion": "适合户外"},
                    {"date": "2025-07-09", "weather": "小雨", "temp_high": 28,
                     "temp_low": 22, "suggestion": "建议安排室内活动"},
                ],
                "days": [
                    {
                        "day": 1, "date": "2025-07-08",
                        "items": [
                            {"time": "10:00", "type": "景点", "name": "宽窄巷子",
                             "duration_hours": 2, "cost": 0, "lat": 30.6740, "lng": 104.0612,
                             "description": "清代古街", "emoji": "🏮"},
                            {"time": "12:30", "type": "餐饮", "name": "小龙坎火锅",
                             "duration_hours": 1.5, "cost": 120, "lat": 30.6745, "lng": 104.0620,
                             "description": "老火锅", "emoji": "🌶️"},
                            {"time": "14:30", "type": "景点", "name": "锦里",
                             "duration_hours": 2, "cost": 0, "lat": 30.6427, "lng": 104.0462,
                             "description": "三国主题", "emoji": "🏯"},
                            {"time": "19:30", "type": "餐饮", "name": "玉林串串香",
                             "duration_hours": 1.5, "cost": 80, "lat": 30.6280, "lng": 104.0750,
                             "description": "本地人最爱", "emoji": "🍢"},
                        ],
                        "day_cost": 200,
                    },
                    {
                        "day": 2, "date": "2025-07-09",
                        "items": [
                            {"time": "10:00", "type": "景点", "name": "大熊猫基地",
                             "duration_hours": 3, "cost": 55, "lat": 30.7331, "lng": 104.1430,
                             "description": "看大熊猫", "emoji": "🐼"},
                            {"time": "13:30", "type": "餐饮", "name": "龙抄手",
                             "duration_hours": 1, "cost": 50, "lat": 30.6580, "lng": 104.0810,
                             "description": "成都小吃", "emoji": "🥟"},
                            {"time": "15:00", "type": "景点", "name": "春熙路",
                             "duration_hours": 1.5, "cost": 0, "lat": 30.6590, "lng": 104.0815,
                             "description": "商业街", "emoji": "🛍️"},
                        ],
                        "day_cost": 105,
                    },
                ],
                "budget_breakdown": {"交通": 350, "住宿": 600, "门票": 105, "餐饮": 490, "其他": 155},
                "tips": ["Day2 有小雨,改室内商场", "成都美食多,行程留白"],
            },
        ),
    ],
)
def test_demo_case(city, days, budget, prefs, people, sample, monkeypatch):
    """3 个 demo 用例端到端:plan → modify → reflect-log,验证 Plan 质量。"""
    agent = _build_mock_agent(sample, monkeypatch=monkeypatch)
    req = {
        "city": city, "days": days, "start_date": "2025-07-08",
        "budget": budget, "preferences": prefs, "people": people,
        "departure": "武汉",
    }

    # 1. plan
    plan_resp = agent.plan(req)
    assert plan_resp["success"] is True, f"plan 失败: {plan_resp.get('error')}"
    plan = plan_resp["plan"]
    _assert_plan_quality(plan, expected_days=days, expected_budget=budget)

    # 2. modify(换景点)
    mod = agent.modify(
        f"ses_{city}",
        "把第 1 天下午改成东方明珠",
        plan,
    )
    assert mod["updated_plan"]["days"][0]["items"][-1]["name"] == "东方明珠"

    # 3. reflect(模拟:让 reflect 工具返 issues,看主流程 catch)
    # 简化:直接验证 reflect() 方法不抛
    refl = agent.reflect(plan, req)
    assert "is_satisfied" in refl


# --------------------------------------------------------------------------- #
# 补充:工具异常友好返(第三轮新增强化)
# --------------------------------------------------------------------------- #
def test_tool_exception_returns_friendly_dict(monkeypatch):
    """工具抛异常时,主循环 catch 并把 error 写进 messages,不让整个 plan 崩。

    策略:monkeypatch 替换 get_weather 工具在 ALL_TOOLS 列表里的引用
    (StructuredTool 本身是 pydantic v1 BaseModel,不能直接 setattr invoke,
    但 ALL_TOOLS 列表里能替换成 boom 函数)
    """
    import backend.agents.plan_agent as plan_agent_module
    from backend.tools import ALL_TOOLS

    sample = {
        "trip_summary": {"city": "武汉", "days": 1, "start_date": "2025-07-08",
                          "end_date": "2025-07-08", "total_budget": 1000, "people": "情侣"},
        "weather": [{"date": "2025-07-08", "weather": "晴", "temp_high": 30, "temp_low": 22}],
        "days": [
            {"day": 1, "date": "2025-07-08",
             "items": [{"time": "09:00", "type": "景点", "name": "黄鹤楼",
                        "duration_hours": 2, "cost": 80}], "day_cost": 80},
        ],
        "budget_breakdown": {"交通": 100, "住宿": 400, "门票": 80, "餐饮": 200, "其他": 50},
        "tips": [],
    }
    _build_mock_agent(sample, monkeypatch=monkeypatch)  # 触发 LLMClient.chat monkeypatch

    # 把 ALL_TOOLS 里的 get_weather 替换成抛异常的 fake
    # 整个 ALL_TOOLS 替换,内部把 get_weather 换成 boom
    original_tools = list(ALL_TOOLS)

    class BoomWeather:
        """模拟 get_weather 抛异常"""
        name = "get_weather"
        description = "boom"

        @staticmethod
        def invoke(*args, **kwargs):
            raise RuntimeError("模拟和风 API 挂了")

    new_tools = []
    for t in original_tools:
        if getattr(t, "name", "") == "get_weather":
            new_tools.append(BoomWeather())
        else:
            new_tools.append(t)
    monkeypatch.setattr(plan_agent_module, "ALL_TOOLS", new_tools)

    # 重新建一个 PlanAgent(让它从 ALL_TOOLS 拿工具)
    agent2 = PlanAgent(llm=LLMClient(), tools=new_tools)

    plan_resp = agent2.plan({
        "city": "武汉", "days": 1, "start_date": "2025-07-08",
        "budget": 1000, "preferences": ["历史"], "people": "情侣",
    })
    # 主流程应成功(工具异常被 catch,继续走)
    assert plan_resp["success"] is True
    assert "黄鹤楼" in plan_resp["plan"]["days"][0]["items"][0]["name"]


# --------------------------------------------------------------------------- #
# 补充:LLM 不可用时友好中文 message
# --------------------------------------------------------------------------- #
def test_llm_unavailable_returns_chinese_friendly_error(monkeypatch):
    """LLM 抛 LLMUnavailable,plan() 应返 success=False + 中文 error。"""
    from backend.llm.llm_client import LLMUnavailable

    agent = PlanAgent()

    def boom(self, messages, tools=None, temperature=0.3, max_retries=None):
        raise LLMUnavailable("模拟 DashScope 限流")

    monkeypatch.setattr("backend.llm.llm_client.LLMClient.chat", boom)

    plan_resp = agent.plan({
        "city": "武汉", "days": 3, "start_date": "2025-07-08",
        "budget": 1500, "preferences": ["历史"], "people": "情侣",
    })
    assert plan_resp["success"] is False
    assert "AI 服务" in (plan_resp.get("error") or "")
    assert "兜底" in (plan_resp.get("error") or "")
    # fallback plan 仍可用
    assert plan_resp.get("fallback") is True
    assert "trip_summary" in plan_resp["plan"]
