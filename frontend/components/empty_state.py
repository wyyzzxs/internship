"""空状态 — 玻璃卡片风格。"""

from __future__ import annotations

import streamlit as st


def render_empty_state(hint: str) -> None:
    st.markdown(
        f"""
        <div class="hero-panel" style="padding:56px 32px;text-align:center;">
            <div style="width:48px;height:3px;background:linear-gradient(90deg,var(--accent),var(--accent3));
                margin:0 auto 24px;border-radius:2px;"></div>
            <h3 style="color:var(--text);margin-bottom:12px;font-weight:600;letter-spacing:0.03em;">暂无行程</h3>
            <p style="color:var(--muted);margin-bottom:32px;line-height:1.6;max-width:480px;margin-left:auto;margin-right:auto;">{hint}</p>
            <div style="display:flex;justify-content:center;gap:40px;flex-wrap:wrap;color:var(--muted);font-size:0.88rem;">
                <div><span style="color:var(--accent);font-weight:600;">01</span> 填写需求</div>
                <div><span style="color:var(--accent2);font-weight:600;">02</span> 生成行程</div>
                <div><span style="color:var(--accent3);font-weight:600;">03</span> 查看结果</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
