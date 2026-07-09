"""加载 data/ 静态 JSON，匹配景点图片与详情。"""

from __future__ import annotations

import base64
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data"
IMAGE_DIR = ROOT / "attraction_image"


@lru_cache(maxsize=1)
def load_attractions() -> list[dict]:
    path = DATA_DIR / "attractions.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("attractions", [])


@lru_cache(maxsize=1)
def load_cities() -> list[dict]:
    with open(DATA_DIR / "cities.json", encoding="utf-8") as f:
        return json.load(f).get("cities", [])


@lru_cache(maxsize=1)
def load_tags() -> dict:
    with open(DATA_DIR / "tags.json", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_heatmap() -> dict:
    with open(DATA_DIR / "heatmap_mock.json", encoding="utf-8") as f:
        return json.load(f)


def get_city_names() -> list[str]:
    return [c["name"] for c in load_cities()]


def get_preference_tags() -> list[str]:
    return [t["name"] for t in load_tags().get("preference_tags", [])]


def get_crowd_types() -> list[str]:
    return [t["name"] for t in load_tags().get("crowd_types", [])]


def _name_keys(name: str) -> list[str]:
    keys = [name.strip()]
    for sep in ("（", "(", " + ", "＋"):
        if sep in name:
            keys.append(name.split(sep)[0].strip())
    return keys


def lookup_attraction(name: str, city: str | None = None) -> dict | None:
    for key in _name_keys(name):
        for a in load_attractions():
            if a.get("name") == key or key in a.get("name", ""):
                if city is None or a.get("city") == city:
                    return a
    return None


def image_to_base64(relative_path: str | None) -> str | None:
    if not relative_path:
        return None
    full = ROOT / relative_path.replace("/", "\\")
    if not full.exists():
        fname = Path(relative_path).name
        full = IMAGE_DIR / fname
    if not full.exists():
        return None
    mime = "jpeg" if full.suffix.lower() in (".jpg", ".jpeg") else "png"
    data = base64.b64encode(full.read_bytes()).decode("ascii")
    return f"data:image/{mime};base64,{data}"


def enrich_plan(plan: dict) -> dict:
    """用 attractions.json 补全图片、标签、机位等字段。"""
    city = plan.get("trip_summary", {}).get("city")
    for day in plan.get("days", []):
        for item in day.get("items", []):
            if item.get("type") != "景点":
                continue
            att = lookup_attraction(item.get("name", ""), city)
            if not att:
                continue
            item.setdefault("attraction_id", att.get("id"))
            item.setdefault("rating", att.get("rating", 4.5))
            item.setdefault("tags", att.get("tags", []))
            item.setdefault("open_hours", att.get("open_hours", ""))
            item.setdefault("description", att.get("description", item.get("description", "")))
            item.setdefault("emoji", att.get("image_emoji", item.get("emoji", "📍")))
            item.setdefault("photo_spots", att.get("photo_spots", []))
            if "image_path" not in item:
                item["image_path"] = att.get("image_path")
            if item.get("cost", 0) == 0 and att.get("ticket_price"):
                pass
    return plan


def get_heatmap_hotspots(city: str) -> list[dict]:
    cities = load_heatmap().get("cities", {})
    return cities.get(city, {}).get("hotspots", [])
