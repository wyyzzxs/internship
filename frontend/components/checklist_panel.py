"""Checklist UI component."""

from __future__ import annotations

import streamlit as st


def render_checklist_panel(markdown_text: str) -> None:
    if not markdown_text:
        st.info("暂无清单内容")
        return
    st.markdown(markdown_text)

