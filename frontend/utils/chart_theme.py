"""Plotly 图表暗色主题 — 对齐 overview.html 玻璃卡片风格。"""

from __future__ import annotations

from themes import THEMES

CHART_COLORS = ["#ff6b4a", "#ffd166", "#4cc9f0", "#06d6a0", "#94a3b8", "#c084fc"]


def theme_palette(theme_key: str) -> list[str]:
    t = THEMES.get(theme_key, THEMES["travel_night"])
    return [t["accent"], t["accent2"], t["accent3"], "#06d6a0", t["muted"], "#c084fc"]


def base_layout(theme_key: str, title: str, *, height: int = 380) -> dict:
    t = THEMES.get(theme_key, THEMES["travel_night"])
    axis = dict(
        showgrid=True,
        gridcolor=f"{t['border']}",
        zeroline=False,
        linecolor=t["border"],
        tickfont=dict(color=t["muted"], size=12),
        titlefont=dict(color=t["muted"], size=12),
    )
    return dict(
        title=dict(
            text=title,
            x=0.5,
            xanchor="center",
            font=dict(color=t["text"], size=17, family="Noto Sans SC, sans-serif"),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=t["text"], family="Noto Sans SC, sans-serif"),
        margin=dict(t=56, b=36, l=48, r=24),
        height=height,
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
            font=dict(color=t["text"], size=12),
        ),
        xaxis={**axis, "title": dict(text="", font=dict(color=t["muted"]))},
        yaxis={**axis, "title": dict(text="", font=dict(color=t["muted"]))},
        hoverlabel=dict(
            bgcolor=t["card"],
            bordercolor=t["border"],
            font=dict(color=t["text"], family="Noto Sans SC, sans-serif"),
        ),
    )
