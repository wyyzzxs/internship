"""预算饼图 + 明细 — overview 风格玻璃卡片 + 暗色图表。"""

from __future__ import annotations

import html

import plotly.graph_objects as go
import streamlit as st

from themes import THEMES
from utils.chart_theme import base_layout, theme_palette

CATEGORY_EMOJI = {"交通": "🚄", "住宿": "🏨", "门票": "🎫", "餐饮": "🍜", "其他": "🛍️"}
CATEGORY_COLOR = {
    "交通": "#4cc9f0",
    "住宿": "#ff6b4a",
    "门票": "#94a3b8",
    "餐饮": "#ffd166",
    "其他": "#06d6a0",
}


def _theme_text(theme_key: str) -> str:
    return THEMES.get(theme_key, THEMES["travel_night"])["text"]


def _theme_muted(theme_key: str) -> str:
    return THEMES.get(theme_key, THEMES["travel_night"])["muted"]


def _section_title(text: str) -> None:
    st.markdown(f'<p class="section-title">{html.escape(text)}</p>', unsafe_allow_html=True)


def _budget_table_html(breakdown: dict, total_spent: float) -> str:
    rows = []
    for key, value in breakdown.items():
        pct = round(value / total_spent * 100, 1) if total_spent else 0
        color = CATEGORY_COLOR.get(key, "#ff6b4a")
        emoji = CATEGORY_EMOJI.get(key, "📌")
        bar_w = max(4, int(pct))
        rows.append(
            f"""
            <tr>
                <td><span class="budget-cat"><span class="budget-dot" style="background:{color};"></span>
                    {emoji} {html.escape(key)}</span></td>
                <td class="budget-amt">¥{value}</td>
                <td class="budget-pct">{pct}%</td>
                <td class="budget-bar-cell">
                    <div class="budget-bar-track"><div class="budget-bar-fill"
                         style="width:{bar_w}%;background:linear-gradient(90deg,{color},{color}88);"></div></div>
                </td>
            </tr>"""
        )
    return f"""
    <div class="glass-table-wrap">
        <table class="glass-table">
            <thead>
                <tr><th>类别</th><th>金额</th><th>占比</th><th>分布</th></tr>
            </thead>
            <tbody>{"".join(rows)}</tbody>
        </table>
    </div>"""


def _pie_figure(labels: list[str], values: list[float], theme_key: str) -> go.Figure:
    colors = theme_palette(theme_key)
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.52,
            marker=dict(
                colors=[colors[i % len(colors)] for i in range(len(labels))],
                line=dict(color="rgba(11, 16, 32, 0.9)", width=2),
            ),
            textinfo="percent",
            textposition="inside",
            textfont=dict(color="#ffffff", size=13, family="Noto Sans SC, sans-serif"),
            hovertemplate="<b>%{label}</b><br>¥%{value}<br>%{percent}<extra></extra>",
            pull=[0.03] * len(labels),
        )
    )
    layout = base_layout(theme_key, "预算分配", height=400)
    layout["showlegend"] = True
    layout["legend"].update(orientation="v", yanchor="middle", y=0.5, x=1.02)
    fig.update_layout(**layout)
    return fig


def _bar_figure(plan: dict, theme_key: str) -> go.Figure | None:
    daily_labels = [f"Day {d.get('day', '?')}" for d in plan.get("days", [])]
    daily_costs = [d.get("day_cost", 0) for d in plan.get("days", [])]
    if not daily_costs:
        return None

    colors = theme_palette(theme_key)
    fig = go.Figure(
        go.Bar(
            x=daily_labels,
            y=daily_costs,
            marker=dict(
                color=[colors[i % len(colors)] for i in range(len(daily_costs))],
                line=dict(color="rgba(255,255,255,0.15)", width=1),
                cornerradius=8,
            ),
            text=[f"¥{c}" for c in daily_costs],
            textposition="outside",
            textfont=dict(color=_theme_text(theme_key), size=13),
            hovertemplate="<b>%{x}</b><br>¥%{y}<extra></extra>",
        )
    )
    layout = base_layout(theme_key, "每日花费对比", height=400)
    layout["yaxis"]["title"] = dict(text="元", font=dict(color=_theme_muted(theme_key)))
    fig.update_layout(**layout)
    return fig


def render_budget_pie(plan: dict) -> None:
    breakdown = plan.get("budget_breakdown", {})
    summary = plan.get("trip_summary", {})
    total_budget = summary.get("total_budget", 0)
    theme_key = st.session_state.get("theme", "travel_night")

    if not breakdown:
        st.info("暂无预算数据。")
        return

    total_spent = sum(breakdown.values())
    over_ratio = total_spent / total_budget if total_budget else 0

    hc1, hc2, hc3 = st.columns(3)
    with hc1:
        st.markdown(
            f'<div class="trip-metric-box"><div class="trip-metric-value">¥{total_spent}</div>'
            f'<div class="trip-metric-label">预计总花费</div></div>',
            unsafe_allow_html=True,
        )
    with hc2:
        st.markdown(
            f'<div class="trip-metric-box"><div class="trip-metric-value">¥{total_budget}</div>'
            f'<div class="trip-metric-label">预算上限</div></div>',
            unsafe_allow_html=True,
        )
    with hc3:
        pct = f"{over_ratio * 100:.0f}%"
        st.markdown(
            f'<div class="trip-metric-box"><div class="trip-metric-value">{pct}</div>'
            f'<div class="trip-metric-label">预算使用率</div></div>',
            unsafe_allow_html=True,
        )

    if total_budget and total_spent > total_budget:
        st.markdown(
            f'<div class="budget-alert budget-alert-warn">⚠️ 超支 ¥{total_spent - total_budget}'
            f'（预算 ¥{total_budget}，预计 ¥{total_spent}）</div>',
            unsafe_allow_html=True,
        )
    elif total_budget:
        st.markdown(
            f'<div class="budget-alert budget-alert-ok">✅ 预算充足，剩余 ¥{total_budget - total_spent}</div>',
            unsafe_allow_html=True,
        )

    labels = [f"{CATEGORY_EMOJI.get(k, '📌')} {k}" for k in breakdown]
    values = list(breakdown.values())

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            _pie_figure(labels, values, theme_key),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    with col2:
        fig_bar = _bar_figure(plan, theme_key)
        if fig_bar:
            st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

    _section_title("💰 预算明细")
    st.markdown(_budget_table_html(breakdown, total_spent), unsafe_allow_html=True)
