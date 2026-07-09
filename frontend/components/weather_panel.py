"""Weather forecast UI component."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render_weather_panel(weather_payload: dict[str, Any]) -> None:
    forecast = weather_payload.get("forecast", [])
    summary = weather_payload.get("summary", {})
    if not forecast:
        st.info("暂无天气数据")
        return

    cols = st.columns(len(forecast))
    for col, item in zip(cols, forecast):
        with col:
            st.metric(
                label=f"{item['date']} 周{item['weekday']}",
                value=f"{item['temp_low']}°C - {item['temp_high']}°C",
                delta=item["weather"],
            )
            if item.get("rain_risk"):
                st.warning("雨天备选")

    frame = pd.DataFrame(forecast)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=frame["date"],
            y=frame["temp_high"],
            mode="lines+markers",
            name="最高温",
            line={"color": "#ef4444", "width": 3},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=frame["date"],
            y=frame["temp_low"],
            mode="lines+markers",
            name="最低温",
            line={"color": "#2563eb", "width": 3},
        )
    )
    fig.update_layout(
        height=280,
        margin={"l": 20, "r": 20, "t": 30, "b": 20},
        legend={"orientation": "h", "y": 1.15},
    )
    st.plotly_chart(fig, use_container_width=True)

    st.info(summary.get("overall_advice", "天气数据已加载"))
    for item in forecast:
        st.caption(f"{item['date']} {item['weather']}：{item['advice']}")

