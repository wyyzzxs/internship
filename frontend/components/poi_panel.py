"""Nearby POI UI component."""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_poi_panel(poi_payload: dict[str, Any]) -> None:
    items = poi_payload.get("items", [])
    if not items:
        st.info("周边暂无匹配 POI")
        return

    for item in items:
        title = item.get("name", "未命名地点")
        distance = item.get("distance_m")
        rating = item.get("rating")
        with st.container(border=True):
            top = f"**{title}**"
            if distance is not None:
                top += f" · {distance}m"
            if rating:
                top += f" · 评分 {rating}"
            st.markdown(top)
            meta = []
            if item.get("type"):
                meta.append(str(item["type"]))
            if item.get("avg_cost"):
                meta.append(f"参考价 {item['avg_cost']}")
            if item.get("address"):
                meta.append(str(item["address"]))
            st.caption(" | ".join(meta))

