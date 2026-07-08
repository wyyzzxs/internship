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
import time
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
                kwargs: dict[str, Any] = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                }
                if openai_tools:
                    kwargs["tools"] = openai_tools
                    kwargs["tool_choice"] = "auto"
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
        """Mock 模式:始终返回无 tool_call 的纯文本 JSON 行程。

        内容与 data/mock_plans/wuhan_3day_1500.json 严格同构,
        PlanAgent 提取 JSON → Pydantic 校验即可通过。
        """
        logger.info("MOCK_LLM=true, 返回 mock 行程文本(len=%d)", len(self._MOCK_PLAN_TEXT))
        return {
            "role": "assistant",
            "content": self._MOCK_PLAN_TEXT,
            "tool_calls": None,
            "raw": None,
        }

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