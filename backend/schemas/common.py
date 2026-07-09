"""枚举 & 共用 Literal 类型。"""
from __future__ import annotations

from typing import Literal

# 行程项目类型(沿用方案 §7.2 字段)
ItemType = Literal["景点", "餐饮", "住宿", "交通", "门票", "其他"]

# 天气现象(常见简写,缺失值兜底归"其他")
WeatherKind = Literal[
    "晴",
    "多云",
    "阴",
    "小雨",
    "中雨",
    "大雨",
    "阵雨",
    "雷阵雨",
    "雪",
    "雾",
    "霾",
    "其他",
]

# 天气建议(放宽为 str,允许 LLM 自由生成;前端展示时再按需规范化)
WeatherSuggestion = str

# 同行人群
PeopleType = Literal["独自", "情侣", "亲子", "朋友", "商务"]

# 预算分类(注意:Plan.budget_breakdown 的键名严格按方案 §7.2 字符串)
BudgetCategory = Literal["交通", "住宿", "门票", "餐饮", "其他"]


__all__ = [
    "BudgetCategory",
    "ItemType",
    "PeopleType",
    "WeatherKind",
    "WeatherSuggestion",
]