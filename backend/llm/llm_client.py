"""LLM 客户端封装:OpenAI 兼容模式调 DashScope,带指数退避重试 + MOCK 短路。

设计要点(项目方案 §3.4 / §14.2):
- 用 openai SDK 兼容模式,base_url 指向 DashScope
- chat():支持 tools 参数(自动转 OpenAI function-calling);返回归一化 dict
- 指数退避:429/500/503 等可重试状态码触发,2^i 秒,最多 3 次
- 失败抛 LLMUnavailable,PlanAgent 兜底
- MOCK_LLM=true 时不调真接口,直接返回 mock 内容(供 PlanAgent fallback 或纯 demo 用)
"""
from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Iterator

from openai import APIStatusError, OpenAI, RateLimitError

from backend import config as _config_module
from backend.config import Config  # noqa: F401 - 保留供类型/外部使用

logger = logging.getLogger("backend.llm")


class LLMUnavailable(RuntimeError):
    """LLM 调用在重试后仍失败的兜底异常。"""


# --------------------------------------------------------------------------- #
# 工具转换 & 重试判定
# --------------------------------------------------------------------------- #
def _retryable(exc: BaseException) -> bool:
    """判定异常是否值得重试。支持 duck typing(测试用 MagicMock 也能命中)。"""
    # OpenAI 原生类型优先
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code in {408, 409, 425, 429, 500, 502, 503, 504}
    # 兜底:任何带 .status_code 整型属性的异常都按状态码判定
    code = getattr(exc, "status_code", None)
    if isinstance(code, int) and code in {408, 409, 425, 429, 500, 502, 503, 504}:
        return True
    return False


def _to_openai_tools(tools: list | None) -> list[dict] | None:
    """把 LangChain BaseTool 列表转 OpenAI function-calling 格式。

    输入可以是 LangChain StructuredTool / BaseTool(有 name/description/args 属性),
    也可以是已序列化的 dict。
    """
    if not tools:
        return None
    out: list[dict] = []
    for t in tools:
        if hasattr(t, "name") and hasattr(t, "description") and hasattr(t, "args"):
            args_schema = t.args
            # args 在 langchain-core 0.2.x 是 Pydantic v2 BaseModel
            if hasattr(args_schema, "model_json_schema"):
                parameters = args_schema.model_json_schema()
            elif hasattr(args_schema, "schema"):
                parameters = args_schema.schema()
            else:  # pragma: no cover - 兜底
                parameters = {"type": "object", "properties": {}}
            out.append(
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": parameters,
                    },
                }
            )
        elif isinstance(t, dict):
            out.append(t)
    return out or None


