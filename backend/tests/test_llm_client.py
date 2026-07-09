"""LLMClient 测试 - mock OpenAI client,验证重试/Mock/tool_calls 归一化。"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.llm.llm_client import LLMClient, LLMUnavailable


# --------------------------------------------------------------------------- #
# 测试辅助
# --------------------------------------------------------------------------- #
class _FakeAPIError(Exception):
    """模拟 openai APIStatusError - 带 status_code 属性。"""

    def __init__(self, status_code: int, message: str = "fake"):
        super().__init__(message)
        self.status_code = status_code


def _build_mock_response(content: str = "ok", tool_calls=None) -> MagicMock:
    """构造一个看起来像 openai SDK Response 的 MagicMock。"""
    resp = MagicMock()
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls or []
    resp.choices = [MagicMock(message=msg)]
    return resp


def _build_tool_call(call_id: str, name: str, args_json: str) -> MagicMock:
    tc = MagicMock()
    tc.id = call_id
    fn = MagicMock()
    fn.name = name
    fn.arguments = args_json
    tc.function = fn
    return tc


def _set_mock(client: LLMClient, fake_create) -> MagicMock:
    """给 LLMClient 装上 mock 的 OpenAI client。"""
    fake = MagicMock()
    fake.chat.completions.create = fake_create
    client._client = fake  # type: ignore[attr-defined]
    return fake


# --------------------------------------------------------------------------- #
# 测试用例
# --------------------------------------------------------------------------- #
def test_mock_mode_short_circuits(monkeypatch):
    """MOCK_LLM=true 时不调 OpenAI,直接返回 mock 内容。"""
    monkeypatch.setattr("backend.config.Config.MOCK_LLM", True)
    client = LLMClient()
    out = client.chat([{"role": "user", "content": "hi"}])
    assert out["role"] == "assistant"
    assert out["content"]
    assert out["tool_calls"] is None
    assert out["raw"] is None


def test_mock_responds_to_city_in_request(monkeypatch):
    """第三轮修复:LLM mock 必须根据 request 动态生成 plan(防回归)。

    验证:用户请求"西安 3 天 3500 亲子"时,mock 返回的 plan.trip_summary.city
    必须是"西安"(不是固定返武汉)。
    """
    monkeypatch.setattr("backend.config.Config.MOCK_LLM", True)
    client = LLMClient()
    # 用真实的 USER_PROMPT_TEMPLATE 格式
    from backend.agents.prompts import USER_PROMPT_TEMPLATE
    user_msg = USER_PROMPT_TEMPLATE.format(
        city="西安", days=3, start_date="2025-07-08", budget=3500,
        preferences=["历史", "亲子"], people="亲子", departure="武汉",
    )
    out = client.chat(
        messages=[{"role": "user", "content": user_msg}],
        tools=None,  # 不用工具,直接看 mock 返的 content
    )
    import json
    plan = json.loads(out["content"])
    assert plan["trip_summary"]["city"] == "西安", (
        f"mock 应返西安,实际 {plan['trip_summary']['city']}"
    )
    assert plan["trip_summary"]["days"] == 3
    assert plan["trip_summary"]["total_budget"] == 3500
    assert plan["trip_summary"]["people"] == "亲子"


def test_mock_simulates_search_attractions_first_call(monkeypatch):
    """第三轮修复:mock 第一次调 search_attractions 工具,让 tools_called 不空。"""
    from langchain_core.tools import tool

    @tool
    def search_attractions(city: str) -> str:
        """mock 测试用"""
        return '{"attractions": []}'

    monkeypatch.setattr("backend.config.Config.MOCK_LLM", True)
    client = LLMClient()
    out = client.chat(
        messages=[{"role": "user", "content": "test"}],
        tools=[search_attractions],
    )
    # 第一次应有 tool_call
    assert out["tool_calls"] is not None
    assert len(out["tool_calls"]) == 1
    assert out["tool_calls"][0]["name"] == "search_attractions"
    # content 为 None(等工具结果)
    assert out["content"] is None


def test_mock_returns_plan_after_tool_message(monkeypatch):
    """第三轮修复:第 2 次(messages 里已有 tool 消息)返 plan,不再调工具。"""
    from langchain_core.tools import tool

    @tool
    def search_attractions(city: str) -> str:
        """mock 测试用"""
        return '{"attractions": []}'

    monkeypatch.setattr("backend.config.Config.MOCK_LLM", True)
    client = LLMClient()
    # messages 已有 tool 消息 → 第 2 轮,直接返 plan
    out = client.chat(
        messages=[
            {"role": "user", "content": "test"},
            {"role": "tool", "content": "[]", "tool_call_id": "x", "name": "search_attractions"},
        ],
        tools=[search_attractions],
    )
    assert out["tool_calls"] is None
    assert out["content"]
    import json
    plan = json.loads(out["content"])
    assert "trip_summary" in plan


def test_retry_then_success(monkeypatch):
    """前 2 次 429,第 3 次成功 - 验证指数退避 + 最终成功。"""
    # 用字符串路径:pytest 在执行时动态解析,避免 test_config.py reload 后类身份变化
    monkeypatch.setattr("backend.config.Config.MOCK_LLM", False)
    calls = {"n": 0}

    def fake_create(**kwargs):
        calls["n"] += 1
        if calls["n"] < 3:
            raise _FakeAPIError(429, "rate limited")
        return _build_mock_response(content="done")

    client = LLMClient()
    _set_mock(client, fake_create)
    monkeypatch.setattr("backend.llm.llm_client.time.sleep", lambda _s: None)

    out = client.chat([{"role": "user", "content": "hi"}])
    assert calls["n"] == 3
    assert out["content"] == "done"


def test_retry_exhausted_raises_llm_unavailable(monkeypatch):
    """3 次重试都失败 → 抛 LLMUnavailable。"""
    monkeypatch.setattr("backend.config.Config.MOCK_LLM", False)

    def fake_create(**kwargs):
        raise _FakeAPIError(503, "service unavailable")

    client = LLMClient()
    _set_mock(client, fake_create)
    monkeypatch.setattr("backend.llm.llm_client.time.sleep", lambda _s: None)

    with pytest.raises(LLMUnavailable):
        client.chat([{"role": "user", "content": "hi"}], max_retries=2)


def test_non_retryable_raises_immediately(monkeypatch):
    """400 这种不可重试状态码直接抛 LLMUnavailable(不重试)。"""
    monkeypatch.setattr("backend.config.Config.MOCK_LLM", False)
    calls = {"n": 0}

    def fake_create(**kwargs):
        calls["n"] += 1
        raise _FakeAPIError(400, "bad request")

    client = LLMClient()
    _set_mock(client, fake_create)
    monkeypatch.setattr("backend.llm.llm_client.time.sleep", lambda _s: None)

    with pytest.raises(LLMUnavailable):
        client.chat([{"role": "user", "content": "hi"}])
    assert calls["n"] == 1


def test_tool_call_normalization(monkeypatch):
    """tool_calls 被正确解析成 {id, name, arguments(dict)}。"""
    monkeypatch.setattr("backend.config.Config.MOCK_LLM", False)

    tc = _build_tool_call("call_1", "search_attractions", '{"city": "武汉"}')
    resp = _build_mock_response(content=None, tool_calls=[tc])

    client = LLMClient()
    _set_mock(client, lambda **kw: resp)

    # 传一个假的 tool,只为触发 _to_openai_tools
    fake_tool = MagicMock()
    fake_tool.name = "search_attractions"
    fake_tool.description = "mock"
    fake_tool.args = MagicMock()
    fake_tool.args.model_json_schema = lambda: {
        "type": "object",
        "properties": {"city": {"type": "string"}},
    }

    out = client.chat([{"role": "user", "content": "hi"}], tools=[fake_tool])
    assert out["tool_calls"] is not None
    assert len(out["tool_calls"]) == 1
    assert out["tool_calls"][0]["name"] == "search_attractions"
    assert out["tool_calls"][0]["arguments"] == {"city": "武汉"}
    assert out["tool_calls"][0]["id"] == "call_1"


def test_chat_stream_yields_content_in_mock_mode(monkeypatch):
    """Mock 模式下,chat_stream 逐字符 yield mock content。"""
    monkeypatch.setattr("backend.config.Config.MOCK_LLM", True)
    client = LLMClient()
    chunks = list(client.chat_stream([{"role": "user", "content": "hi"}]))
    assert "".join(chunks)  # 至少 yield 出非空字符串