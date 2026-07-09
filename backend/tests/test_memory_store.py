"""MemorySessionStore 测试 - CRUD + history 截断到 last_n。

覆盖:
- get_or_create(不存在则创建)
- save_plan(可覆盖,空 plan)
- append_message(累积)
- get_history(last_n 截断,默认 10)
- get_plan(返 dict 或 None)
- clear(清空)
"""
from __future__ import annotations

import pytest

from backend.db.memory_store import MemorySessionStore


@pytest.fixture
def store() -> MemorySessionStore:
    """每个测试一个新 store(内存 DB,隔离)。"""
    return MemorySessionStore()


# --------------------------------------------------------------------------- #
# CRUD 基础
# --------------------------------------------------------------------------- #
def test_get_or_create_new_session(store):
    s = store.get_or_create("ses_001", user_id="u1")
    assert s["session_id"] == "ses_001"
    assert s["user_id"] == "u1"
    assert s["current_plan_json"] == ""
    assert s["messages_json"] == "[]"


def test_get_or_create_existing_session(store):
    store.get_or_create("ses_002")
    s = store.get_or_create("ses_002")  # 第二次
    assert s["session_id"] == "ses_002"


def test_save_plan(store):
    plan = {"trip_summary": {"city": "武汉", "days": 3}, "days": []}
    store.save_plan("ses_003", plan)
    loaded = store.get_plan("ses_003")
    assert loaded == plan


def test_save_plan_overwrite(store):
    plan1 = {"trip_summary": {"city": "武汉"}, "days": []}
    plan2 = {"trip_summary": {"city": "西安"}, "days": []}
    store.save_plan("ses_004", plan1)
    store.save_plan("ses_004", plan2)
    assert store.get_plan("ses_004") == plan2


def test_get_plan_nonexistent(store):
    assert store.get_plan("ses_nonexistent") is None


# --------------------------------------------------------------------------- #
# messages 累积 + 截断
# --------------------------------------------------------------------------- #
def test_append_message(store):
    store.append_message("ses_005", {"role": "user", "content": "hi"})
    store.append_message("ses_005", {"role": "assistant", "content": "hello"})
    history = store.get_history("ses_005")
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "hi"}
    assert history[1] == {"role": "assistant", "content": "hello"}


def test_get_history_truncates_to_last_n(store):
    """累积 15 条,get_history(last_n=10) 只返后 10 条。"""
    for i in range(15):
        store.append_message("ses_trunc", {"role": "user", "content": f"msg-{i}"})

    history = store.get_history("ses_trunc", last_n=10)
    assert len(history) == 10
    # 最后一条应是 msg-14
    assert history[-1]["content"] == "msg-14"
    # 第一条应是 msg-5(从 0 开始,被截掉前 5 条)
    assert history[0]["content"] == "msg-5"


def test_get_history_default_last_n_is_10(store):
    """get_history 不传 last_n 时默认 10。"""
    for i in range(12):
        store.append_message("ses_default", {"role": "user", "content": f"m-{i}"})
    history = store.get_history("ses_default")
    assert len(history) == 10


def test_get_history_empty(store):
    """空会话返 [] 而非报错。"""
    assert store.get_history("ses_empty") == []


# --------------------------------------------------------------------------- #
# clear
# --------------------------------------------------------------------------- #
def test_clear(store):
    store.save_plan("ses_clear", {"a": 1})
    store.append_message("ses_clear", {"role": "user", "content": "x"})
    store.clear("ses_clear")
    assert store.get_plan("ses_clear") is None
    assert store.get_history("ses_clear") == []


# --------------------------------------------------------------------------- #
# 字段名对齐方案 §3.5
# --------------------------------------------------------------------------- #
def test_row_has_required_fields(store):
    """get_or_create 返回的 dict 必须含 §3.5 所有字段。"""
    s = store.get_or_create("ses_fields", user_id="u_test")
    for field in ("session_id", "user_id", "current_plan_json",
                  "messages_json", "created_at", "updated_at"):
        assert field in s, f"缺字段: {field}"