# --------------------------------------------------------------------------- #
# 主类
# --------------------------------------------------------------------------- #
class LLMClient:
    """OpenAI 兼容模式 LLM 客户端(DashScope qwen-plus 等)。

    用法:
        client = LLMClient()
        resp = client.chat(messages, tools=[...])  # {"content", "tool_calls", "raw"}
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.model = model or Config.LLM_MODEL
        self.api_key = (api_key or Config.DASHSCOPE_API_KEY or "").strip()
        self.base_url = base_url or Config.LLM_BASE_URL
        self._client: Any | None = None

    @property
    def client(self) -> Any:
        """惰性实例化 OpenAI client,便于测试时通过 `_client` 直接替换。"""
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    # ------------------------------------------------------------------ #
    # 主入口
    # ------------------------------------------------------------------ #
    def chat(
        self,
        messages: list[dict],
        tools: list | None = None,
        temperature: float = 0.3,
        max_retries: int | None = None,
    ) -> dict:
        """同步调用,失败按指数退避重试。

        Args:
            messages: OpenAI 风格消息列表
            tools: LangChain BaseTool 列表或已序列化 dict(自动转 OpenAI 格式)
            temperature: 采样温度
            max_retries: 重试次数,默认走 Config.LLM_MAX_RETRIES

        Returns:
            归一化的 dict:{"role", "content", "tool_calls", "raw"}
                - content: str | None
                - tool_calls: list[{"id", "name", "arguments"}] | None

        Raises:
            LLMUnavailable: 重试耗尽后抛出。
        """
        # 动态读 Config.MOCK_LLM(避免 test_config reload 后模块级 Config 引用失效)
        if _config_module.Config.MOCK_LLM:
            return self._mock_chat(messages, tools)

        openai_tools = _to_openai_tools(tools)
        retries = max_retries if max_retries is not None else Config.LLM_MAX_RETRIES

        last_exc: BaseException | None = None
        for attempt in range(retries):
            try:
                # DashScope 兼容模式不允许 assistant.content=None(返回 400:
                # "if content is list. item must be dict and key[type] should in dict")。
                # 工具调用回合里 LLM 只回 tool_calls 不回 content,我们在送出去前
                # 把 None 归一成空串,避免第二轮 LLM 调用 400。
                norm_messages = []
                for m in messages:
                    m2 = dict(m)
                    if m2.get("content") is None and m2.get("role") == "assistant":
                        m2["content"] = ""
                    norm_messages.append(m2)
                kwargs: dict[str, Any] = {
                    "model": self.model,
                    "messages": norm_messages,
                    "temperature": temperature,
                }
                if openai_tools:
                    kwargs["tools"] = openai_tools
                    kwargs["tool_choice"] = "auto"
                logger.debug("LLM 请求: model=%s messages=%d tools=%d", self.model, len(norm_messages), len(openai_tools or []))
                resp = self.client.chat.completions.create(**kwargs)
                return self._normalize(resp)

            except Exception as exc:  # noqa: BLE001 - 统一兜底
                last_exc = exc
                if not _retryable(exc) or attempt == retries - 1:
                    break
                backoff = 2 ** attempt
                logger.warning(
                    "LLM 调用失败 (attempt %d/%d): %s, sleep %ds",
                    attempt + 1,
                    retries,
                    exc,
                    backoff,
                )
                time.sleep(backoff)

        logger.error("LLM 调用彻底失败: %s", last_exc)
        raise LLMUnavailable(str(last_exc) if last_exc else "LLM unavailable")

    def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.3,
    ) -> Iterator[str]:
        """流式调用,逐 token yield。失败不重试(留给上层 chat 兜底)。

        本轮未在 PlanAgent 接入,保留接口占位。
        """
        if Config.MOCK_LLM:
            mock = self._mock_chat(messages, None)
            for ch in mock["content"] or "":
                yield ch
            return

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            stream=True,
        )
        for chunk in stream:
            try:
                piece = chunk.choices[0].delta.content or ""
            except (AttributeError, IndexError):
                piece = ""
            if piece:
                yield piece

    # ------------------------------------------------------------------ #
    # 内部:归一化 & Mock
    # ------------------------------------------------------------------ #
    def _normalize(self, resp: Any) -> dict:
        """把 OpenAI Response 转成统一 dict 格式。"""
        try:
            msg = resp.choices[0].message
            content = getattr(msg, "content", None)
            tool_calls = getattr(msg, "tool_calls", None)
        except (AttributeError, IndexError):
            content, tool_calls = None, None

        tool_calls_norm: list[dict] | None = None
        if tool_calls:
            tool_calls_norm = []
            for tc in tool_calls:
                fn = getattr(tc, "function", None)
                args_raw = getattr(fn, "arguments", "{}") if fn else "{}"
                try:
                    parsed_args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                except json.JSONDecodeError:
                    parsed_args = {"_raw": args_raw}
                tool_calls_norm.append(
                    {
                        "id": getattr(tc, "id", None),
                        "name": getattr(fn, "name", None) if fn else None,
                        "arguments": parsed_args,
                    }
                )

        return {
            "role": "assistant",
            "content": content,
            "tool_calls": tool_calls_norm,
            "raw": resp,
        }

    def _mock_chat(self, messages: list[dict], tools: list | None) -> dict:
        """Mock 模式(第三轮修复):**根据 messages 里的 user 请求动态生成 plan**。

        行为:
        1. 解析最后一条 user message(USER_PROMPT_TEMPLATE 格式),提取 city/days/budget/...
        2. 优先尝试 data/mock_plans/{slug}_{days}day_{budget}.json
        3. 找不到 → data/mock_plans/wuhan_3day_1500.json
        4. 找不到 → 内置 _MOCK_PLAN_TEXT(武汉 3 天 1500 情侣)
        5. 还会模拟 1 次 search_attractions 工具调用,让 tools_called 看起来真实
        """
        req = self._parse_user_request(messages)
        plan_text = self._find_mock_plan_text(req)

        # 第一轮:模拟 1 次工具调用,让 tools_called 不空
        if tools and any(getattr(t, "name", "") == "search_attractions" for t in tools):
            # 检查 messages 里是否已有 tool 消息(第二轮就不重复调)
            has_tool_message = any(m.get("role") == "tool" for m in messages)
            if not has_tool_message:
                logger.info("MOCK_LLM=true, 模拟第 1 轮:调 search_attractions")
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "mock_call_001",
                            "name": "search_attractions",
                            "arguments": {
                                "city": req.get("city", "武汉"),
                                "tags": req.get("preferences", ["历史文化"]),
                                "top_k": 5,
                            },
                        }
                    ],
                    "raw": None,
                }

        logger.info(
            "MOCK_LLM=true, 返 mock 行程文本(city=%s, days=%s, budget=%s)",
            req.get("city"), req.get("days"), req.get("budget"),
        )
        return {
            "role": "assistant",
            "content": plan_text,
            "tool_calls": None,
            "raw": None,
        }

    def _parse_user_request(self, messages: list[dict]) -> dict:
        """从 messages 倒序找最后一条 user message,正则提取 city/days/budget/people/start_date。"""
        req: dict = {}
        for m in reversed(messages):
            if m.get("role") == "user":
                content = m.get("content", "")
                # USER_PROMPT_TEMPLATE 格式:
                #   城市:{city}
                #   天数:{days}
                #   出发日期:{start_date}
                #   预算:{budget} 元
                #   偏好:{preferences}
                #   同行人群:{people}
                m_city = re.search(r"城市[:：]\s*(\S+)", content)
                m_days = re.search(r"天数[:：]\s*(\d+)", content)
                m_date = re.search(r"出发日期[:：]\s*(\S+)", content)
                m_budget = re.search(r"预算[:：]\s*([\d.]+)\s*元", content)
                m_prefs = re.search(r"偏好[:：]\s*\[([^\]]*)\]", content)
                m_people = re.search(r"同行人群[:：]\s*(\S+)", content)

                if m_city:
                    req["city"] = m_city.group(1)
                if m_days:
                    req["days"] = int(m_days.group(1))
                if m_date:
                    req["start_date"] = m_date.group(1)
                if m_budget:
                    req["budget"] = float(m_budget.group(1))
                if m_prefs:
                    # 解析 ["历史","美食"] 这种
                    prefs_str = m_prefs.group(1)
                    req["preferences"] = [p.strip().strip('"\'') for p in prefs_str.split(",") if p.strip()]
                if m_people:
                    req["people"] = m_people.group(1)
                break
        return req

    def _find_mock_plan_text(self, req: dict) -> str:
        """根据 request 找最匹配的 mock plan。

        候选路径(按优先级,第三轮修复):
        1. data/mock_plans/{slug}_{days}day_{budget}.json    ← 精确匹配
        2. data/mock_plans/{slug}_{days}day_*.json          ← 同城市同 days 任意 budget (glob)
        3. data/mock_plans/{slug}_*day_*.json                ← 同城市任意 days/budget (glob)
        4. data/mock_plans/wuhan_3day_1500.json              ← 终极兜底
        5. _MOCK_PLAN_TEXT                                    ← 内存兜底
        """
        city = req.get("city", "武汉")
        try:
            days_n = int(req.get("days", 3))
        except (TypeError, ValueError):
            days_n = 3
        try:
            budget_n = int(req.get("budget", 1500))
        except (TypeError, ValueError):
            budget_n = 1500

        city_slug_map = {
            "武汉": "wuhan", "西安": "xian", "成都": "chengdu",
            "北京": "beijing", "杭州": "hangzhou", "厦门": "xiamen",
        }
        slug = city_slug_map.get(city, city.lower().replace(" ", "_"))

        data_dir = Config.DATA_DIR / "mock_plans"

        # 1. 精确匹配
        candidates: list[Path] = [
            data_dir / f"{slug}_{days_n}day_{budget_n}.json",
        ]
        # 2. 同城市同 days 任意 budget(glob)
        candidates.extend(sorted(data_dir.glob(f"{slug}_{days_n}day_*.json")))
        # 3. 同城市任意 days/budget(glob,排除 step 1 重复)
        candidates.extend(
            sorted(p for p in data_dir.glob(f"{slug}_*day_*.json") if p not in candidates)
        )
        # 4. 终极兜底
        candidates.append(data_dir / "wuhan_3day_1500.json")

        for path in candidates:
            if path.exists():
                try:
                    with path.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    logger.info("MOCK 找到演示数据: %s", path)
                    return json.dumps(data, ensure_ascii=False)
                except (OSError, json.JSONDecodeError) as exc:
                    logger.warning("MOCK 演示数据 %s 读取失败: %s", path, exc)

        logger.info("MOCK 没有匹配的演示数据,用内置 _MOCK_PLAN_TEXT 兜底")
        return self._MOCK_PLAN_TEXT

    # 内容与 data/mock_plans/wuhan_3day_1500.json 同步,
    # 便于 PlanAgent 在 mock 模式下提取出的 JSON 直接通过 Pydantic 校验。
    _MOCK_PLAN_TEXT: str = json.dumps(
        {
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
                },
                {
                    "date": "2025-07-09",
                    "weather": "多云",
                    "temp_high": 34,
                    "temp_low": 27,
                    "suggestion": "适合户外",
                },
                {
                    "date": "2025-07-10",
                    "weather": "阵雨",
                    "temp_high": 30,
                    "temp_low": 25,
                    "suggestion": "建议安排室内活动",
                },
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
                        },
                        {
                            "time": "12:00",
                            "type": "餐饮",
                            "name": "户部巷午餐",
                            "duration_hours": 1,
                            "cost": 50,
                            "lat": 30.5472,
                            "lng": 114.3061,
                            "description": "武汉特色小吃一条街",
                            "emoji": "🍜",
                        },
                        {
                            "time": "14:00",
                            "type": "景点",
                            "name": "武汉长江大桥",
                            "duration_hours": 1.5,
                            "cost": 0,
                            "lat": 30.5538,
                            "lng": 114.3125,
                            "description": "万里长江第一桥",
                            "emoji": "🌉",
                        },
                        {
                            "time": "18:30",
                            "type": "餐饮",
                            "name": "武昌鱼晚餐",
                            "duration_hours": 1.5,
                            "cost": 120,
                            "lat": 30.5520,
                            "lng": 114.3100,
                            "description": "湖北名菜武昌鱼",
                            "emoji": "🐟",
                        },
                    ],
                    "day_cost": 250,
                },
                {
                    "day": 2,
                    "date": "2025-07-09",
                    "items": [
                        {
                            "time": "09:30",
                            "type": "景点",
                            "name": "东湖风景区",
                            "duration_hours": 4,
                            "cost": 0,
                            "lat": 30.5505,
                            "lng": 114.3708,
                            "description": "中国第二大城中湖",
                            "emoji": "🌸",
                        },
                        {
                            "time": "13:30",
                            "type": "餐饮",
                            "name": "东湖农家菜",
                            "duration_hours": 1.5,
                            "cost": 90,
                            "lat": 30.5510,
                            "lng": 114.3650,
                            "description": "东湖周边特色菜",
                            "emoji": "🥬",
                        },
                        {
                            "time": "15:30",
                            "type": "景点",
                            "name": "湖北省博物馆",
                            "duration_hours": 2,
                            "cost": 0,
                            "lat": 30.5647,
                            "lng": 114.3396,
                            "description": "曾侯乙编钟所在地",
                            "emoji": "🏛️",
                        },
                    ],
                    "day_cost": 90,
                },
                {
                    "day": 3,
                    "date": "2025-07-10",
                    "items": [
                        {
                            "time": "09:30",
                            "type": "景点",
                            "name": "江汉路步行街",
                            "duration_hours": 2,
                            "cost": 0,
                            "lat": 30.5905,
                            "lng": 114.2720,
                            "description": "百年商业街",
                            "emoji": "🛍️",
                        },
                        {
                            "time": "12:00",
                            "type": "餐饮",
                            "name": "吉庆街午餐",
                            "duration_hours": 1.5,
                            "cost": 70,
                            "lat": 30.5880,
                            "lng": 114.2705,
                            "description": "武汉老字号美食",
                            "emoji": "🥘",
                        },
                        {
                            "time": "14:00",
                            "type": "景点",
                            "name": "武汉大学",
                            "duration_hours": 2,
                            "cost": 0,
                            "lat": 30.5418,
                            "lng": 114.3650,
                            "description": "雨天备选室内博物馆",
                            "emoji": "🌧️",
                        },
                    ],
                    "day_cost": 70,
                },
            ],
            "budget_breakdown": {
                "交通": 200,
                "住宿": 600,
                "门票": 80,
                "餐饮": 330,
                "其他": 60,
            },
            "tips": [
                "周一黄鹤楼闭馆,本次行程周二开始不受影响",
                "Day3 有阵雨,已把户外活动改为室内备选",
                "东湖绿道免费,可租共享单车环湖",
            ],
        },
        ensure_ascii=False,
    )


__all__ = ["LLMClient", "LLMUnavailable"]