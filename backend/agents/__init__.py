"""Agent 层入口(成员 A 负责)。

注意:不在此处 eager import,避免 `python -m backend.agents.plan_agent`
触发 `RuntimeWarning: ... found in sys.modules after import ...`。

推荐用法:`from backend.agents.plan_agent import PlanAgent`
兼容用法:`from backend.agents import PlanAgent`(走 __getattr__ lazy import)
"""
from __future__ import annotations

__all__ = ["PlanAgent"]


def __getattr__(name):  # PEP 562 - 模块级 lazy import
    if name == "PlanAgent":
        from backend.agents.plan_agent import PlanAgent

        return PlanAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")