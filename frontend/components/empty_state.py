"""空状态 — 玻璃卡片风格。"""

from __future__ import annotations

import streamlit as st


def render_empty_state(hint: str) -> None:
    st.markdown(
        f"""
        <div class="hero-panel" style="padding:48px 24px;">
            <div style="font-size:56px;margin-bottom:16px;">✈️ 🗺️ 🍜</div>
            <h3 style="color:var(--text);margin-bottom:10px;">还没有行程</h3>
            <p style="color:var(--muted);margin-bottom:28px;">{hint}</p>
            <div style="display:flex;justify-content:center;gap:32px;flex-wrap:wrap;color:var(--muted);font-size:0.92rem;">
                <div><b style="color:var(--accent);">①</b> 填写左侧需求</div>
                <div><b style="color:var(--accent2);">②</b> 点击生成行程</div>
                <div><b style="color:var(--accent3);">③</b> 查看地图 / 预算</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
