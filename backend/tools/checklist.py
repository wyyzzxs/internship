"""Travel checklist generator."""

from __future__ import annotations

from typing import Any

from .common import tool_decorator


def _weather_rows(weather: dict[str, Any] | list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if weather is None:
        return []
    if isinstance(weather, dict):
        return list(weather.get("forecast") or [])
    return list(weather)


def _extract_activity_names(plan: dict[str, Any] | None) -> list[str]:
    if not plan:
        return []
    activities: list[str] = []
    for day in plan.get("itinerary", []) or plan.get("days", []) or []:
        for item in day.get("items", []) or day.get("activities", []) or []:
            name = item.get("name") or item.get("title") or item.get("attraction")
            if name:
                activities.append(str(name))
    return activities[:8]


def generate_checklist_text(
    plan: dict[str, Any] | None = None,
    weather: dict[str, Any] | list[dict[str, Any]] | None = None,
    people_type: str = "朋友",
) -> str:
    """Generate a Markdown checklist from itinerary, weather and traveller type."""

    rows = _weather_rows(weather)
    activities = _extract_activity_names(plan)
    rainy = any(item.get("rain_risk") or "雨" in str(item.get("weather", "")) for item in rows)
    hot = any(int(item.get("temp_high", 0) or 0) >= 32 for item in rows)
    cold = any(int(item.get("temp_low", 99) or 99) <= 8 for item in rows)
    people_type = people_type or "朋友"

    sections: dict[str, list[str]] = {
        "证件与支付": ["身份证/学生证", "少量现金", "银行卡或移动支付备用方式"],
        "生活用品": ["换洗衣物", "舒适步行鞋", "纸巾与湿巾", "水杯"],
        "电子产品": ["手机充电器", "充电宝", "耳机", "相机或备用存储卡"],
        "药品": ["常用药", "创可贴", "肠胃药"],
    }

    if rainy:
        sections["天气装备"] = ["折叠伞或轻便雨衣", "防水袋", "备用袜子"]
    elif hot:
        sections["天气装备"] = ["防晒霜", "遮阳帽", "墨镜", "清凉喷雾"]
    elif cold:
        sections["天气装备"] = ["保暖外套", "围巾", "暖宝宝"]

    if people_type == "亲子":
        sections["同行人群"] = ["儿童常用药", "儿童水杯", "备用零食", "小玩具"]
    elif people_type == "情侣":
        sections["同行人群"] = ["拍照支架", "预订纪念餐厅", "轻便香水"]
    elif people_type == "商务":
        sections["同行人群"] = ["正装", "电脑与电源", "名片或资料夹"]
    elif people_type == "独自":
        sections["同行人群"] = ["紧急联系人卡片", "备用门锁", "离线地图"]

    if activities:
        sections["行程相关"] = [f"{name} 门票/预约截图" for name in activities[:3]]

    lines = ["## 旅行 Checklist"]
    for title, items in sections.items():
        lines.append(f"\n### {title}")
        for item in items:
            lines.append(f"- [ ] {item}")
    return "\n".join(lines)


@tool_decorator
def generate_checklist(plan: dict, weather: dict, people_type: str = "朋友") -> str:
    """根据行程、天气和同行人群生成 Markdown 旅行装备清单。"""

    return generate_checklist_text(plan=plan, weather=weather, people_type=people_type)

