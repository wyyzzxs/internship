"""行程概览 metrics — overview.html stat-card 风格。"""

from __future__ import annotations

import streamlit as st


def render_summary_metrics(plan: dict) -> None:
    summary = plan.get("trip_summary", {})
    breakdown = plan.get("budget_breakdown", {})
    total_spent = sum(breakdown.values()) if breakdown else 0
    total_budget = summary.get("total_budget", 0)

    attraction_count = sum(
        1
        for day in plan.get("days", [])
        for item in day.get("items", [])
        if item.get("type") == "景点"
    )

    st.markdown(
        f"""
        <div style="color:var(--muted);font-size:0.95rem;margin-bottom:16px;text-align:center;">
            <b style="color:var(--text);">{summary.get('city', '')}</b>
            · {summary.get('start_date', '')} 至 {summary.get('end_date', '')}
            · {summary.get('people', '')}
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    cards = [
        ("📅", "出行天数", f"{summary.get('days', 0)} 天"),
        ("🏛️", "精选景点", f"{attraction_count} 个"),
        ("💰", "预计花费", f"¥{total_spent}"),
        ("🎯", "预算上限", f"¥{total_budget}"),
    ]
    cols = [c1, c2, c3, c4]
    for col, (icon, label, value) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="trip-metric-box">
                    <div class="trip-metric-icon">{icon}</div>
                    <div class="trip-metric-value">{value}</div>
                    <div class="trip-metric-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if total_budget and total_spent > total_budget:
        st.markdown(
            f'<p style="color:#ff6b6b;text-align:center;margin-top:8px;">'
            f"⚠️ 预计超支 ¥{total_spent - total_budget}</p>",
            unsafe_allow_html=True,
        )
