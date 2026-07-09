"""Flask 前端辅助 — 复用 frontend/utils 逻辑。"""

from __future__ import annotations

import json
import math
import os
import re
from copy import deepcopy
from io import BytesIO
from urllib.parse import quote

from utils.data_loader import (
    enrich_plan,
    get_city_names,
    get_crowd_types,
    get_heatmap_hotspots,
    get_preference_tags,
    image_to_base64,
    load_cities,
    lookup_attraction,
)
from utils.mock_chat import get_mock_chat_response
from utils.mock_data import DEMO_PRESETS, get_mock_plan

TYPE_COLORS = {
    "景点": "#4cc9f0",
    "餐饮": "#ffd166",
    "交通": "#94a3b8",
    "住宿": "#c084fc",
    "其他": "#06d6a0",
}

CATEGORY_COLOR = {
    "交通": "#4cc9f0",
    "住宿": "#ff6b4a",
    "门票": "#94a3b8",
    "餐饮": "#ffd166",
    "其他": "#06d6a0",
}


def use_mock() -> bool:
    return os.getenv("USE_MOCK", "true").lower() == "true"


def backend_url() -> str:
    return os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")


def fetch_plan_api(request: dict) -> dict:
    if use_mock():
        resp = get_mock_plan(**request)
        resp["plan"] = enrich_plan(resp["plan"])
        return resp
    from utils.api_client import fetch_plan
    return fetch_plan(request)


def chat_api(session_id: str, message: str, plan: dict | None) -> dict:
    if use_mock():
        return get_mock_chat_response(message, plan)
    from utils.api_client import fetch_chat
    return fetch_chat(session_id, message, plan)


def load_preset(key: str) -> dict | None:
    preset = DEMO_PRESETS.get(key)
    if not preset:
        return None
    return deepcopy(preset)


def _as_float(value) -> float | None:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(num):
        return None
    return num


def collect_attractions(plan: dict) -> list[dict]:
    seen: set[str] = set()
    city = plan.get("trip_summary", {}).get("city")
    result = []
    for day in plan.get("days", []):
        for item in day.get("items", []):
            if item.get("type") != "景点":
                continue
            name = item.get("name", "")
            if name in seen:
                continue
            seen.add(name)
            att = lookup_attraction(name, city)
            row = dict(item)
            if att:
                for k in ("rating", "tags", "open_hours", "photo_spots", "image_path", "description"):
                    if att.get(k):
                        row.setdefault(k, att[k])
            row["image_b64"] = image_to_base64(row.get("image_path"))
            result.append(row)
    return result


def collect_map_points(plan: dict) -> list[dict]:
    points = []
    seen: set[tuple[float, float, str]] = set()
    for day in plan.get("days", []):
        for item in day.get("items", []):
            lat, lng = _as_float(item.get("lat")), _as_float(item.get("lng"))
            if lat is None or lng is None:
                continue
            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                continue
            key = (round(lat, 5), round(lng, 5), item.get("name", ""))
            if key in seen:
                continue
            seen.add(key)
            points.append({
                "name": item.get("name", ""),
                "lat": lat,
                "lng": lng,
                "cost": item.get("cost", 0),
                "time": item.get("time", ""),
                "description": item.get("description", ""),
                "emoji": item.get("emoji", ""),
            })
    return points


def get_city_center(plan: dict) -> list[float]:
    city = plan.get("trip_summary", {}).get("city", "武汉")
    for c in load_cities():
        if c["name"] == city:
            lng, lat = _as_float(c.get("lng")), _as_float(c.get("lat"))
            if lng is not None and lat is not None:
                return [lng, lat]
    points = collect_map_points(plan)
    if points:
        return [points[0]["lng"], points[0]["lat"]]
    return [114.3055, 30.5928]


def get_heatmap_data(city: str) -> list[dict]:
    result = []
    for h in get_heatmap_hotspots(city):
        lng, lat = _as_float(h.get("lng")), _as_float(h.get("lat"))
        if lng is None or lat is None:
            continue
        density = _as_float(h.get("density")) or 50
        result.append({"lng": lng, "lat": lat, "count": density})
    return result


def weather_for_day(plan: dict, day_date: str) -> dict | None:
    for w in plan.get("weather", []):
        if w.get("date") == day_date:
            return w
    return None


