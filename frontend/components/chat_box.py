"""对话修改组件 — P1-4 UI 部分。"""

from __future__ import annotations

import streamlit as st

from utils.api_client import USE_MOCK, fetch_chat
from utils.data_loader import enrich_plan


def _format_diff(diff: dict | None) -> str | None:
    if not diff:
        return None
    if diff.get("type") == "budget":
        return f"预算已调整 → ¥{diff.get('new_budget', '?')}"
    day = diff.get("day")
    removed = diff.get("removed")
    added = diff.get("added")
    if day and removed and added:
        return f"Day {day}：{removed} → {added}"
    if day and added:
        return f"Day {day} 新增：{added}"
    if day and removed:
        return f"Day {day} 移除：{removed}"
    if added:
        return f"已新增：{added}"
    return None


def render_chat_box(plan: dict | None, session_id: str) -> None:
    if plan is None:
        st.info("请先生成行程，再进行对话修改。")
        return

    if USE_MOCK:
        st.caption("Mock 对话模式 · 后端 `/api/chat` 接入后自动切换为 Agent 修改")

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "assistant", "content": "您好！我可以帮您修改行程，例如：「把第 2 天下午改成博物馆」或「我想去西安电子科技大学一趟，重新安排」"}
        ]

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("输入修改指令，如：第三天加一个博物馆"):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        try:
            with st.spinner("Agent 思考中..."):
                result = fetch_chat(session_id, prompt, plan)
        except Exception as exc:
            result = {"success": False, "reply": f"请求失败：{exc}"}

        reply = result.get("reply", "已收到。")
        st.session_state.chat_messages.append({"role": "assistant", "content": reply})

        if result.get("success") is False:
            st.error(reply)
            st.rerun()
            return

        updated = result.get("updated_plan")
        if updated:
            st.session_state.plan = enrich_plan(updated)
            diff_text = _format_diff(result.get("diff"))
            if diff_text:
                st.success(diff_text)
            hist = st.session_state.setdefault("plan_history", [])
            hist.append(st.session_state.plan)

        st.rerun()
