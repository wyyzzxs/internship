"""Pydantic Schema 测试 - 序列化往返 + 字段约束 + 嵌套结构。"""
from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from backend.schemas.plan import (
    AgentRequest,
    BudgetBreakdown,
    BudgetResult,
    Plan,
    PlanResponse,
)


def _sample_plan_dict() -> dict:
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


def test_plan_round_trip():
    """Plan → dict → Plan 完整往返。"""
    plan = Plan.model_validate(_sample_plan_dict())
    dumped = plan.model_dump(mode="json")
    # JSON 可序列化
    s = json.dumps(dumped, ensure_ascii=False)
    again = Plan.model_validate(json.loads(s))
    assert again.trip_summary.city == "武汉"
    assert again.days[0].items[0].name == "黄鹤楼"
    assert again.budget_breakdown.交通 == 200
    assert again.tips == ["周一黄鹤楼闭馆"]


def test_plan_response_default_success():
    plan = Plan.model_validate(_sample_plan_dict())
    resp = PlanResponse(plan=plan)
    assert resp.success is True
    assert resp.tools_called == []
    assert resp.fallback is False
    assert resp.error is None


def test_plan_response_fallback_flag():
    plan = Plan.model_validate(_sample_plan_dict())
    resp = PlanResponse(plan=plan, tools_called=["fallback"], fallback=True)
    assert resp.fallback is True


def test_agent_request_validation_ok():
    req = AgentRequest(
        city="武汉",
        days=3,
        start_date="2025-07-08",
        budget=1500,
        preferences=["历史"],
        people="情侣",
    )
    assert req.city == "武汉"
    assert req.people == "情侣"
    assert req.departure == "武汉"  # 默认值


def test_agent_request_days_out_of_range():
    with pytest.raises(ValidationError):
        AgentRequest(city="武汉", days=10, start_date="2025-07-08", budget=1500)


def test_agent_request_budget_must_be_positive():
    with pytest.raises(ValidationError):
        AgentRequest(city="武汉", days=3, start_date="2025-07-08", budget=0)


def test_budget_breakdown_chinese_keys():
    """budget_breakdown 的中文键必须可正常赋值。"""
    bb = BudgetBreakdown(交通=100, 住宿=200, 门票=50, 餐饮=80, 其他=20)
    assert bb.交通 == 100
    assert bb.住宿 == 200
    assert bb.门票 == 50
    # dump 后是 dict,中文键保留
    assert bb.model_dump()["交通"] == 100


def test_budget_result_over_budget_flag():
    bb = BudgetBreakdown(交通=100, 住宿=500, 门票=50, 餐饮=80, 其他=20)
    res = BudgetResult(
        breakdown=bb,
        total=750,
        total_budget=500,
        is_over_budget=True,
        over_amount=250,
        suggestion="超支",
    )
    assert res.is_over_budget is True
    assert res.over_amount == 250
    assert res.suggestion == "超支"


def test_plan_extra_fields_ignored():
    """extra='ignore' 保证 LLM 多吐字段不会让校验失败。"""
    data = _sample_plan_dict()
    data["unknown_field"] = "should be ignored"
    data["days"][0]["unknown_nested"] = ["x", "y"]
    plan = Plan.model_validate(data)
    assert plan.trip_summary.city == "武汉"