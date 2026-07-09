"""Loading 骨架屏 + Agent 步骤进度 — P1-8。"""

from __future__ import annotations

import time

import streamlit as st

AGENT_STEPS = [
    ("检索景点知识库", 0.25),
    ("查询天气预报", 0.45),
    ("计算预算分配", 0.65),
    ("优化游览路线", 0.85),
    ("生成完整行程", 1.0),
]

SKELETON_CSS = """
<style>
.sk-row { height: 14px; background: linear-gradient(90deg,rgba(255,255,255,0.04) 25%,rgba(255,255,255,0.08) 50%,rgba(255,255,255,0.04) 75%);
  background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: 4px; margin: 8px 0; }
.sk-block { height: 120px; background: linear-gradient(90deg,rgba(255,255,255,0.03) 25%,rgba(255,255,255,0.07) 50%,rgba(255,255,255,0.03) 75%);
  background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: 12px; margin: 12px 0;
  border: 1px solid rgba(255,107,74,0.12); }
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
        status.markdown(f'<p style="color:var(--muted);font-size:0.9rem;">{label}</p>', unsafe_allow_html=True)
        progress.progress(pct, text=label)
        time.sleep(0.35)
    status.empty()
    progress.empty()


def render_skeleton() -> None:
    st.markdown(SKELETON_CSS, unsafe_allow_html=True)
