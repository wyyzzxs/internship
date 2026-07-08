"""Loading 骨架屏 + Agent 步骤进度 — P1-8。"""

from __future__ import annotations

import time

import streamlit as st

AGENT_STEPS = [
    ("🔍 检索景点知识库", 0.25),
    ("🌤️ 查询天气预报", 0.45),
    ("💰 计算预算分配", 0.65),
    ("🗺️ 优化游览路线", 0.85),
    ("✨ 生成完整行程", 1.0),
]

SKELETON_CSS = """
<style>
.sk-row { height: 18px; background: linear-gradient(90deg,#eee 25%,#f5f5f5 50%,#eee 75%);
  background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: 4px; margin: 8px 0; }
.sk-block { height: 120px; background: linear-gradient(90deg,#eee 25%,#f5f5f5 50%,#eee 75%);
  background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: 12px; margin: 12px 0; }
@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
</style>
<div class="sk-block"></div>
<div class="sk-row" style="width:80%"></div>
<div class="sk-row" style="width:60%"></div>
<div class="sk-row" style="width:90%"></div>
<div class="sk-block"></div>
"""


def run_agent_progress() -> None:
    progress = st.progress(0, text="Agent 启动中...")
    status = st.empty()
    for label, pct in AGENT_STEPS:
        status.info(label)
        progress.progress(pct, text=label)
        time.sleep(0.35)
    status.empty()
    progress.empty()


def render_skeleton() -> None:
    st.markdown(SKELETON_CSS, unsafe_allow_html=True)
