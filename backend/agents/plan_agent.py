"""PlanAgent 主类 - 端到端 Agent 闭环(项目方案 §3.2 / §3.4 / §6.4)。

主入口:plan(request: dict) -> dict
执行流程:
1. AgentRequest 校验(days 1-7、budget>0 等)
2. while loop (≤10 次):调 LLM → 解析 tool_calls → 执行 → 喂回 → 提取 JSON
3. Pydantic 校验 Plan,失败 fallback
4. LLMUnavailable / RuntimeError / ValidationError → 全部走 _fallback_plan

兜底链(本轮不依赖外部 JSON):
- 优先尝试 data/mock_plans/{city}.json(由成员 F 提供,本轮未提交)
- 都没有 → _minimal_plan 内存兜底(保证任何 request 都能返回非空结构)
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

from pydantic import ValidationError

from backend.agents.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from backend.config import Config
from backend.llm.llm_client import LLMClient, LLMUnavailable
from backend.schemas.plan import (
    AgentRequest,
    Plan,
    PlanDay,
    PlanDayItem,
    PlanResponse,
    TripSummary,
    WeatherDay,
)
from backend.tools import ALL_TOOLS

logger = logging.getLogger("backend.agents.plan_agent")

# 兜底匹配:从 LLM content 中提取 JSON
_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)
_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)

# 中文城市名 → 拼音 slug(用于 mock_plans 路径)
_CITY_SLUG = {
    "武汉": "wuhan",
    "西安": "xian",
    "成都": "chengdu",
    "北京": "beijing",
    "杭州": "hangzhou",
    "厦门": "xiamen",
}


# --------------------------------------------------------------------------- #
# 辅助函数
# --------------------------------------------------------------------------- #
def _add_days(start_date: str, delta: int) -> str:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return (datetime.strptime(start_date, fmt) + timedelta(days=delta)).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return start_date


def _slug(city: str) -> str:
    return _CITY_SLUG.get(city, city.lower().replace(" ", "_"))


def _extract_json(content: str) -> Optional[dict]:
    """从 LLM content 中尽力捞 JSON 对象。"""
    if not content:
        return None
    fence = _FENCE_RE.search(content)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass
    match = _JSON_BLOCK_RE.search(content)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


# --------------------------------------------------------------------------- #
# 主类
# --------------------------------------------------------------------------- #
class PlanAgent:
    """单 Agent + 工具调度的核心。"""

    def __init__(
        self,
        llm: LLMClient | None = None,
        tools: list[Callable] | None = None,
        session_store: Any | None = None,
    ) -> None:
        self.llm = llm or LLMClient()
        self.tools = tools if tools is not None else list(ALL_TOOLS)
        self.tool_map: dict[str, Callable] = {
            getattr(t, "name", getattr(t, "__name__", str(t))): t for t in self.tools
        }
        self.max_iterations = Config.AGENT_MAX_ITERATIONS
        self.session_store = session_store  # 预留,本轮未实现
        self._last_tools_called: list[str] = []

    # ------------------------------------------------------------------ #
    # 主入口
    # ------------------------------------------------------------------ #
    def plan(self, request: dict) -> dict:
        """生成完整行程。返回 dict(严格符合 PlanResponse schema)。

        Args:
            request: 必须含 city/days/start_date/budget;可选 preferences/people/departure
        """
        # 1. 内部校验:days 1-7、budget>0
        try:
            AgentRequest.model_validate(request)
        except ValidationError as exc:
            logger.warning("AgentRequest 校验失败(%s),触发 fallback", exc)
            fallback = self._fallback_plan(request)
            fallback["error"] = f"validation: {exc.errors()[0]['msg']}"
            fallback["success"] = False
            return fallback

        # 2. 主循环
        try:
            plan_dict = self._call_llm_with_tools_loop(request)
            if not plan_dict or "trip_summary" not in plan_dict:
                raise RuntimeError("LLM 未返回含 trip_summary 的合法 JSON")
            plan = Plan.model_validate(plan_dict)
            return PlanResponse(
                success=True,
                plan=plan,
                tools_called=list(self._last_tools_called),
            ).model_dump(mode="json")
        except (LLMUnavailable, RuntimeError, ValueError) as exc:
            logger.warning("主流程失败(%s),触发 fallback", exc)
            fallback = self._fallback_plan(request)
            fallback["error"] = str(exc)
            fallback["success"] = False
            return fallback

    # ------------------------------------------------------------------ #
    # 主循环
    # ------------------------------------------------------------------ #
    def _call_llm_with_tools_loop(self, request: dict) -> Optional[dict]:
        self._last_tools_called = []

        messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(
                    city=request.get("city", "武汉"),
                    days=request.get("days", 3),
                    start_date=request.get("start_date", "2025-07-08"),
                    budget=request.get("budget", 1500),
                    preferences=request.get("preferences") or ["历史文化"],
                    people=request.get("people", "情侣"),
                    departure=request.get("departure", "武汉"),
                ),
            },
        ]

        for i in range(self.max_iterations):
            logger.info("Agent loop iter %d/%d", i + 1, self.max_iterations)
            resp = self.llm.chat(messages, tools=self.tools, temperature=0.3)

            assistant: dict[str, Any] = {
                "role": "assistant",
                "content": resp.get("content"),
            }
            if resp.get("tool_calls"):
                assistant["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"], ensure_ascii=False),
                        },
                    }
                    for tc in resp["tool_calls"]
                ]
            messages.append(assistant)

            # 有 tool_calls → 执行后喂回
            if resp.get("tool_calls"):
                for tc in resp["tool_calls"]:
                    name = tc["name"]
                    args = tc["arguments"] or {}
                    self._last_tools_called.append(name)
                    tool_obj = self.tool_map.get(name)
                    if not tool_obj:
                        logger.warning("未找到工具 %s", name)
                        tool_result = json.dumps(
                            {"error": f"tool {name} not found"}, ensure_ascii=False
                        )
                    else:
                        try:
                            tool_result = tool_obj.invoke(args)
                        except Exception as exc:  # noqa: BLE001
                            logger.warning("工具 %s 执行失败: %s", name, exc)
                            tool_result = json.dumps(
                                {"error": str(exc), "tool": name}, ensure_ascii=False
                            )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "name": name,
                            "content": tool_result,
                        }
                    )
                continue

            # 无 tool_calls → 尝试提取 JSON
            extracted = _extract_json(resp.get("content") or "")
            if extracted and "trip_summary" in extracted:
                return extracted

            if i == self.max_iterations - 1:
                logger.warning("达到最大迭代仍未提取出合法 JSON")
                return extracted
            messages.append(
                {
                    "role": "user",
                    "content": "请把上面所有工具结果整理成严格的 JSON 行程输出,不要任何额外说明。",
                }
            )

        return None

    # ------------------------------------------------------------------ #
    # Fallback
    # ------------------------------------------------------------------ #
    def _fallback_plan(self, request: dict) -> dict:
        """优先尝试 data/mock_plans/{city}.json(由成员 F 维护,本轮未提交);
        文件不存在或加载失败时,直接返回 _minimal_plan 内存兜底。
        """
        city = (request.get("city") or "武汉").strip()
        # 候选路径:成员 F 接管后会提供,本轮未必存在
        candidates = [
            Config.MOCK_PLANS_DIR / f"{_slug(city)}_3day_1500.json",
            Config.MOCK_PLANS_DIR / f"{city}.json",
        ]
        for path in candidates:
            if path.exists():
                try:
                    with path.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    logger.info("使用 fallback 行程: %s", path)
                    plan = Plan.model_validate(data)
                    return PlanResponse(
                        success=True,
                        plan=plan,
                        tools_called=["fallback"],
                        fallback=True,
                    ).model_dump(mode="json")
                except (OSError, json.JSONDecodeError, ValueError) as exc:
                    logger.warning("fallback 文件 %s 加载失败: %s", path, exc)

        # 终极兜底:内存最小 Plan(任何 request 都能返回非空结构)
        minimal = self._minimal_plan(request)
        return PlanResponse(
            success=True,
            plan=minimal,
            tools_called=["fallback_minimal"],
            fallback=True,
        ).model_dump(mode="json")

    def _minimal_plan(self, request: dict) -> Plan:
        """在内存里塞一份最小 Plan,保证任何 request 都能返回非空结构。"""
        city = str(request.get("city") or "武汉")
        try:
            days = int(request.get("days") or 1)
        except (TypeError, ValueError):
            days = 1
        try:
            budget = float(request.get("budget") or 1000)
        except (TypeError, ValueError):
            budget = 1000.0
        start_date = str(request.get("start_date") or "2025-07-08")
        people = str(request.get("people") or "情侣")

        summary = TripSummary(
            city=city,
            days=days,
            start_date=start_date,
            end_date=_add_days(start_date, max(0, days - 1)),
            total_budget=budget,
            people=people,  # type: ignore[arg-type]
        )
        days_list = []
        for d in range(1, max(days, 1) + 1):
            days_list.append(
                PlanDay(
                    day=d,
                    date=_add_days(start_date, d - 1),
                    items=[
                        PlanDayItem(
                            time="09:00",
                            type="景点",
                            name=f"{city}景点(占位)",
                            duration_hours=2,
                            cost=0,
                            description="fallback 数据,完整版待 AI 生成",
                            emoji="📍",
                        )
                    ],
                    day_cost=0,
                )
            )
        return Plan(
            trip_summary=summary,
            weather=[
                WeatherDay(
                    date=start_date,
                    weather="晴",
                    temp_high=30,
                    temp_low=22,
                    suggestion="适合户外",
                )
            ],
            days=days_list,
            tips=["当前为兜底数据,实际行程由 AI 生成"],
        )

    # ------------------------------------------------------------------ #
    # 反射(预留)
    # ------------------------------------------------------------------ #
    def reflect(self, plan: dict, request: dict) -> dict:
        """本轮不接入真实反射循环,直接调用 self_reflect 工具并返回其结果。

        真实循环触发见第二轮任务清单(项目方案 §3.3 Tool 7)。
        """
        reflect_tool = self.tool_map.get("self_reflect")
        if not reflect_tool:
            return {"is_satisfied": True, "issues": [], "suggestion": "no reflect tool"}
        try:
            raw = reflect_tool.invoke({"plan": plan, "request": request})
            return json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            logger.warning("self_reflect 执行失败: %s", exc)
            return {"is_satisfied": True, "issues": [], "suggestion": "reflect skipped"}


# --------------------------------------------------------------------------- #
# CLI 入口
# --------------------------------------------------------------------------- #
def _cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="命令行跑 PlanAgent.plan()")
    parser.add_argument("--city", default="武汉", help="目的地")
    parser.add_argument("--days", type=int, default=3, help="天数")
    parser.add_argument("--start-date", default="2025-07-08", help="出发日期 YYYY-MM-DD")
    parser.add_argument("--budget", type=float, default=1500, help="总预算(元)")
    parser.add_argument("--preferences", nargs="*", default=["历史文化", "美食"], help="偏好标签")
    parser.add_argument("--people", default="情侣", help="同行人群")
    parser.add_argument("--departure", default="武汉", help="出发地")
    args = parser.parse_args(argv)

    req = {
        "city": args.city,
        "days": args.days,
        "start_date": args.start_date,
        "budget": args.budget,
        "preferences": args.preferences,
        "people": args.people,
        "departure": args.departure,
    }
    agent = PlanAgent()
    result = agent.plan(req)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))


__all__ = ["PlanAgent"]