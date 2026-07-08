"""输入表单 — P0-1 UI + P0-8 演示 + 主题/语言。"""

from __future__ import annotations

from datetime import date

import streamlit as st

from themes import THEMES
from utils.data_loader import get_city_names, get_crowd_types, get_preference_tags
from utils.i18n import t
from utils.mock_data import DEMO_PRESETS


def render_input_form(lang: str = "zh") -> dict:
    st.header(t("travel_needs", lang))
    st.subheader(t("demo_mode", lang))

    demo_key = st.selectbox(
        "一键加载预设",
        ["（手动输入）"] + list(DEMO_PRESETS.keys()),
        key="demo_preset",
    )
    if demo_key != "（手动输入）":
        if st.button("加载演示数据", type="primary", use_container_width=True):
            preset = DEMO_PRESETS[demo_key]
            st.session_state.plan_response = preset
            st.session_state.plan = preset["plan"]
            st.session_state.session_id = preset.get("session_id", "")
            if st.session_state.get("plan_history"):
                st.session_state.plan_history.append(preset["plan"])
            else:
                st.session_state.plan_history = [preset["plan"]]
            st.toast(f"已加载：{demo_key}", icon="✅")
            st.rerun()

    st.divider()
    st.subheader("🎨 主题 & 语言")
    theme_keys = list(THEMES.keys())
    theme_labels = [THEMES[k]["label"] for k in theme_keys]
    current_theme = st.session_state.get("theme", "travel_night")
    idx = theme_keys.index(current_theme) if current_theme in theme_keys else 0
    chosen = st.selectbox("界面主题", theme_labels, index=idx)
    st.session_state.theme = theme_keys[theme_labels.index(chosen)]
    st.session_state.lang = st.selectbox("语言 / Language", ["zh", "en"],
                                         index=0 if lang == "zh" else 1,
                                         format_func=lambda x: "中文" if x == "zh" else "English")

    st.divider()
    city = st.selectbox("目的地", get_city_names(), index=0)
    days = st.slider("出行天数", 1, 7, 3)
    start_date = st.date_input("出发日期", value=date.today())
    budget = st.number_input("预算（元）", min_value=100, max_value=50000, value=1500, step=100)
    preferences = st.multiselect("旅行偏好", get_preference_tags(), default=["历史文化", "美食探店"])
    people = st.selectbox("同行人群", get_crowd_types(), index=0)
    departure = st.text_input("出发地", value="武汉")
    special = st.text_area("特殊要求（可选）", placeholder="例：不想走太多路、带老人")

    return {
        "city": city,
        "days": days,
        "start_date": start_date.isoformat(),
        "budget": budget,
        "preferences": preferences,
        "people": people,
        "departure": departure,
        "special": special or None,
    }
