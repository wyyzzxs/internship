"""对话修改组件 — P1-4 UI 部分。"""

from __future__ import annotations

import streamlit as st

from utils.api_client import fetch_chat


def render_chat_box(plan: dict | None, session_id: str) -> None:
    if plan is None:
        st.info("请先生成行程，再进行对话修改。")
        return

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "assistant", "content": "您好！我可以帮您修改行程，例如：「把第 2 天下午改成博物馆」"}
        ]

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("输入修改指令，如：第三天加一个博物馆"):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.spinner("Agent 思考中..."):
            result = fetch_chat(session_id, prompt, plan)

        reply = result.get("reply", "已收到。")
        st.session_state.chat_messages.append({"role": "assistant", "content": reply})

        if result.get("updated_plan"):
            st.session_state.plan = result["updated_plan"]
            diff = result.get("diff")
            if diff:
                st.success(
                    f"已修改 Day {diff.get('day')}："
                    f"{diff.get('removed')} → {diff.get('added')}"
                )
        st.rerun()
