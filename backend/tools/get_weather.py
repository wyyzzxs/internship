"""get_weather 工具 - 临时 mock 实现。

⚠️ **临时越界 mock** - 方案 §8.3 / §9.2 此工具由**成员 B**负责接入和风天气 API。
   本文件由成员 A 在第二轮临时编写,仅供测试驱动 PlanAgent.modify / reflect-loop 跑通。
   B 接入真实实现后,本文件应被删除(tools/__init__.py 的 import 同步更新)。

签名严格对齐方案 §3.3 Tool 2:`(city, start_date, days=3) -> str(JSON)`
返回值字段:`date/weather/temp_high/temp_low/wind/suggestion/hourly(可选)`
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from langchain_core.tools import tool

from backend.config import Config

logger = logging.getLogger("backend.tools.get_weather")


def _read_cache() -> dict:
    cache_path = Config.DATA_DIR / "weather_cache.json"
    if not cache_path.exists():
        return {}
    try:
        with cache_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("读 weather_cache 失败: %s", exc)
        return {}


def _parse_start_date(start_date: str) -> datetime:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(start_date, fmt)
        except ValueError:
            continue
    return datetime.now()


def _weather_suggestion(weather: str) -> str:
    if any(k in weather for k in ("雨", "雷")):
        return "建议安排室内活动"
    if any(k in weather for k in ("晴", "多云")):
        return "适合户外"
    return "其他"


def _get_weather_impl(city: str, start_date: str, days: int = 3) -> dict:
    """从 weather_cache.json 读 mock 数据,缺日期时按"晴"兜底。"""
    days = max(1, min(int(days), 7))
    cache = _read_cache()
    start = _parse_start_date(start_date)

    out: list[dict] = []
    city_cache = cache.get(city) or cache.get("武汉") or {}
    for i in range(days):
        d = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        info = city_cache.get(d)
        if info:
            out.append(
                {
                    "date": d,
                    "weather": info.get("weather", "晴"),
                    "temp_high": info.get("temp_high", 30),
                    "temp_low": info.get("temp_low", 22),
                    "wind": info.get("wind", ""),
                    "icon": info.get("icon", ""),
                    "suggestion": _weather_suggestion(info.get("weather", "晴")),
                }
            )
        else:
            out.append(
                {
                    "date": d,
                    "weather": "晴",
                    "temp_high": 30,
                    "temp_low": 22,
                    "wind": "",
                    "icon": "☀️",
                    "suggestion": _weather_suggestion("晴"),
                }
            )

    return {"city": city, "weather": out, "source": "mock"}


@tool
def get_weather(city: str, start_date: str, days: int = 3) -> str:
    """查询未来 N 天天气预报(mock,B 接入和风 API 后替换)。

    Args:
        city: 城市名
        start_date: 起始日期 YYYY-MM-DD
        days: 天数 1-7

    Returns:
        JSON 字符串,每天含 date/weather/temp_high/temp_low/wind/suggestion。
    """
    result = _get_weather_impl(city, start_date, days)
    return json.dumps(result, ensure_ascii=False)


__all__ = ["get_weather", "_get_weather_impl"]