def plan_stats(plan: dict) -> dict:
    bd = plan.get("budget_breakdown", {})
    spent = sum(bd.values()) if bd else 0
    attractions = sum(
        1 for d in plan.get("days", []) for i in d.get("items", []) if i.get("type") == "景点"
    )
    summary = plan.get("trip_summary", {})
    return {
        "city": summary.get("city", ""),
        "days": summary.get("days", 0),
        "spent": spent,
        "budget": summary.get("total_budget", 0),
        "attractions": attractions,
        "start_date": summary.get("start_date", ""),
        "end_date": summary.get("end_date", ""),
    }


def plan_to_markdown(plan: dict) -> str:
    s = plan.get("trip_summary", {})
    lines = [
        f"# {s.get('city', '')} {s.get('days', '')} 日游攻略",
        "",
        f"- **日期**: {s.get('start_date', '')} ~ {s.get('end_date', '')}",
        f"- **预算**: ¥{s.get('total_budget', 0)}",
        f"- **同行**: {s.get('people', '')}",
        "",
    ]
    for day in plan.get("days", []):
        w = weather_for_day(plan, day.get("date", ""))
        header = f"## Day {day.get('day')} ({day.get('date')})"
        if w:
            header += f" · {w.get('weather', '')} {w.get('temp_low')}–{w.get('temp_high')}°C"
        lines.append(header)
        lines.append("")
        for item in day.get("items", []):
            cost = "免费" if item.get("cost", 0) == 0 else f"¥{item['cost']}"
            lines.append(
                f"- **{item.get('time', '')}** [{item.get('type', '')}] "
                f"{item.get('name', '')} ({cost}) — {item.get('description', '')}"
            )
        lines.append(f"- 当日花费: ¥{day.get('day_cost', 0)}")
        lines.append("")
    bd = plan.get("budget_breakdown", {})
    if bd:
        lines.append("## 预算明细")
        for k, v in bd.items():
            lines.append(f"- {k}: ¥{v}")
    tips = plan.get("tips", [])
    if tips:
        lines.append("")
        lines.append("## 贴士")
        for tip in tips:
            lines.append(f"- {tip}")
    return "\n".join(lines)


def plan_to_json(plan: dict) -> str:
    return json.dumps(plan, ensure_ascii=False, indent=2)


def plan_to_pdf_bytes(plan: dict) -> bytes | None:
    md = plan_to_markdown(plan)
    try:
        from markdown_pdf import MarkdownPdf, Section

        pdf = MarkdownPdf()
        pdf.add_section(Section(md))
        buf = BytesIO()
        pdf.save(buf)
        return buf.getvalue()
    except Exception:
        return None


def compare_plans(plan_a: dict | None, plan_b: dict | None) -> dict | None:
    if not plan_a or not plan_b:
        return None
    sa, sb = plan_stats(plan_a), plan_stats(plan_b)
    diff = sa["spent"] - sb["spent"]
    if diff > 0:
        message = f"方案 B 比方案 A 省 ¥{diff}"
        winner = "b"
    elif diff < 0:
        message = f"方案 A 比方案 B 省 ¥{-diff}"
        winner = "a"
    else:
        message = "两方案花费相同"
        winner = "tie"
    return {"a": sa, "b": sb, "diff": diff, "message": message, "winner": winner}


