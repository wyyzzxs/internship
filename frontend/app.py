"""AI 智能旅游规划师 — 主入口。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

import streamlit as st

from components.budget_pie import render_budget_pie
from components.card_wall import render_card_wall
from components.chat_box import render_chat_box
from components.empty_state import render_empty_state
from components.export_panel import render_export_panel
from components.input_form import render_input_form
from components.loading import render_skeleton, run_agent_progress
from components.map_view import render_map
from components.summary_metrics import render_summary_metrics
from components.timeline import render_timeline
from components.trip_compare import render_trip_compare
from themes import get_theme_css
from utils.api_client import USE_MOCK, fetch_plan
from utils.i18n import t

st.set_page_config(
    page_title="AI 智能旅游规划师",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Session
for key, default in [
    ("plan", None), ("plan_response", None), ("session_id", ""),
    ("theme", "travel_night"), ("lang", "zh"), ("plan_history", []),
    ("show_heatmap", False), ("generating", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# Lottie 加载动画（P2-8）
try:
    from streamlit_lottie import st_lottie
    import requests

    @st.cache_data
    def _lottie(url: str):
        r = requests.get(url, timeout=5)
        return r.json() if r.status_code == 200 else None

    LOTTIE_URL = "https://assets5.lottiefiles.com/packages/lf20_usmfxgpd.json"
except ImportError:
    st_lottie = None


def main() -> None:
    st.markdown(get_theme_css(st.session_state.get("theme", "travel_night")), unsafe_allow_html=True)
    lang = st.session_state.get("lang", "zh")

    with st.sidebar:
        request = render_input_form(lang)
        lang = st.session_state.get("lang", lang)
        st.divider()
        generate = st.button(t("generate", lang), type="primary", use_container_width=True)
        st.session_state.show_heatmap = st.checkbox("🔥 显示路线热力图", value=st.session_state.show_heatmap)

    st.markdown(
        f"""
        <div class="hero-panel">
            <p class="main-header" style="margin:0;">✈️ {t("title", lang)}</p>
            <p class="hero-subtitle">{t("subtitle", lang)}</p>
            <span class="mode-badge">{t("mock_mode", lang) if USE_MOCK else t("api_mode", lang)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if generate:
        st.session_state.generating = True
        placeholder = st.empty()
        with placeholder.container():
            if st_lottie:
                anim = _lottie(LOTTIE_URL)
                if anim:
                    st_lottie(anim, height=120, key="loading_lottie")
            run_agent_progress()
            render_skeleton()
        response = fetch_plan(request)
        placeholder.empty()
        st.session_state.generating = False
        if response.get("success"):
            prev = st.session_state.plan
            st.session_state.plan_response = response
            st.session_state.plan = response["plan"]
            st.session_state.session_id = response.get("session_id", "")
            if prev:
                hist = st.session_state.plan_history
                if not hist or hist[-1] != prev:
                    hist.append(prev)
            st.session_state.plan_history.append(response["plan"])
            st.toast("行程生成成功！", icon="✅")
            st.balloons()
        else:
            st.error(response.get("error", "生成失败，已保留 Mock 数据。"))

    plan = st.session_state.plan
    tabs = st.tabs([
        t("tab_itinerary", lang), t("tab_map", lang),
        t("tab_chat", lang), t("tab_budget", lang), "📥 导出", "⚖️ 对比",
    ])

    with tabs[0]:
        if plan:
            render_summary_metrics(plan)
            st.divider()
            render_timeline(plan)
            st.subheader("🏛️ 景点卡片")
            render_card_wall(plan)
            tips = plan.get("tips", [])
            if tips:
                st.subheader("💡 旅行贴士")
                for tip in tips:
                    st.info(tip)
        else:
            render_empty_state(t("empty_hint", lang))

    with tabs[1]:
        if plan:
            render_map(plan, show_heatmap=st.session_state.show_heatmap)
        else:
            render_empty_state("请先生成行程。")

    with tabs[2]:
        render_chat_box(plan, st.session_state.session_id)

    with tabs[3]:
        if plan:
            render_budget_pie(plan)
        else:
            render_empty_state("请先生成行程。")

    with tabs[4]:
        if plan:
            render_export_panel(plan)
        else:
            st.info("请先生成行程后再导出。")

    with tabs[5]:
        hist = st.session_state.plan_history
        plan_b = hist[-2] if len(hist) >= 2 else None
        render_trip_compare(plan, plan_b)


if __name__ == "__main__":
    main()
