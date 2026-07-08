"""self_reflect 工具 - mock 实现(真实版本轮不实现,PlanAgent.reflect() 仅占位调用)。

接口对齐项目方案 §3.3 Tool 7。
"""
from __future__ import annotations

import json

from langchain_core.tools import tool


@tool
def self_reflect(plan: dict, request: dict) -> str:
    """Agent 自我反思:检查行程是否满足用户需求(本轮 mock)。

    Args:
        plan: 当前生成的行程
        request: 用户原始需求

    Returns:
        JSON 字符串,is_satisfied/issues/suggestion。
    """
    return json.dumps(
        {
            "is_satisfied": True,
            "issues": [],
            "suggestion": "mock reflect - 本轮未启用真实反思",
        },
        ensure_ascii=False,
    )


__all__ = ["self_reflect"]