"""Pydantic 模型 - 严格对齐项目方案 §7.2 响应 JSON。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.common import (
    BudgetCategory,
    ItemType,
    PeopleType,
    WeatherKind,
    WeatherSuggestion,
)


class _StrictModel(BaseModel):
    """所有 schema 共用:允许额外字段(向后兼容)但多余字段不报。"""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


# ---------------------------------------------------------------------------
# 请求
# ---------------------------------------------------------------------------
class AgentRequest(_StrictModel):
    """`/api/plan` 入参,字段名严格按方案 §7.2。"""

    city: str = Field(..., description="目的地")
    days: int = Field(..., ge=1, le=7, description="行程天数 1-7")
    start_date: str = Field(..., description="出发日期 YYYY-MM-DD")
    budget: float = Field(..., gt=0, description="总预算(元)")
    preferences: list[str] = Field(default_factory=list, description="偏好标签")
    people: PeopleType = Field("情侣", description="同行人群")
    departure: str = Field("武汉", description="出发地,用于估算交通费")
    session_id: Optional[str] = Field(default=None, description="可选会话 ID")


# ---------------------------------------------------------------------------
# Trip 子结构
# ---------------------------------------------------------------------------
class TripSummary(_StrictModel):
    city: str
    days: int
    start_date: str
    end_date: str
    total_budget: float
    people: PeopleType


class WeatherDay(_StrictModel):
    date: str
    weather: WeatherKind
    temp_high: float
    temp_low: float
    suggestion: WeatherSuggestion = "适合户外"
    wind: Optional[str] = None
    icon: Optional[str] = None


class Attraction(_StrictModel):
    """景点/POI 通用结构 - 给工具和 schema 共用。"""

    id: Optional[str] = None
    name: str
    city: Optional[str] = None
    category: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    description: Optional[str] = None
    best_duration_hours: Optional[float] = None
    ticket_price: float = 0.0
    lat: Optional[float] = None
    lng: Optional[float] = None
    emoji: Optional[str] = None
    rating: Optional[float] = None


class PlanDayItem(_StrictModel):
    time: str = Field(..., description="HH:MM")
    type: ItemType
    name: str
    duration_hours: float = 1.0
    cost: float = 0.0
    lat: Optional[float] = None
    lng: Optional[float] = None
    description: Optional[str] = None
    emoji: Optional[str] = None


class PlanDay(_StrictModel):
    day: int = Field(..., ge=1)
    date: str
    items: list[PlanDayItem] = Field(default_factory=list)
    day_cost: float = 0.0
    weather: Optional[WeatherDay] = None


class BudgetItem(_StrictModel):
    """预算条目(单项) - 用于 calculate_budget 输入。"""

    type: BudgetCategory
    name: Optional[str] = None
    cost: float


class BudgetBreakdown(_StrictModel):
    """`Plan.budget_breakdown` - 键名严格按方案 §7.2 字符串。"""

    交通: float = 0.0
    住宿: float = 0.0
    门票: float = 0.0
    餐饮: float = 0.0
    其他: float = 0.0


class BudgetResult(_StrictModel):
    """`calculate_budget` 工具输出。"""

    breakdown: BudgetBreakdown
    total: float
    total_budget: float
    is_over_budget: bool
    over_amount: float = 0.0
    suggestion: Optional[str] = None
    daily_costs: list[float] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Plan 顶层
# ---------------------------------------------------------------------------
class Plan(_StrictModel):
    trip_summary: TripSummary
    weather: list[WeatherDay] = Field(default_factory=list)
    days: list[PlanDay] = Field(default_factory=list)
    budget_breakdown: BudgetBreakdown = Field(default_factory=BudgetBreakdown)
    tips: list[str] = Field(default_factory=list)


class PlanResponse(_StrictModel):
    """`/api/plan` 响应外层,严格按方案 §7.2。

    兼容字段:`fallback` 标记兜底结果;`error` 标记主流程失败原因。
    """

    success: bool = True
    session_id: Optional[str] = None
    plan: Plan
    tools_called: list[str] = Field(default_factory=list)
    fallback: bool = False
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# 反射(预留,本轮不触发)
# ---------------------------------------------------------------------------
class ReflectionResult(_StrictModel):
    is_satisfied: bool
    issues: list[str] = Field(default_factory=list)
    suggestion: Optional[str] = None


__all__ = [
    "AgentRequest",
    "Attraction",
    "BudgetBreakdown",
    "BudgetItem",
    "BudgetResult",
    "Plan",
    "PlanDay",
    "PlanDayItem",
    "PlanResponse",
    "ReflectionResult",
    "TripSummary",
    "WeatherDay",
]