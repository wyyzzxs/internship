"""景点卡片墙 — P0-4 真实图片 + 3D 翻转 + 机位信息。"""

from __future__ import annotations

import html

import streamlit as st
import streamlit.components.v1 as components

from themes import THEMES
from utils.data_loader import enrich_plan, image_to_base64, lookup_attraction


def _card_page_css(theme_key: str) -> str:
    t = THEMES.get(theme_key, THEMES["travel_night"])
    return f"""
body {{ margin: 0; padding: 8px; font-family: 'Noto Sans SC', 'Segoe UI', sans-serif;
       background: transparent; color: {t['text']}; }}
.card-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 18px; }}
.flip-card {{ perspective: 1000px; height: 300px; }}
.flip-card-inner {{ position: relative; width: 100%; height: 100%; transition: transform 0.6s;
    transform-style: preserve-3d; cursor: pointer; }}
.flip-card:hover .flip-card-inner {{ transform: rotateY(180deg); }}
.flip-card-front, .flip-card-back {{
    position: absolute; width: 100%; height: 100%; backface-visibility: hidden;
    border-radius: 14px; overflow: hidden; box-sizing: border-box;
    border: 1px solid {t['border']};
    box-shadow: 0 8px 28px rgba(0,0,0,0.35);
}}
.flip-card-front {{ color: white; display: flex; flex-direction: column; justify-content: flex-end; }}
.flip-card-front.has-img {{ background-size: cover; background-position: center; }}
.flip-card-front.no-img {{
    background: linear-gradient(135deg, {t['accent']}, {t['accent3']});
    justify-content: center; align-items: center; text-align: center;
}}
.front-overlay {{
    background: linear-gradient(transparent 25%, rgba(11,16,32,0.88));
    padding: 18px; width: 100%; box-sizing: border-box;
}}
.flip-card-back {{
    background: {t['card']}; color: {t['text']};
    transform: rotateY(180deg); overflow-y: auto; font-size: 13px;
    padding: 18px; line-height: 1.6; backdrop-filter: blur(12px);
}}
.card-emoji {{ font-size: 48px; margin-bottom: 8px; filter: drop-shadow(0 2px 8px rgba(0,0,0,0.4)); }}
.card-name {{ font-size: 18px; font-weight: 700; text-shadow: 0 2px 8px rgba(0,0,0,0.5); }}
.card-meta {{ font-size: 13px; opacity: 0.92; margin-top: 6px; }}
.card-tag {{
    display: inline-block; background: {t['accent']}22; color: {t['accent2']};
    border: 1px solid {t['border']}; border-radius: 6px;
    padding: 3px 10px; margin: 3px; font-size: 11px;
}}
.spot-item {{
    font-size: 12px; margin: 6px 0; padding: 8px 10px;
    background: rgba(255,255,255,0.05); border-left: 3px solid {t['accent3']};
    border-radius: 0 6px 6px 0; color: {t['muted']};
}}
.hint {{ color: {t['muted']}; font-size: 12px; margin-top: 16px; text-align: center; }}
"""


CARD_PAGE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>__CSS__</style>
</head>
<body>
<div class="card-grid">__CARDS__</div>
<p class="hint">悬停卡片可翻转 · 背面含拍照机位推荐</p>
</body>
</html>
"""


def _collect_attractions(plan: dict) -> list[dict]:
    seen: set[str] = set()
    result: list[dict] = []
    city = plan.get("trip_summary", {}).get("city")
    for day in plan.get("days", []):
        for item in day.get("items", []):
            if item.get("type") != "景点":
                continue
            name = item.get("name", "")
            if name in seen:
                continue
            seen.add(name)
            att = lookup_attraction(name, city)
            if att:
                item = {**item, **{k: att.get(k) for k in ("rating", "tags", "open_hours", "photo_spots", "image_path") if att.get(k)}}
            result.append(item)
    return result


def _esc(text: str) -> str:
    return html.escape(str(text))


def _build_card(a: dict) -> str:
    cost = a.get("cost", 0)
    cost_str = "免费" if cost == 0 else f"¥{cost}"
    tags_html = "".join(f'<span class="card-tag">{_esc(t)}</span>' for t in a.get("tags", []))
    hours = a.get("open_hours", "")
    hours_html = f"<br>🕐 {_esc(hours)}" if hours else ""

    spots_html = ""
    for sp in a.get("photo_spots", [])[:2]:
        spots_html += (
            f'<div class="spot-item">📷 {_esc(sp.get("location",""))} · '
            f'{_esc(sp.get("best_time",""))} · {_esc(sp.get("tip",""))}</div>'
        )
    if spots_html:
        spots_html = "<br><b>拍照机位</b><br>" + spots_html

    b64 = image_to_base64(a.get("image_path"))
    if b64:
        front = f"""
        <div class="flip-card-front has-img" style="background-image:url('{b64}');">
            <div class="front-overlay">
                <div class="card-name">{_esc(a.get('name',''))}</div>
                <div class="card-meta">⭐ {a.get('rating',4.5)} · {cost_str} · {a.get('duration_hours',2)}h</div>
            </div>
        </div>"""
    else:
        front = f"""
        <div class="flip-card-front no-img">
            <div class="card-emoji">{_esc(a.get('emoji','📍'))}</div>
            <div class="card-name">{_esc(a.get('name',''))}</div>
            <div class="card-meta">⭐ {a.get('rating',4.5)} · {cost_str} · {a.get('duration_hours',2)}h</div>
        </div>"""

    return f"""
    <div class="flip-card"><div class="flip-card-inner">{front}
        <div class="flip-card-back">
            <strong>{_esc(a.get('name',''))}</strong><br><br>
            {_esc(a.get('description',''))}<br><br>{tags_html}{hours_html}{spots_html}
        </div>
    </div></div>"""


def render_card_wall(plan: dict) -> None:
    plan = enrich_plan(plan)
    attractions = _collect_attractions(plan)
    if not attractions:
        st.info("暂无景点卡片。")
        return

    cards = "".join(_build_card(a) for a in attractions)
    theme_key = st.session_state.get("theme", "travel_night")
    page = CARD_PAGE.replace("__CSS__", _card_page_css(theme_key)).replace("__CARDS__", cards)
    rows = (len(attractions) + 2) // 3
    components.html(page, height=max(340, rows * 320 + 48), scrolling=False)
