"""calculate_budget 工具 - 真实版(纯函数,本轮保留)。

**A 范围内**:第一轮就写完的真实版,本轮未修改。

签名严格对齐方案 §3.3 Tool 3:`(items, total_budget) -> str(JSON)`
返回值:`breakdown/total/total_budget/is_over_budget/over_amount/suggestion/daily_costs`
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict

from langchain_core.tools import tool

logger = logging.getLogger("backend.tools.calculate_budget")

_VALID_TYPES = {"交通", "住宿", "门票", "餐饮", "其他"}


def _calc_budget_impl(items: list[dict], total_budget: float) -> dict:
    """纯函数实现,可单独测试。

    Args:
        items: 行程项目列表,每个含 type/cost/day(可选)
        total_budget: 用户总预算(元)

    Returns:
        标准化字典,含 breakdown/total/is_over_budget/suggestion/daily_costs
    """
    breakdown: dict[str, float] = defaultdict(float)
    daily: defaultdict[int, float] = defaultdict(float)

    for item in items:
        t = item.get("type")
        cost = float(item.get("cost", 0) or 0)
        if t not in _VALID_TYPES:
            logger.warning("未知 type=%s, 计入'其他'", t)
            t = "其他"
        breakdown[t] += cost
        day = item.get("day")
        if day is not None:
            daily[int(day)] += cost

    total = round(sum(breakdown.values()), 2)
    total_budget = round(float(total_budget), 2)
    is_over = total > total_budget
    over_amount = round(max(total - total_budget, 0.0), 2)

    suggestion: str | None = None
    if is_over:
        over_pct = over_amount / total_budget * 100 if total_budget else 0
        suggestion = (
            f"超支 {over_amount:.0f} 元 ({over_pct:.1f}%)。"
            "建议优先缩减住宿(改经济型)或减少 1 顿正餐;门票可考虑免费替代景点。"
        )
    elif total_budget > 0 and total < total_budget * 0.6:
        suggestion = "预算宽松,可考虑升级 1 晚酒店或增加特色体验。"

    return {
        "breakdown": {k: round(v, 2) for k, v in breakdown.items()},
        "total": total,
        "total_budget": total_budget,
        "is_over_budget": is_over,
        "over_amount": over_amount,
        "suggestion": suggestion,
        "daily_costs": [round(daily.get(d, 0.0), 2) for d in sorted(daily)],
    }


@tool
def calculate_budget(items: list[dict], total_budget: float) -> str:
    """根据行程项目和总预算计算各项费用,检查是否超支。

    Args:
        items: 行程项目列表,每个含 type/cost/day(可选)
                type ∈ {"交通","住宿","门票","餐饮","其他"}
        total_budget: 用户总预算(元)

    Returns:
        JSON 字符串,含 breakdown/total/is_over_budget/suggestion/daily_costs。
    """
    result = _calc_budget_impl(items, total_budget)
    return json.dumps(result, ensure_ascii=False)


__all__ = ["calculate_budget", "_calc_budget_impl"]
