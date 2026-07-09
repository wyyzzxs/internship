"""行程概览 metrics — overview stat-card 风格。"""

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
        <div style="color:var(--muted);font-size:0.92rem;margin-bottom:18px;text-align:center;letter-spacing:0.02em;">
            <b style="color:var(--text);font-weight:600;">{summary.get('city', '')}</b>
            &nbsp;·&nbsp; {summary.get('start_date', '')} — {summary.get('end_date', '')}
            &nbsp;·&nbsp; {summary.get('people', '')}
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    cards = [
        ("Days", "出行天数", f"{summary.get('days', 0)}"),
        ("Spots", "精选景点", f"{attraction_count}"),
        ("Cost", "预计花费", f"¥{total_spent}"),
        ("Budget", "预算上限", f"¥{total_budget}"),
    ]
    cols = [c1, c2, c3, c4]
    for col, (_tag, label, value) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="trip-metric-box">
                    <div class="trip-metric-label">{label}</div>
                    <div class="trip-metric-value">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if total_budget and total_spent > total_budget:
        st.markdown(
            f'<p class="budget-alert budget-alert-warn" style="margin-top:12px;">'
            f"预计超支 ¥{total_spent - total_budget}</p>",
            unsafe_allow_html=True,
        )
