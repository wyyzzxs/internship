"""PlanAgent 主类 - 端到端 Agent 闭环(项目方案 §3.2 / §3.4 / §6.4)。

**主入口**(第二轮扩展):
- plan(request)            -> dict   # 生成行程(带 reflect-loop,最多 3 次)
- modify(session_id, msg, plan) -> dict  # 多轮对话修改(第二轮新增,§3.5 / P1-4)
- reflect(plan, request)   -> dict   # 反思(规则版,可切 LLM 增强)
- session_store            -> MemorySessionStore | None  # 第二轮新增(§3.5)

**执行流程**:
1. AgentRequest 校验(days 1-7、budget>0 等)
2. 主循环(≤10 次):调 LLM → 解析 tool_calls → 执行 → 喂回 → 提取 JSON
3. **reflect-loop**(第二轮新增):拿到最终 JSON 后调 self_reflect,
   不通过则按 suggestion 规则修复,最多 3 次强制返回
4. LLMUnavailable / RuntimeError / ValidationError → 走 _fallback_plan

**兜底链**(本轮不依赖外部 JSON):
- 优先尝试 data/mock_plans/{city}.json(由成员 F 提供,本轮未必存在)
- 都没有 → _minimal_plan 内存兜底

**MOCK 模式退化**:
- modify():不走 LLM,按 message 关键字做规则替换(详见 _mock_modify_impl)
- reflect():走 _self_reflect_impl 规则版,不调 LLM
- plan() 主循环:_call_llm_with_tools_loop 走 LLMClient._mock_chat 返固定 mock 文本
"""
from __future__ import annotations

import argparse
import copy
import json
import logging
import re
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional

from pydantic import ValidationError

from backend.agents.prompts import (
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_MODIFY,
    USER_PROMPT_TEMPLATE,
)
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

# 第二轮新增:reflect-loop 上限(项目方案 §3.3 Tool 7 反思)
_MAX_REFLECT_ATTEMPTS = 3

