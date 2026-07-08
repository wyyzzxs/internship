"""行程时间轴 — P0-3 竖排 + 类型配色 + 日卡片。"""

from __future__ import annotations

import streamlit as st

WEATHER_EMOJI = {"晴": "☀️", "多云": "⛅", "小雨": "🌧️", "阴": "☁️", "雪": "❄️"}
TYPE_STYLE = {
    "景点": {"color": "var(--accent3)", "bg": "rgba(76, 201, 240, 0.12)", "icon": "🏛️"},
    "餐饮": {"color": "var(--accent2)", "bg": "rgba(255, 209, 102, 0.12)", "icon": "🍜"},
    "交通": {"color": "var(--muted)", "bg": "rgba(148, 163, 184, 0.1)", "icon": "🚄"},
}


def _weather_for_day(plan: dict, day_date: str) -> dict | None:
    for w in plan.get("weather", []):
        if w.get("date") == day_date:
            return w
    return None


def render_timeline(plan: dict) -> None:
    days = plan.get("days", [])
    if not days:
        st.info("暂无行程数据，请点击「生成行程」。")
        return

    for day_data in days:
        day_num = day_data.get("day", 1)
        day_date = day_data.get("date", "")
        weekday = day_data.get("weekday", "")
        day_cost = day_data.get("day_cost", 0)
        steps = day_data.get("steps", 0)
        weather = _weather_for_day(plan, day_date)
        weather_str = ""
        if weather:
            emoji = WEATHER_EMOJI.get(weather.get("weather", ""), "🌡️")
            weather_str = f"{emoji} {weather['weather']} {weather.get('temp_low')}~{weather.get('temp_high')}°C"

        st.markdown(
            f'<div class="day-card"><h3 style="margin-top:0;color:var(--text);">📅 Day {day_num}'
            f' <span style="font-size:0.85rem;font-weight:normal;color:var(--muted);">'
            f'{day_date} · {weekday}</span></h3>',
            unsafe_allow_html=True,
        )
        if weather_str:
            st.caption(weather_str)

        for item in day_data.get("items", []):
            t = item.get("type", "景点")
            style = TYPE_STYLE.get(t, TYPE_STYLE["景点"])
            cost = item.get("cost", 0)
            cost_str = "免费" if cost == 0 else f"¥{cost}"
            end = item.get("end_time", "")
            time_str = item.get("time", "")
            if end:
                time_str += f" – {end}"

            st.markdown(
                f"""
                <div style="display:flex;gap:12px;margin:10px 0;padding:10px 12px;
                     border-radius:8px;background:{style['bg']};border-left:3px solid {style['color']};">
                    <div style="min-width:90px;font-weight:600;color:{style['color']};">{time_str}</div>
                    <div style="flex:1;color:var(--text);">
                        <div style="font-weight:600;">{item.get('emoji','📍')} {item.get('name','')} · {cost_str}</div>
                        <div style="font-size:0.85rem;color:var(--muted);margin-top:4px;">{item.get('description','')}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        footer = f"💰 当日 ¥{day_cost}"
        if steps:
            footer += f"  ·  🚶 {steps:,} 步"
        if weather_str:
            footer += f"  ·  {weather_str}"
        st.markdown(f"<p style='color:var(--muted);font-size:0.9rem;'>{footer}</p></div>", unsafe_allow_html=True)
