"""Mock 数据 — 3 个答辩演示预设 + 对话模拟。"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta

from utils.data_loader import enrich_plan

TOOLS_CALLED = [
    "search_attractions",
    "get_weather",
    "calculate_budget",
    "optimize_route",
]
SESSION_ID = "ses_mock_20250708_001"


def _base_plan(city: str, days: int, budget: int, people: str) -> dict:
    start = date.today()
    end = start + timedelta(days=days - 1)
    return {
        "trip_summary": {
            "city": city,
            "days": days,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "total_budget": budget,
            "people": people,
        },
        "weather": [],
        "days": [],
        "budget_breakdown": {},
        "tips": [],
    }


def _wrap(plan: dict) -> dict:
    plan = enrich_plan(plan)
    return {
        "success": True,
        "session_id": SESSION_ID,
        "plan": plan,
        "tools_called": TOOLS_CALLED,
    }


def _build_wuhan_plan() -> dict:
    start = date.today()
    d = [start + timedelta(days=i) for i in range(3)]
    plan = _base_plan("武汉", 3, 1500, "情侣出游")
    plan["weather"] = [
        {"date": d[0].isoformat(), "weather": "晴", "temp_high": 33, "temp_low": 26, "suggestion": "适合户外"},
        {"date": d[1].isoformat(), "weather": "多云", "temp_high": 31, "temp_low": 25, "suggestion": "适合户外"},
        {"date": d[2].isoformat(), "weather": "小雨", "temp_high": 28, "temp_low": 23, "suggestion": "建议室内"},
    ]
    plan["days"] = [
        {
            "day": 1, "date": d[0].isoformat(), "weekday": "周六", "steps": 12000,
            "items": [
                {"time": "08:30", "end_time": "09:30", "type": "交通", "name": "武汉站 → 黄鹤楼", "duration_hours": 1, "cost": 6, "lat": 30.5438, "lng": 114.3055, "description": "地铁 4 号线", "emoji": "🚄", "transport": "地铁"},
                {"time": "10:00", "end_time": "12:00", "type": "景点", "name": "黄鹤楼", "duration_hours": 2, "cost": 80, "lat": 30.5438, "lng": 114.3055, "description": "江南三大名楼之首", "emoji": "🏯"},
                {"time": "12:30", "end_time": "13:30", "type": "餐饮", "name": "户部巷午餐", "duration_hours": 1, "cost": 50, "lat": 30.5465, "lng": 114.2978, "description": "热干面、豆皮", "emoji": "🍜"},
                {"time": "14:30", "end_time": "17:00", "type": "景点", "name": "长江大桥", "duration_hours": 2.5, "cost": 0, "lat": 30.5497, "lng": 114.2896, "description": "步行长江大桥", "emoji": "🌊"},
                {"time": "20:00", "end_time": "21:00", "type": "景点", "name": "江汉江滩", "duration_hours": 1, "cost": 0, "lat": 30.5580, "lng": 114.2950, "description": "长江灯光秀", "emoji": "🌃"},
            ],
            "day_cost": 136,
        },
        {
            "day": 2, "date": d[1].isoformat(), "weekday": "周日", "steps": 9800,
            "items": [
                {"time": "09:00", "end_time": "12:00", "type": "景点", "name": "湖北省博物馆", "duration_hours": 3, "cost": 0, "lat": 30.5625, "lng": 114.3665, "description": "曾侯乙编钟", "emoji": "🏛️"},
                {"time": "14:30", "end_time": "17:30", "type": "景点", "name": "东湖风景区", "duration_hours": 3, "cost": 0, "lat": 30.5510, "lng": 114.4100, "description": "东湖绿道骑行", "emoji": "🌿"},
            ],
            "day_cost": 160,
        },
        {
            "day": 3, "date": d[2].isoformat(), "weekday": "周一", "steps": 7500,
            "items": [
                {"time": "09:30", "end_time": "11:30", "type": "景点", "name": "昙华林", "duration_hours": 2, "cost": 0, "lat": 30.5480, "lng": 114.3080, "description": "文艺街区", "emoji": "📸"},
                {"time": "14:00", "end_time": "16:00", "type": "景点", "name": "武汉大学", "duration_hours": 2, "cost": 0, "lat": 30.5360, "lng": 114.3650, "description": "珞珈山校园", "emoji": "🎓"},
            ],
            "day_cost": 46,
        },
    ]
    plan["budget_breakdown"] = {"交通": 200, "住宿": 600, "门票": 80, "餐饮": 470, "其他": 150}
    plan["tips"] = ["湖北省博物馆需提前预约", "第 3 天有小雨，建议室内景点"]
    return _wrap(plan)


def _build_xian_family_plan() -> dict:
    start = date.today()
    d = [start + timedelta(days=i) for i in range(3)]
    plan = _base_plan("西安", 3, 3000, "亲子家庭")
    plan["weather"] = [
        {"date": d[0].isoformat(), "weather": "晴", "temp_high": 30, "temp_low": 20, "suggestion": "适合户外"},
        {"date": d[1].isoformat(), "weather": "晴", "temp_high": 32, "temp_low": 22, "suggestion": "注意防晒"},
        {"date": d[2].isoformat(), "weather": "多云", "temp_high": 28, "temp_low": 19, "suggestion": "适合户外"},
    ]
    plan["days"] = [
        {
            "day": 1, "date": d[0].isoformat(), "weekday": "周六", "steps": 8000,
            "items": [
                {"time": "09:00", "end_time": "12:00", "type": "景点", "name": "兵马俑", "duration_hours": 3, "cost": 120, "lat": 34.3844, "lng": 109.2786, "description": "世界第八大奇迹", "emoji": "🏺"},
                {"time": "14:00", "end_time": "16:00", "type": "景点", "name": "华清宫", "duration_hours": 2, "cost": 120, "lat": 34.3675, "lng": 109.2138, "description": "唐玄宗与杨贵妃", "emoji": "♨️"},
            ],
            "day_cost": 280,
        },
        {
            "day": 2, "date": d[1].isoformat(), "weekday": "周日", "steps": 10000,
            "items": [
                {"time": "09:00", "end_time": "11:30", "type": "景点", "name": "大雁塔", "duration_hours": 2.5, "cost": 50, "lat": 34.2183, "lng": 108.9641, "description": "唐代佛教建筑", "emoji": "🗼"},
                {"time": "14:00", "end_time": "17:00", "type": "景点", "name": "陕西历史博物馆", "duration_hours": 3, "cost": 0, "lat": 34.2240, "lng": 108.9550, "description": "馆藏丰富，适合亲子", "emoji": "🏛️"},
            ],
            "day_cost": 150,
        },
        {
            "day": 3, "date": d[2].isoformat(), "weekday": "周一", "steps": 6000,
            "items": [
                {"time": "10:00", "end_time": "12:00", "type": "景点", "name": "西安城墙", "duration_hours": 2, "cost": 54, "lat": 34.2587, "lng": 108.9467, "description": "骑行城墙", "emoji": "🏰"},
                {"time": "18:00", "end_time": "20:00", "type": "餐饮", "name": "回民街", "duration_hours": 2, "cost": 120, "lat": 34.2625, "lng": 108.9400, "description": "羊肉泡馍、肉夹馍", "emoji": "🍖"},
            ],
            "day_cost": 174,
        },
    ]
    plan["budget_breakdown"] = {"交通": 400, "住宿": 1200, "门票": 344, "餐饮": 600, "其他": 256}
    plan["tips"] = ["兵马俑建议请讲解", "亲子游节奏放缓，每天 2-3 个景点"]
    return _wrap(plan)


def _build_chengdu_food_plan() -> dict:
    start = date.today()
    d = [start, start + timedelta(days=1)]
    plan = _base_plan("成都", 2, 800, "情侣出游")
    plan["trip_summary"]["days"] = 2
    plan["weather"] = [
        {"date": d[0].isoformat(), "weather": "阴", "temp_high": 26, "temp_low": 18, "suggestion": "适合户外"},
        {"date": d[1].isoformat(), "weather": "多云", "temp_high": 27, "temp_low": 19, "suggestion": "适合户外"},
    ]
    plan["days"] = [
        {
            "day": 1, "date": d[0].isoformat(), "weekday": "周六", "steps": 9000,
            "items": [
                {"time": "09:30", "end_time": "11:30", "type": "景点", "name": "宽窄巷子", "duration_hours": 2, "cost": 0, "lat": 30.6638, "lng": 104.0552, "description": "老成都缩影", "emoji": "🏘️"},
                {"time": "12:00", "end_time": "13:30", "type": "餐饮", "name": "奎星楼街", "duration_hours": 1.5, "cost": 80, "lat": 30.6620, "lng": 104.0580, "description": "冒烤鸭、糖油果子", "emoji": "🌶️"},
                {"time": "15:00", "end_time": "17:00", "type": "景点", "name": "锦里古街", "duration_hours": 2, "cost": 0, "lat": 30.6459, "lng": 104.0480, "description": "三国文化 + 小吃", "emoji": "🏮"},
            ],
            "day_cost": 80,
        },
        {
            "day": 2, "date": d[1].isoformat(), "weekday": "周日", "steps": 7000,
            "items": [
                {"time": "08:30", "end_time": "11:00", "type": "景点", "name": "成都大熊猫繁育研究基地", "duration_hours": 2.5, "cost": 55, "lat": 30.7410, "lng": 104.1480, "description": "看国宝吃竹子", "emoji": "🐼"},
                {"time": "12:30", "end_time": "14:00", "type": "餐饮", "name": "建设路小吃街", "duration_hours": 1.5, "cost": 60, "lat": 30.6700, "lng": 104.1000, "description": "成都网红美食街", "emoji": "🍜"},
            ],
            "day_cost": 115,
        },
    ]
    # 故意超预算演示
    plan["budget_breakdown"] = {"交通": 150, "住宿": 400, "门票": 55, "餐饮": 350, "其他": 100}
    plan["tips"] = ["成都美食偏辣，可备注微辣", "熊猫基地建议早上 8 点前到"]
    return _wrap(plan)


DEMO_PRESETS: dict[str, dict] = {
    "武汉 3 天 1500 元（历史文化）": _build_wuhan_plan(),
    "西安 3 天亲子（历史游）": _build_xian_family_plan(),
    "成都 2 日美食游（预算 800）": _build_chengdu_food_plan(),
}


def get_mock_plan(city: str = "武汉", **_kwargs) -> dict:
    for preset in DEMO_PRESETS.values():
        if preset["plan"]["trip_summary"]["city"] == city:
            return deepcopy(preset)
    plan = _build_wuhan_plan()
    plan["plan"]["trip_summary"]["city"] = city
    return plan


def get_mock_chat_response(message: str, current_plan: dict | None = None) -> dict:
    plan = deepcopy(current_plan) if current_plan else _build_wuhan_plan()["plan"]

    if "博物馆" in message:
        for day in plan.get("days", []):
            for item in day.get("items", []):
                if "江滩" in item.get("name", "") or "江汉" in item.get("name", ""):
                    item["name"] = "湖北省博物馆"
                    item["description"] = "曾侯乙编钟，免费参观"
                    item["cost"] = 0
                    item["emoji"] = "🏛️"
                    item["lat"] = 30.5625
                    item["lng"] = 114.3665
                    enrich_plan(plan)
                    return {
                        "success": True,
                        "reply": "好的，已把江滩改为湖北省博物馆，游览 2 小时，免费参观。",
                        "updated_plan": plan,
                        "diff": {"day": day["day"], "removed": "江汉江滩", "added": "湖北省博物馆"},
                    }

    if "预算" in message or "省钱" in message or "1000" in message:
        bd = plan.get("budget_breakdown", {})
        for k in bd:
            bd[k] = int(bd[k] * 0.7)
        plan["trip_summary"]["total_budget"] = 1000
        return {
            "success": True,
            "reply": "已将预算压缩至 1000 元，住宿和餐饮已调整为经济型方案。",
            "updated_plan": plan,
            "diff": {"type": "budget", "new_budget": 1000},
        }

    if "加" in message and ("景点" in message or "博物馆" in message):
        if plan.get("days"):
            day = plan["days"][-1]
            day["items"].append({
                "time": "15:00", "end_time": "17:00", "type": "景点",
                "name": "湖北省博物馆", "duration_hours": 2, "cost": 0,
                "lat": 30.5625, "lng": 114.3665,
                "description": "曾侯乙编钟", "emoji": "🏛️",
            })
            enrich_plan(plan)
            return {
                "success": True,
                "reply": f"已在 Day {day['day']} 下午添加湖北省博物馆。",
                "updated_plan": plan,
                "diff": {"day": day["day"], "added": "湖北省博物馆"},
            }

    return {
        "success": True,
        "reply": f"收到：「{message}」。Mock 模式下已记录，联调后将由 Agent 真实修改。",
        "updated_plan": plan,
        "diff": None,
    }
