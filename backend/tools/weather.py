"""Weather forecast tool with QWeather support and local fallback."""

from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta
from typing import Any

import requests

from .common import env_bool, load_json, tool_decorator


RAIN_KEYWORDS = ("雨", "雪", "雷", "阵雨", "暴雨")
WEATHER_ICONS = {
    "晴": "sunny",
    "多云": "cloudy",
    "阴": "overcast",
    "小雨": "rain",
    "阵雨": "rain",
    "雷阵雨": "storm",
    "中雨": "rain",
    "大雨": "rain",
}


def _parse_date(value: str | date | None) -> date:
    if isinstance(value, date):
        return value
    if not value:
        return date.today()
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def _advice(weather: str, temp_high: int, temp_low: int) -> str:
    if any(keyword in weather for keyword in RAIN_KEYWORDS):
        return "当天有降水风险，建议优先安排博物馆、商场、室内展馆，并携带雨具。"
    if temp_high >= 35:
        return "高温天气，建议避开 12:00-15:00 户外暴晒，增加午休和补水。"
    if temp_low <= 5:
        return "早晚温度较低，建议准备保暖外套。"
    return "天气适合常规游览，可按原计划安排室外景点。"


def _normalize_daily(
    city: str,
    forecast_date: date,
    raw: dict[str, Any],
    source: str,
) -> dict[str, Any]:
    weather = str(raw.get("weather") or raw.get("textDay") or raw.get("text") or "多云")
    temp_high = int(raw.get("temp_high") or raw.get("tempMax") or raw.get("temp") or 25)
    temp_low = int(raw.get("temp_low") or raw.get("tempMin") or max(temp_high - 6, -20))
    wind = str(
        raw.get("wind")
        or raw.get("windDirDay")
        or raw.get("windScaleDay")
        or raw.get("windDir")
        or "微风"
    )
    return {
        "city": city,
        "date": forecast_date.isoformat(),
        "weekday": "一二三四五六日"[forecast_date.weekday()],
        "weather": weather,
        "temp_high": temp_high,
        "temp_low": temp_low,
        "wind": wind,
        "icon": raw.get("icon") or WEATHER_ICONS.get(weather, "cloudy"),
        "rain_risk": any(keyword in weather for keyword in RAIN_KEYWORDS),
        "advice": _advice(weather, temp_high, temp_low),
        "source": source,
    }


def _fallback_forecast(city: str, start: date, days: int) -> list[dict[str, Any]]:
    cache = load_json("weather_cache.json")
    city_cache = cache.get(city)
    if not city_cache:
        city_cache = next(iter(cache.values()))

    rows = [city_cache[key] for key in sorted(city_cache)]
    result: list[dict[str, Any]] = []
    for offset in range(days):
        forecast_date = start + timedelta(days=offset)
        raw = rows[offset % len(rows)]
        result.append(_normalize_daily(city, forecast_date, raw, "local_cache"))
    return result


def _qweather_hosts() -> tuple[str | None, str, str]:
    api_host = os.getenv("QWEATHER_API_HOST", "").strip().rstrip("/")
    if api_host:
        return api_host, f"{api_host}/geo/v2/city/lookup", f"{api_host}/v7/weather/7d"
    return None, "https://geoapi.qweather.com/v2/city/lookup", "https://devapi.qweather.com/v7/weather/7d"


def _qweather_json(response: requests.Response) -> dict[str, Any]:
    response.raise_for_status()
    payload = response.json()
    code = str(payload.get("code", "200"))
    if code not in {"200", "0"}:
        raise RuntimeError(f"和风天气返回错误 code={code}: {payload}")
    return payload


def _safe_error_message(exc: Exception) -> str:
    message = str(exc)
    return re.sub(r"([?&]key=)[^&\s]+", r"\1***", message)


def _qweather_location_id(city: str, api_key: str) -> str | None:
    _, geo_url, _ = _qweather_hosts()
    response = requests.get(
        geo_url,
        params={"location": city, "key": api_key, "range": "cn"},
        timeout=8,
    )
    payload = _qweather_json(response)
    locations = payload.get("location") or []
    if not locations:
        return None
    return str(locations[0]["id"])


def _qweather_forecast(city: str, start: date, days: int, api_key: str) -> list[dict[str, Any]]:
    location_id = _qweather_location_id(city, api_key)
    if not location_id:
        return []

    _, _, weather_url = _qweather_hosts()
    response = requests.get(
        weather_url,
        params={"location": location_id, "key": api_key},
        timeout=8,
    )
    payload = _qweather_json(response)
    daily_rows = payload.get("daily") or []
    by_date = {row.get("fxDate"): row for row in daily_rows}

    result: list[dict[str, Any]] = []
    for offset in range(days):
        forecast_date = start + timedelta(days=offset)
        raw = by_date.get(forecast_date.isoformat())
        if raw:
            result.append(_normalize_daily(city, forecast_date, raw, "qweather"))
    return result


def get_weather_forecast(city: str, start_date: str | date | None = None, days: int = 3) -> dict[str, Any]:
    """Return a normalized weather forecast for the itinerary date range."""

    days = max(1, min(int(days), 7))
    start = _parse_date(start_date)
    api_key = os.getenv("QWEATHER_API_KEY", "").strip()
    force_mock = env_bool("MOCK_WEATHER", default=False)

    forecast: list[dict[str, Any]] = []
    errors: list[str] = []
    if api_key and not force_mock:
        try:
            forecast = _qweather_forecast(city, start, days, api_key)
        except Exception as exc:
            errors.append(f"QWeather 查询失败，已切换本地缓存：{_safe_error_message(exc)}")

    if len(forecast) < days:
        forecast = _fallback_forecast(city, start, days)

    summary = {
        "rainy_days": sum(1 for item in forecast if item["rain_risk"]),
        "max_temp": max(item["temp_high"] for item in forecast),
        "min_temp": min(item["temp_low"] for item in forecast),
        "source": forecast[0]["source"] if forecast else "unknown",
    }
    summary["overall_advice"] = (
        "行程中存在降水日，建议把室外核心景点安排在晴天，把博物馆、美食街、商场作为雨天备选。"
        if summary["rainy_days"]
        else "天气整体可控，适合按原计划游览。"
    )
    return {"city": city, "start_date": start.isoformat(), "days": days, "forecast": forecast, "summary": summary, "errors": errors}


@tool_decorator
def get_weather(city: str, start_date: str, days: int = 3) -> dict[str, Any]:
    """查询城市未来 1-7 天游玩天气，返回温度、降雨风险和行程建议。"""

    return get_weather_forecast(city=city, start_date=start_date, days=days)