def fetch_checklist(plan: dict, people_type: str) -> str:
    weather = plan.get("weather", [])
    weather_payload = {"forecast": weather} if weather else {}
    people_type = normalize_people_for_api(people_type)

    def _local_checklist() -> str:
        lines = ["# 出行清单", "", f"**同行**: {people_type}", ""]
        if weather:
            lines.append("## 天气提醒")
            for w in weather[:5]:
                lines.append(
                    f"- {w.get('date', '')}: {w.get('weather', '')} "
                    f"{w.get('temp_low', '')}–{w.get('temp_high', '')}°C · {w.get('suggestion', '')}"
                )
        lines.extend(["", "## 必备物品", "- 身份证 / 充电宝", "- 舒适步行鞋", "- 雨伞或防晒（视天气）"])
        if plan.get("tips"):
            lines.extend(["", "## 行程贴士"])
            lines.extend(f"- {tip}" for tip in plan.get("tips", [])[:5])
        return "\n".join(lines)

    if use_mock():
        return _local_checklist()
    import requests

    url = backend_url() + "/api/checklist"
    try:
        resp = requests.post(
            url,
            json={"plan": plan, "weather": weather_payload, "people_type": people_type},
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json().get("content", "")
        return content or _local_checklist()
    except Exception:
        return _local_checklist()


def check_backend_status() -> dict:
    status = {
        "backend_url": backend_url(),
        "use_mock": use_mock(),
        "health": False,
        "plan_api": False,
        "chat_api": False,
        "weather_api": False,
        "checklist_api": False,
    }
    if use_mock():
        status["health"] = True
        return status
    import requests

    base = backend_url()
    try:
        r = requests.get(f"{base}/api/health", timeout=3)
        status["health"] = r.status_code == 200
    except Exception:
        pass
    for key, path, method in [
        ("plan_api", "/api/plan", "POST"),
        ("chat_api", "/api/chat", "POST"),
        ("weather_api", "/api/weather?city=武汉&days=1", "GET"),
        ("checklist_api", "/api/checklist", "POST"),
    ]:
        try:
            if method == "GET":
                r = requests.get(f"{base}{path}", timeout=3)
            elif path == "/api/checklist":
                r = requests.post(f"{base}{path}", json={"plan": {}, "people_type": "朋友"}, timeout=3)
            else:
                r = requests.post(f"{base}{path}", json={}, timeout=3)
            status[key] = r.status_code != 404
        except Exception:
            status[key] = False
    return status


def form_context() -> dict:
    return {
        "cities": get_city_names(),
        "crowd_types": get_crowd_types(),
        "preference_tags": get_preference_tags(),
        "presets": list(DEMO_PRESETS.keys()),
        "use_mock": use_mock(),
    }


PEOPLE_REVERSE = {
    "情侣": "情侣出游",
    "亲子": "亲子家庭",
    "独自": "独自旅行",
    "朋友": "朋友结伴",
    "商务": "爸妈长辈",
}

PEOPLE_TO_BACKEND = {
    "情侣出游": "情侣",
    "亲子家庭": "亲子",
    "独自旅行": "独自",
    "朋友结伴": "朋友",
    "爸妈长辈": "朋友",
}


def export_filename(city: str, suffix: str) -> tuple[str, dict]:
    """生成兼容 Windows 的下载文件名（ASCII 兜底 + UTF-8 中文名）。"""
    slug = re.sub(r"[^a-zA-Z0-9\-]+", "_", city or "travel").strip("_") or "travel"
    ascii_name = f"{slug}_{suffix}"
    utf8_name = f"{city or 'travel'}_{suffix}"
    disposition = f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(utf8_name)}"
    return ascii_name, {"Content-Disposition": disposition}


def normalize_people_for_api(people: str) -> str:
    return PEOPLE_TO_BACKEND.get(people, people)


def default_form() -> dict:
    from datetime import date

    return {
        "city": "武汉",
        "days": 3,
        "start_date": date.today().isoformat(),
        "budget": 1500,
        "people": "情侣出游",
        "departure": "武汉",
        "preferences": ["历史文化", "美食探店"],
        "special": "",
    }


def form_from_plan(plan: dict) -> dict:
    from datetime import date

    s = plan.get("trip_summary", {})
    people = s.get("people", "情侣")
    return {
        "city": s.get("city", "武汉"),
        "days": s.get("days", 3),
        "start_date": s.get("start_date") or date.today().isoformat(),
        "budget": int(s.get("total_budget", 1500)),
        "people": PEOPLE_REVERSE.get(people, people if people in get_crowd_types() else "情侣出游"),
        "departure": "武汉",
        "preferences": ["历史文化", "美食探店"],
        "special": "",
    }


def resolve_form(session: dict, plan: dict | None) -> dict:
    stored = session.get("last_form")
    if stored:
        merged = default_form()
        merged.update(stored)
        if not merged.get("start_date"):
            merged["start_date"] = default_form()["start_date"]
        return merged
    if plan:
        return form_from_plan(plan)
    return default_form()


def form_stale(form: dict, plan: dict | None) -> bool:
    if not plan:
        return False
    s = plan.get("trip_summary", {})
    try:
        if int(form.get("days", 0)) != int(s.get("days", 0)):
            return True
        if form.get("city") != s.get("city"):
            return True
        if int(form.get("budget", 0)) != int(s.get("total_budget", 0)):
            return True
        if form.get("start_date") and s.get("start_date") and form.get("start_date") != s.get("start_date"):
            return True
    except (TypeError, ValueError):
        pass
    return False