# 第二轮新增:每城市免费默认景点(modify 规则"加景点"用)
_FREE_ATTRACTION_BY_CITY: dict[str, dict] = {
    "武汉": {"name": "武汉大学", "type": "景点", "duration_hours": 2, "cost": 0,
             "lat": 30.5418, "lng": 114.3650, "description": "樱花城堡", "emoji": "🎓"},
    "西安": {"name": "大雁塔广场", "type": "景点", "duration_hours": 1.5, "cost": 0,
             "lat": 34.2196, "lng": 108.9637, "description": "免费文化广场", "emoji": "🗼"},
    "成都": {"name": "人民公园", "type": "景点", "duration_hours": 1.5, "cost": 0,
             "lat": 30.6536, "lng": 104.0668, "description": "老成都茶馆", "emoji": "🌳"},
    "北京": {"name": "奥林匹克公园", "type": "景点", "duration_hours": 2, "cost": 0,
             "lat": 40.0021, "lng": 116.3972, "description": "鸟巢水立方外景", "emoji": "🏟️"},
    "杭州": {"name": "西湖", "type": "景点", "duration_hours": 3, "cost": 0,
             "lat": 30.2425, "lng": 120.1505, "description": "免费 5A 景区", "emoji": "🌊"},
    "厦门": {"name": "环岛路", "type": "景点", "duration_hours": 2, "cost": 0,
             "lat": 24.4798, "lng": 118.1180, "description": "免费海滨步道", "emoji": "🏖️"},
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


# ItemType Literal 兜底:把 LLM 自由发挥的 type 字符串归一到 6 个枚举值
_VALID_ITEM_TYPES = {"景点", "餐饮", "住宿", "交通", "门票", "其他"}


def _normalize_item_type(raw: object) -> str:
    """把任意字符串/对象归一到 ItemType 枚举值。

    常见误用:"夜景观赏"、"休闲度假"、"购物"、"看演出"、"citywalk"...
    全部映射到最近的合法枚举,避免 Pydantic Literal 校验失败。
    """
    if not isinstance(raw, str) or not raw.strip():
        return "其他"
    s = raw.strip()
    if s in _VALID_ITEM_TYPES:
        return s
    # 关键词启发式
    if any(k in s for k in ("景点", "景区", "公园", "博物馆", "古镇", "寺", "塔", "楼", "观景", "夜游", "夜景", "citywalk", "散步", "漫步", "游览", "参观")):
        return "景点"
    if any(k in s for k in ("餐", "吃", "美食", "小吃", "餐厅", "饭店", "火锅", "烧烤", "早餐", "午餐", "晚餐", "夜宵")):
        return "餐饮"
    if any(k in s for k in ("酒店", "民宿", "客栈", "住宿", "旅馆", "入住", "宾馆")):
        return "住宿"
    if any(k in s for k in ("交通", "打车", "地铁", "公交", "高铁", "火车", "飞机", "航班", "自驾", "出行", "车")):
        return "交通"
    if any(k in s for k in ("门票", "票", "入场", "预约", "演出票")):
        return "门票"
    return "其他"


def _normalize_plan_dict(plan_dict: dict) -> dict:
    """规范化 LLM 输出的 plan dict,把每个 item.type 归一到 ItemType。"""
    days = plan_dict.get("days") or []
    for d in days:
        items = d.get("items") or []
        for item in items:
            if isinstance(item, dict) and "type" in item:
                item["type"] = _normalize_item_type(item.get("type"))
    return plan_dict


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
        self.session_store = session_store  # 预留,本轮由成员 A 临时实现
        self._last_tools_called: list[str] = []

    # ================================================================== #
    # 主入口:plan() - 第二轮加 reflect-loop(最多 3 次反射)
    # ================================================================== #
    def plan(self, request: dict) -> dict:
        """生成完整行程。返回 dict(严格符合 PlanResponse schema)。

        Args:
            request: 必须含 city/days/start_date/budget;可选 preferences/people/departure

        **第二轮新增**:plan() 主循环拿到最终 JSON 后,触发 reflect-loop:
        - 最多 _MAX_REFLECT_ATTEMPTS(3) 次反射
        - 不通过则按 suggestion 规则做局部修复(超支→重算预算,景点不足→补景点)
        - 修复后再 reflect,3 次不通过强制返回

        **第三轮新增**:错误兜底加固
        - LLMUnavailable → 中文友好 message + fallback
        - ValidationError → 友好提示 + fallback
        - RuntimeError → 兜底
        """
        # 1. 内部校验
        try:
            AgentRequest.model_validate(request)
        except ValidationError as exc:
            logger.warning("AgentRequest 校验失败(%s),触发 fallback", exc)
            fallback = self._fallback_plan(request)
            first_err = exc.errors()[0] if exc.errors() else {}
            field = ".".join(str(x) for x in first_err.get("loc", []))
            msg = first_err.get("msg", "validation failed")
            # 保留 "validation" 关键字(老测试断言) + 中文友好 message(给前端)
            fallback["error"] = f"validation: {field} {msg} | 请求参数校验失败:字段 {field} {msg}"
            fallback["success"] = False
            return fallback

        # 2. 主循环
        try:
            plan_dict = self._call_llm_with_tools_loop(request)
            if not plan_dict or "trip_summary" not in plan_dict:
                raise RuntimeError("LLM 未返回含 trip_summary 的合法 JSON")
            # LLM 经常给出 "夜景观赏"/"休闲度假" 这类自由 type,
            # 归一到 ItemType 枚举(景点/餐饮/住宿/交通/门票/其他),
            # 避免 Pydantic Literal 校验失败导致 fallback。
            plan_dict = _normalize_plan_dict(plan_dict)
            plan = Plan.model_validate(plan_dict)

            # 3. **第二轮新增**:reflect-loop
            plan, reflect_log = self._reflect_loop(plan, request)

            return PlanResponse(
                success=True,
                session_id=self._generate_session_id(request),
                plan=plan,
                tools_called=list(self._last_tools_called),
            ).model_dump(mode="json")
        except LLMUnavailable as exc:
            logger.warning("LLM 不可用(%s),触发 fallback", exc)
            fallback = self._fallback_plan(request)
            # 第三轮:返中文友好 message(给前端),但保留原 exc 文本(给日志/老测试)
            fallback["error"] = (
                f"{exc} | AI 服务暂不可用(DashScope 超时/限流),已为您展示兜底行程。"
                "请稍后重试或联系管理员。"
            )
            fallback["success"] = False
            return fallback
        except (RuntimeError, ValueError) as exc:
            logger.warning("主流程失败(%s),触发 fallback", exc)
            fallback = self._fallback_plan(request)
            fallback["error"] = f"生成行程时出错:{exc}。已为您展示兜底行程。"
            fallback["success"] = False
            return fallback

    # ================================================================== #
    # 第二轮新增:reflect-loop 主逻辑
    # ================================================================== #
    def _reflect_loop(
        self,
        plan: Plan,
        request: dict,
    ) -> tuple[Plan, list[dict]]:
        """对 plan 做最多 3 次反思 + 规则修复。

        Returns:
            (修复后的 plan, 反思日志列表)
        """
        reflect_log: list[dict] = []
        current = plan

        for attempt in range(1, _MAX_REFLECT_ATTEMPTS + 1):
            reflection = self.reflect(current.model_dump(mode="json"), request)
            reflect_log.append({"attempt": attempt, **reflection})

            if reflection.get("is_satisfied"):
                logger.info("reflect-loop: 第 %d 次反射通过", attempt)
                return current, reflect_log

            logger.info(
                "reflect-loop: 第 %d 次反射未通过(%s),尝试规则修复",
                attempt, reflection.get("issues"),
            )
            # 规则修复
            fixed = self._apply_reflection_fix(current, reflection)
            if fixed is None:
                logger.warning("reflect-loop: 无可应用的修复,强制返回")
                return current, reflect_log
            current = fixed

        logger.warning("reflect-loop: 达到 %d 次上限,强制返回", _MAX_REFLECT_ATTEMPTS)
        return current, reflect_log

    def _apply_reflection_fix(self, plan: Plan, reflection: dict) -> Plan | None:
        """根据 reflection.suggestion 做规则修复。

        Returns:
            修复后的 Plan,或者 None(无可应用的修复)。
        """
        suggestion = (reflection.get("suggestion") or "").strip()
        plan_dict = plan.model_dump(mode="json")

        # 修复 1:超支 → 重新算 budget_breakdown
        if "calculate_budget" in suggestion.lower() or "超支" in suggestion or "预算" in suggestion:
            if "重新计算" in suggestion or "重算" in suggestion or "超支" in suggestion:
                # 把总预算从 breakdown 各项按比例压缩到 request.budget 以内
                bd = plan_dict.get("budget_breakdown") or {}
                current_total = sum(float(v or 0) for v in bd.values())
                req_budget = float(self._last_request_budget or 1500)
                if current_total > req_budget * 1.05 and current_total > 0:
                    scale = (req_budget * 0.95) / current_total  # 压缩到 95% 内
                    for k in list(bd.keys()):
                        bd[k] = round(float(bd[k]) * scale, 2)
                    plan_dict["budget_breakdown"] = bd
                    logger.info("规则修复: budget_breakdown 按比例压缩 scale=%.3f", scale)
                    return Plan.model_validate(plan_dict)

        # 修复 2:景点不足 → 补景点
        if "search_attractions" in suggestion.lower() or "补全景点" in suggestion:
            city = plan_dict.get("trip_summary", {}).get("city", "武汉")
            free_attraction = _FREE_ATTRACTION_BY_CITY.get(
                city, {"name": f"{city}城市公园", "type": "景点", "duration_hours": 1.5,
                       "cost": 0, "lat": 0, "lng": 0, "description": "免费兜底景点", "emoji": "🌳"},
            )
            days_list = plan_dict.get("days") or []
            if days_list and len(days_list) < int(self._last_request_days or 0):
                # 不足,补一天
                new_day_num = len(days_list) + 1
                plan_dict["days"].append(
                    {
                        "day": new_day_num,
                        "date": _add_days(plan_dict["trip_summary"]["start_date"], new_day_num - 1),
                        "items": [{"time": "10:00", **free_attraction}],
                        "day_cost": free_attraction.get("cost", 0),
                    }
                )
                return Plan.model_validate(plan_dict)

        # 修复 3:活动过密 → 删最后一个
        if "精简" in suggestion or "过密" in suggestion:
            for d in plan_dict.get("days") or []:
                if len(d.get("items") or []) > 5:
                    d["items"] = d["items"][:5]
                    logger.info("规则修复: Day %s 精简到 5 个活动", d.get("day"))
                    return Plan.model_validate(plan_dict)

        return None

    # ================================================================== #
    # 主循环
    # ================================================================== #
    def _call_llm_with_tools_loop(self, request: dict) -> Optional[dict]:
        self._last_tools_called = []
        # 记录给 reflect-loop 用
        self._last_request_budget = request.get("budget")
        self._last_request_days = request.get("days")

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
                    # DashScope 兼容模式不接受 OpenAI tool message 多余的 name 字段,
                    # 严格按 {"role":"tool","tool_call_id":..,"content":..} 三字段构造,
                    # 避免后端把它误判成 list-content 格式返回 400。
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": tool_result if isinstance(tool_result, str) else json.dumps(tool_result, ensure_ascii=False),
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

    # ================================================================== #
    # 第二轮新增:modify() - 多轮对话修改
    # ================================================================== #
    def modify(self, session_id: str, message: str, current_plan: dict) -> dict:
        """多轮对话修改行程(P1-4 / 方案 §3.5)。

        Args:
            session_id: 会话 ID(用于从 session_store 取历史)
            message: 用户指令,例如"把第 2 天下午改成湖北省博物馆"
            current_plan: 当前完整行程 dict(PlanResponse.plan 序列化)

        Returns:
            {
              "reply": str,
              "updated_plan": dict(完整新 Plan),
              "diff": {"day": int|None, "removed": str|None, "added": str|None}
            }

        **MOCK 模式退化**:不走 LLM,按 message 关键字做规则替换:
        - 含"换"/"改成" → 替换对应 day 末项的 name
        - 含"减预算" / "砍预算" / 数字 → budget_breakdown × 缩放系数
        - 含"加"/"增加" → append 免费景点到末项
        - 含"住"/"酒店" → 加一晚住宿(简化为追加 住宿=300)
        """
        # 1. 拿历史(可选,session_store 为 None 时返空)
        history: list[dict] = []
        if self.session_store is not None:
            try:
                history = self.session_store.get_history(session_id, last_n=10)
            except Exception as exc:  # noqa: BLE001
                logger.warning("get_history 失败: %s", exc)

        # 2. 构造 messages
        plan_json = json.dumps(current_plan, ensure_ascii=False, indent=2)
        user_msg = (
            f"当前行程:\n{plan_json}\n\n"
            f"用户指令:{message}"
        )

        messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT_MODIFY}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_msg})

        # 简单指令白名单:只有非常明确的"换/改成/加预算/住宿"才走规则快路径。
        # 之前关键词列表里"改"字太宽泛,"再修改一下"也会命中,导致所有对话都被截到
        # mock 规则路径,真实 LLM 永远没机会跑。改成更精确的整词/词组匹配。
        simple_modify = any(
            keyword in message
            for keyword in (
                "\u6362\u666f\u70b9",          # 换景点
                "\u6539\u6210",                # 改成
                "\u6362\u6210",                # 换成
                "\u66ff\u6362\u4e3a",          # 替换为
                "\u51cf\u9884\u7b97",          # 减预算
                "\u780d\u9884\u7b97",          # 砍预算
                "\u52a0\u9152\u5e97",          # 加酒店
                "\u52a0\u4f4f\u5bbf",          # 加住宿
                "\u8ba2\u9152\u5e97",          # 订酒店
                "\u8ba2\u623f",                # 订房
            )
        ) and not any(  # 但如果包含自然语言意图更强的词,优先走 LLM
            soft in message
            for soft in ("\u54ea\u91cc", "\u600e\u4e48", "\u4e3a\u4ec0\u4e48", "\u54ea\u4e9b", "\u4ec0\u4e48\u5730\u65b9", "\u5403\u996d", "\u98df\u5802", "\u5403\u4ec0\u4e48")
        )

        # 3. 优先真实 LLM,简单指令才走规则快路径;LLM 不可用时退到规则兜底
        if Config.MOCK_LLM or simple_modify:
            result = self._mock_modify_impl(message, current_plan)
        else:
            # 真实 LLM 调用
            try:
                resp = self.llm.chat(messages, temperature=0.3)
                content = resp.get("content") or ""
                extracted = _extract_json(content) or {}
                result = {
                    "reply": extracted.get("reply") or "已按您的要求修改行程。",
                    "updated_plan": extracted.get("updated_plan") or current_plan,
                    "diff": extracted.get("diff") or {"day": None, "removed": None, "added": None},
                }
            except LLMUnavailable as exc:
                logger.warning("modify LLM 不可用,降级到规则: %s", exc)
                result = self._mock_modify_impl(message, current_plan)

        # 4. Pydantic 校验 updated_plan,失败回退到 current_plan
        try:
            updated = result.get("updated_plan") or current_plan
            validated = Plan.model_validate(updated)
            result["updated_plan"] = validated.model_dump(mode="json")
        except ValidationError as exc:
            logger.warning("modify 输出的 updated_plan 校验失败(%s),回退到原 plan", exc)
            result["updated_plan"] = current_plan
            result["reply"] = f"修改结果无法通过结构校验,已保留原行程。({exc.errors()[0]['msg']})"
            result["diff"] = {"day": None, "removed": None, "added": None}

        # 5. 写回 session_store(可选)
        if self.session_store is not None:
            try:
                self.session_store.append_message(session_id, {"role": "user", "content": message})
                self.session_store.append_message(
                    session_id, {"role": "assistant", "content": result.get("reply", "")}
                )
                self.session_store.save_plan(session_id, result["updated_plan"])
            except Exception as exc:  # noqa: BLE001
                logger.warning("session_store 写入失败: %s", exc)

        return result

    def _mock_modify_impl(self, message: str, current_plan: dict) -> dict:
        """Rule-based itinerary modification used in MOCK_LLM mode."""
        plan = copy.deepcopy(current_plan)
        days_list = plan.get("days") or []
        bd = plan.get("budget_breakdown") or {}
        tips = list(plan.get("tips") or [])
        diff: dict = {"day": None, "removed": None, "added": None}
        reply = "\u5df2\u6309\u60a8\u7684\u8981\u6c42\u4fee\u6539\u884c\u7a0b\u3002"

        day_match = re.search(r"\u7b2c\s*(\d+)\s*\u5929", message) or re.search(r"day\s*(\d+)", message, re.IGNORECASE)
        target_day = int(day_match.group(1)) if day_match else None

        def _target_day_index() -> int | None:
            if not days_list:
                return None
            if target_day is not None and 1 <= target_day <= len(days_list):
                return target_day - 1
            return 0

        def _extract_new_name() -> str | None:
            known_names = ["\u6e56\u5317\u7701\u535a\u7269\u9986", "\u9ec4\u9e64\u697c", "\u4e1c\u65b9\u660e\u73e0", "\u9655\u897f\u5386\u53f2\u535a\u7269\u9986"]
            for name in known_names:
                if name in message:
                    return name
            match = re.search(r"(?:\u6539\u6210|\u6539\u4e3a|\u6362\u6210|\u6362\u4e3a|\u66ff\u6362\u6210|\u66ff\u6362\u4e3a)\s*([^\uff0c\u3002\uff1b;,\s]+)", message)
            return match.group(1).strip() if match else None

        def _known_attraction_patch(name: str) -> dict:
            known = {
                "\u6e56\u5317\u7701\u535a\u7269\u9986": {"cost": 0, "lat": 30.5619, "lng": 114.3592, "emoji": "\U0001f3db\ufe0f"},
                "\u9ec4\u9e64\u697c": {"cost": 80, "lat": 30.5438, "lng": 114.3055, "emoji": "\U0001f3ef"},
                "\u4e1c\u65b9\u660e\u73e0": {"cost": 199, "lat": 31.2397, "lng": 121.4998, "emoji": "\U0001f5fc"},
                "\u9655\u897f\u5386\u53f2\u535a\u7269\u9986": {"cost": 0, "lat": 34.2216, "lng": 108.9537, "emoji": "\U0001f3db\ufe0f"},
            }
            data = known.get(name, {})
            return {"name": name, "description": f"\u5df2\u6309\u7528\u6237\u8981\u6c42\u66ff\u6362\u4e3a{name}", **data}

        new_name = _extract_new_name()
        if new_name and any(k in message for k in ("\u6362", "\u6539", "\u66ff\u6362")):
            day_index = _target_day_index()
            if day_index is not None:
                day = days_list[day_index]
                items = day.get("items") or []
                if items:
                    item_index = len(items) - 1
                    removed_name = items[item_index].get("name", "")
                    items[item_index] = {**items[item_index], **_known_attraction_patch(new_name)}
                    day["items"] = items
                    day["day_cost"] = sum(float(item.get("cost", 0) or 0) for item in items)
                    real_day = day_index + 1
                    diff.update(day=real_day, removed=removed_name, added=new_name)
                    reply = f"\u5df2\u5c06 Day {real_day} \u7684{removed_name}\u6539\u4e3a{new_name}\u3002"

        elif "\u9884\u7b97" in message or re.search(r"\d{3,5}\s*(?:\u5143|\u5757|\uffe5|\xa5)?", message):
            numbers = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", message)]
            target_numbers = [num for num in numbers if num >= 100]
            target = target_numbers[-1] if target_numbers else None
            current_total = sum(float(v or 0) for v in bd.values())
            scale = (target / current_total) if target and current_total > 0 else 0.8
            for key in list(bd.keys()):
                bd[key] = round(float(bd[key] or 0) * scale, 2)
            plan["budget_breakdown"] = bd
            if target:
                plan.setdefault("trip_summary", {})["total_budget"] = target
                reply = f"\u5df2\u6309\u6bd4\u4f8b\u8c03\u6574\u9884\u7b97\u5230 {target:.0f} \u5143\u5de6\u53f3\u3002"
            else:
                reply = "\u5df2\u6309\u6bd4\u4f8b\u538b\u7f29\u9884\u7b97\u3002"
            diff["day"] = None

        elif any(k in message for k in ("\u52a0", "\u589e\u52a0", "\u52a0\u4e00\u4e2a", "\u6dfb\u4e00\u4e2a")):
            city = (plan.get("trip_summary") or {}).get("city", "\u6b66\u6c49")
            free = _FREE_ATTRACTION_BY_CITY.get(city, {"name": f"{city}\u57ce\u5e02\u516c\u56ed", "type": "\u666f\u70b9", "duration_hours": 1.5, "cost": 0, "lat": 0, "lng": 0, "description": "\u514d\u8d39\u515c\u5e95\u666f\u70b9", "emoji": "\U0001f33f"})
            target = target_day if target_day is not None else len(days_list)
            if 1 <= target <= len(days_list):
                day = days_list[target - 1]
                items = day.get("items") or []
                items.append({"time": "16:00", **free})
                day["items"] = items
                day["day_cost"] = sum(float(item.get("cost", 0) or 0) for item in items)
                diff.update(day=target, added=free["name"])
                reply = f"\u5df2\u5728 Day {target} \u8ffd\u52a0\u514d\u8d39\u666f\u70b9{free['name']}\u3002"
            else:
                tips.append(f"\u5df2\u8bb0\u5f55\u52a0\u666f\u70b9\u9700\u6c42\uff0c\u4f46 Day {target} \u4e0d\u5b58\u5728\uff0c\u6682\u672a\u6267\u884c\u3002")

        elif any(k in message for k in ("\u4f4f", "\u9152\u5e97", "\u8ba2\u623f")):
            if days_list:
                day = days_list[-1]
                items = day.get("items") or []
                hotel = {"time": "20:00", "type": "\u4f4f\u5bbf", "name": "\u7ecf\u6d4e\u578b\u9152\u5e97(\u6a21\u62df)", "duration_hours": 8, "cost": 300, "emoji": "\U0001f3e8"}
                items.append(hotel)
                day["items"] = items
                day["day_cost"] = sum(float(item.get("cost", 0) or 0) for item in items)
                bd["\u4f4f\u5bbf"] = round(float(bd.get("\u4f4f\u5bbf", 0) or 0) + 300, 2)
                plan["budget_breakdown"] = bd
                diff.update(day=len(days_list), added=hotel["name"])
                reply = f"\u5df2\u5728 Day {len(days_list)} \u672b\u5c3e\u8ffd\u52a0 1 \u665a\u4f4f\u5bbf\u3002"

        if reply == "\u5df2\u6309\u60a8\u7684\u8981\u6c42\u4fee\u6539\u884c\u7a0b\u3002":
            reply = (
                f"\u6536\u5230\u60a8\u7684\u4fee\u6539\u9700\u6c42\u3002"
                f"\u5982\u679c\u60a8\u60f3\u8c03\u6574\u9884\u7b97\u3001\u66f4\u6362\u666f\u70b9\u3001"
                f"\u6dfb\u52a0\u4f4f\u5bbf\u6216\u6539\u53d8\u540c\u884c\u4eba\u7fa4\uff0c"
                f"\u8bf7\u544a\u8bc9\u6211\u5177\u4f53\u8981\u6c42\uff0c\u6211\u4f1a\u4e3a\u60a8\u91cd\u65b0\u8c03\u6574\u3002"
            )

        plan["days"] = days_list
        plan["tips"] = tips
        return {"reply": reply, "updated_plan": plan, "diff": diff}

    # ================================================================== #
    # Fallback
    # ================================================================== #
    def _fallback_plan(self, request: dict) -> dict:
        """3 城演示数据轮换兜底(第三轮新增)。

        候选路径(按优先级):
        1. data/mock_plans/{city}_{days}day_{budget}.json  ← 用户精确请求
        2. data/mock_plans/{city}_3day_1500.json           ← 同一城市任意 days/budget
        3. data/mock_plans/{city}.json                    ← 城市直接命名
        4. data/mock_plans/wuhan_3day_1500.json           ← 终极兜底(武汉演示数据)
        5. 全部失败 → _minimal_plan 内存兜底
        """
        city = (request.get("city") or "武汉").strip()
        try:
            days_n = int(request.get("days") or 3)
        except (TypeError, ValueError):
            days_n = 3
        try:
            budget_n = int(request.get("budget") or 1500)
        except (TypeError, ValueError):
            budget_n = 1500

        candidates: list[Path] = [
            # 精确匹配
            Config.MOCK_PLANS_DIR / f"{_slug(city)}_{days_n}day_{budget_n}.json",
            # 城市同款(任意 days/budget)
            Config.MOCK_PLANS_DIR / f"{_slug(city)}_3day_1500.json",
            # 中文城市名
            Config.MOCK_PLANS_DIR / f"{city}_3day_1500.json",
            Config.MOCK_PLANS_DIR / f"{city}.json",
            # 终极兜底(由本轮 chengdu_2day_2000.json / wuhan_3day_1500.json / xian_3day_3500.json 共 3 城覆盖)
            Config.MOCK_PLANS_DIR / "wuhan_3day_1500.json",
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
                        session_id=self._generate_session_id(request),
                        plan=plan,
                        tools_called=["fallback"],
                        fallback=True,
                    ).model_dump(mode="json")
                except (OSError, json.JSONDecodeError, ValueError) as exc:
                    logger.warning("fallback 文件 %s 加载失败: %s", path, exc)

        # 终极兜底:内存最小 Plan
        minimal = self._minimal_plan(request)
        return PlanResponse(
            success=True,
            session_id=self._generate_session_id(request),
            plan=minimal,
            tools_called=["fallback_minimal"],
            fallback=True,
        ).model_dump(mode="json")

    @staticmethod
    def _generate_session_id(request: dict) -> str:
        """第三轮新增:后端自动生成 session_id(消除文档/代码冲突)。

        格式:`ses_{YYYYMMDD}_{uuid4前8位}`
        D 接管后可以忽略这个字段,改用 FastAPI 层生成。
        """
        today = datetime.now().strftime("%Y%m%d")
        return f"ses_{today}_{uuid.uuid4().hex[:8]}"

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

    # ================================================================== #
    # 反射(第二轮升级:接 reflect-loop)
    # ================================================================== #
    def reflect(self, plan: dict, request: dict) -> dict:
        """对 plan 做反思(规则版,Config.MOCK_LLM=false 时可切 LLM 增强版)。

        MOCK 模式:走 self_reflect 工具(规则版)
        真实 LLM 模式:同上(工具内部自动切 LLM 增强)

        返回 dict:{"is_satisfied", "issues", "suggestion"}
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


__all__ = ["PlanAgent", "_extract_json"]
