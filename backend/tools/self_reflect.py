"""self_reflect 工具 - **真实版**(规则检测 + 可选 LLM 增强)。

**A 职责范围**(项目方案 §9.1 注释:self_reflect 反思工具由 A 实现)。

签名严格对齐方案 §3.3 Tool 7:`(plan: dict, request: dict) -> str(JSON)`
返回值:`{"is_satisfied": bool, "issues": [...], "suggestion": "..."}`

真实版实现逻辑:
- **预算超支**: sum(budget_breakdown.values()) > request.budget * 1.05 → 触发
- **景点不足**: len(days) < request.days → 触发
- **单日过密**: any day.items 数量 > 5 → 触发
- **天气未联动**: 无 suggestion 字段或全是"晴" → 提示
- 全部通过 → is_satisfied=True

真实 LLM 增强(Config.MOCK_LLM=false 时):
- 把 plan+request 喂给 LLM,让它给出更细致的评估
- 输出结构跟规则版完全一致
"""
from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.tools import tool

from backend.agents.prompts import REFLECT_PROMPT

logger = logging.getLogger("backend.tools.self_reflect")


def _self_reflect_impl(plan: dict, request: dict) -> dict:
    """规则版反思,纯函数可单独测。返回结构化 dict。"""
    issues: list[str] = []
    suggestion: str | None = None

    # 1) 预算超支检查(允许 5% 溢出)
    breakdown = plan.get("budget_breakdown") or {}
    total_cost = sum(float(v or 0) for v in breakdown.values())
    budget = float(request.get("budget") or 0)
    if budget > 0 and total_cost > budget * 1.05:
        over_amount = round(total_cost - budget, 2)
        issues.append(f"预算超支 {over_amount} 元(超出 {over_amount/budget*100:.1f}%)")
        # suggestion 同时含"超支"和"重算"两个关键字,方便修复规则匹配
        suggestion = "预算超支,重新计算 budget_breakdown,调用 calculate_budget 重算"

    # 2) 景点/天数不足
    days_list = plan.get("days") or []
    request_days = int(request.get("days") or 0)
    if request_days and len(days_list) < request_days:
        issues.append(f"行程天数不足:实际 {len(days_list)} 天,需求 {request_days} 天")
        if not suggestion:
            suggestion = "行程天数不足,补全景点,重新调用 search_attractions"

    # 3) 单日活动过密(>5 个 item)
    for d in days_list:
        items = d.get("items") or []
        if len(items) > 5:
            day_num = d.get("day", "?")
            issues.append(f"Day {day_num} 活动数 {len(items)} 过多(>5),建议精简")
            if not suggestion:
                suggestion = "精简当天活动,把同区域景点合并"
            break

    # 4) 天气未联动(plan.weather 全是"晴"且 request_days >= 3 → 提示)
    weather_list = plan.get("weather") or []
    if weather_list and request_days >= 3:
        all_sunny = all((w.get("weather") or "").strip() in ("晴",) for w in weather_list)
        # 只有当 request_days=3 而 weather 全是晴,可能被怀疑是 fallback 数据
        if all_sunny and len(weather_list) >= 3:
            issues.append("天气数据可能为兜底值,未真实查询")

    is_satisfied = len(issues) == 0
    if is_satisfied:
        suggestion = "行程合理,无需调整"

    return {
        "is_satisfied": is_satisfied,
        "issues": issues,
        "suggestion": suggestion or "OK",
    }


def _llm_enhanced_reflect(plan: dict, request: dict) -> dict:
    """真实 LLM 增强(本轮保留接口,PlanAgent 主流程默认走规则版)。

    MOCK_LLM=false 时,PlanAgent 会用此函数代替规则版。
    """
    try:
        # 避免循环 import:延迟到函数内
        from backend.llm.llm_client import LLMClient

        client = LLMClient()
        prompt = REFLECT_PROMPT.format(
            request=json.dumps(request, ensure_ascii=False),
            plan=json.dumps(plan, ensure_ascii=False)[:4000],  # 防爆
        )
        resp = client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        content = resp.get("content") or ""
        # 提取 JSON
        from backend.agents.plan_agent import _extract_json

        data = _extract_json(content) or {}
        return {
            "is_satisfied": bool(data.get("is_satisfied", True)),
            "issues": list(data.get("issues") or []),
            "suggestion": str(data.get("suggestion") or ""),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM 反思失败,降级到规则版: %s", exc)
        return _self_reflect_impl(plan, request)


@tool
def self_reflect(plan: dict, request: dict) -> str:
    """Agent 自我反思:检查行程是否满足用户需求(规则版,Config.MOCK_LLM=false 时可切 LLM 增强)。

    Args:
        plan: 当前生成的行程 dict
        request: 用户原始需求 dict

    Returns:
        JSON 字符串,is_satisfied/issues/suggestion。
    """
    from backend.config import Config  # 避免循环 import

    if Config.MOCK_LLM:
        result: dict[str, Any] = _self_reflect_impl(plan, request)
    else:
        result = _llm_enhanced_reflect(plan, request)
    return json.dumps(result, ensure_ascii=False)


__all__ = ["self_reflect", "_self_reflect_impl", "_llm_enhanced_reflect"]
