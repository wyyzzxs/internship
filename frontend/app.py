"""Standalone Streamlit demo for member B features."""

from __future__ import annotations

from datetime import date

import streamlit as st

from frontend.components.checklist_panel import render_checklist_panel
from frontend.components.poi_panel import render_poi_panel
from frontend.components.weather_panel import render_weather_panel
from frontend.utils.api_client import generate_checklist, get_nearby_poi, get_weather


CITY_COORDS = {
    "武汉": {"lat": 30.5438, "lng": 114.3055, "spot": "黄鹤楼"},
    "西安": {"lat": 34.3840, "lng": 109.2780, "spot": "秦始皇帝陵博物院"},
    "成都": {"lat": 30.7390, "lng": 104.1500, "spot": "成都大熊猫繁育研究基地"},
    "北京": {"lat": 39.9163, "lng": 116.3972, "spot": "故宫博物院"},
    "杭州": {"lat": 30.2428, "lng": 120.1502, "spot": "西湖"},
    "厦门": {"lat": 24.4473, "lng": 118.0670, "spot": "鼓浪屿"},
}


st.set_page_config(page_title="AI 智能旅游规划师", layout="wide")
st.title("AI 智能旅游规划师")

with st.sidebar:
    city = st.selectbox("目的地", list(CITY_COORDS))
    days = st.slider("出行天数", 1, 7, 3)
    start_date = st.date_input("出发日期", value=date.today())
    people_type = st.selectbox("同行人群", ["朋友", "独自", "情侣", "亲子", "商务"])
    poi_type = st.radio(
        "周边类型",
        options=["restaurant", "hotel", "attraction", "toilet"],
        index=0,
        horizontal=True,
    )
    radius_m = st.slider("周边范围", 300, 3000, 1000, step=100)

coord = CITY_COORDS[city]

try:
    weather_payload = get_weather(city, start_date.isoformat(), days)
except Exception as exc:
    st.error(f"天气接口调用失败：{exc}")
    st.stop()

tab_weather, tab_poi, tab_checklist = st.tabs(["天气", "周边", "清单"])

with tab_weather:
    render_weather_panel(weather_payload)

with tab_poi:
    st.caption(f"中心点：{coord['spot']}")
    try:
        poi_payload = get_nearby_poi(
            lat=coord["lat"],
            lng=coord["lng"],
            city=city,
            poi_type=poi_type,
            radius_m=radius_m,
        )
        render_poi_panel(poi_payload)
    except Exception as exc:
        st.error(f"周边 POI 接口调用失败：{exc}")

with tab_checklist:
    demo_plan = {
        "itinerary": [
            {"items": [{"name": coord["spot"]}, {"name": "城市美食街"}, {"name": "夜景散步"}]}
        ]
    }
    try:
        checklist = generate_checklist(demo_plan, weather_payload, people_type)
        render_checklist_panel(checklist)
    except Exception as exc:
        st.error(f"清单接口调用失败：{exc}")
