"""Mock 对话修改 — 与后端 PlanAgent._mock_modify_impl 规则对齐。"""

from __future__ import annotations

import re
from copy import deepcopy

from utils.data_loader import enrich_plan


def _recalc_day_cost(day: dict) -> None:
    day["day_cost"] = sum(float(item.get("cost", 0) or 0) for item in day.get("items", []))


def _extract_day_num(message: str) -> int | None:
    m = re.search(r"第\s*(\d+)\s*天", message)
    return int(m.group(1)) if m else None


def _extract_poi_name(message: str) -> str | None:
    """从消息里提取目标地点名。"""
    known = [
        "西安电子科技大学", "电子科技大学", "西电",
        "陕西历史博物馆", "湖北省博物馆", "兵马俑", "大雁塔", "黄鹤楼",
    ]
    for name in known:
        if name in message:
            return name

    patterns = [
        r"(?:去|到|参观|拜访|加上|增加|安排)\s*[「『\"']?([^，。；,\s「『\"']+?)(?:一趟|一下|看看)?[」』\"']?",
    ]
    for pat in patterns:
        m = re.search(pat, message)
        if m:
            name = m.group(1).strip("，。；, 一趟一下")
            if len(name) >= 2:
                return name
    if "博物馆" in message:
        return "博物馆"
    return None


def _insert_visit(plan: dict, poi_name: str, target_day: int | None = None) -> dict:
    """在指定天插入参观行程。"""
    days_list = plan.get("days") or []
    if not days_list:
        return {"day": None, "removed": None, "added": poi_name}

    day_idx = (target_day - 1) if target_day and 1 <= target_day <= len(days_list) else 0
    day = days_list[day_idx]

    # 西电坐标（长安校区近似）
    lat, lng = (34.1300, 108.8800) if "电子" in poi_name or "西电" in poi_name else (0.0, 0.0)
    new_item = {
        "time": "14:30",
        "end_time": "16:30",
        "type": "景点",
        "name": poi_name,
        "duration_hours": 2,
        "cost": 0,
        "lat": lat,
        "lng": lng,
        "description": f"按您的要求新增：{poi_name}",
        "emoji": "🎓" if "大学" in poi_name or "电" in poi_name else "📍",
    }
    day.setdefault("items", []).append(new_item)
    _recalc_day_cost(day)

    tips = list(plan.get("tips") or [])
    tip = f"已按对话调整：Day {day_idx + 1} 新增「{poi_name}」"
    if tip not in tips:
        tips.insert(0, tip)
    plan["tips"] = tips

    return {"day": day_idx + 1, "removed": None, "added": poi_name}


def _mock_modify_chat(message: str, plan: dict) -> dict:
    """与后端 PlanAgent._mock_modify_impl 对齐的规则修改。"""
    days_list = plan.get("days") or []
    bd = dict(plan.get("budget_breakdown") or {})
    diff: dict = {"day": None, "removed": None, "added": None}
    reply = ""

    target_day = _extract_day_num(message)
    poi = _extract_poi_name(message)

    # 重新安排 / 加目的地（答辩常见话术）
    if any(k in message for k in ("重新安排", "重新规划", "安排一下", "去一趟", "想去")) and poi:
        diff = _insert_visit(plan, poi, target_day)
        reply = f"好的，已为您重新安排行程，在 Day {diff['day']} 新增参观「{poi}」。"

    # 换 / 改成
    elif any(k in message for k in ("换", "改成", "替换", "改为", "换成")):
        new_name = poi or "新景点"
        if target_day and 1 <= target_day <= len(days_list):
            d = days_list[target_day - 1]
            items = d.get("items") or []
            if items:
                removed = items[-1].get("name", "")
                items[-1] = {**items[-1], "name": new_name, "description": f"已替换为{new_name}"}
                _recalc_day_cost(d)
                diff = {"day": target_day, "removed": removed, "added": new_name}
                reply = f"已将 Day {target_day} 末尾活动从「{removed}」改为「{new_name}」。"
        elif days_list and days_list[0].get("items"):
            d = days_list[0]
            items = d["items"]
            removed = items[-1].get("name", "")
            items[-1] = {**items[-1], "name": new_name, "description": f"已替换为{new_name}"}
            _recalc_day_cost(d)
            diff = {"day": 1, "removed": removed, "added": new_name}
            reply = f"已将 Day 1 末尾活动从「{removed}」改为「{new_name}」。"

    # 博物馆（答辩用例）
    elif "博物馆" in message:
        for day in days_list:
            for item in day.get("items", []):
                if any(k in item.get("name", "") for k in ("江滩", "江汉", "城墙", "回民")):
                    removed = item["name"]
                    item.update({
                        "name": "陕西历史博物馆" if plan.get("trip_summary", {}).get("city") == "西安" else "湖北省博物馆",
                        "description": "馆藏丰富，建议提前预约",
                        "cost": 0,
                        "emoji": "🏛️",
                        "lat": 34.2240,
                        "lng": 108.9550,
                    })
                    _recalc_day_cost(day)
                    diff = {"day": day["day"], "removed": removed, "added": item["name"]}
                    reply = f"好的，已将「{removed}」改为「{item['name']}」。"
                    break

    # 减预算
    elif any(k in message for k in ("减预算", "砍预算", "降低预算", "压预算", "省钱")) or (
        re.search(r"\d{3,5}\s*元", message) and any(k in message for k in ("砍", "压", "减", "降"))
    ):
        target = None
        m = re.search(r"(\d{3,5})\s*元", message)
        if m:
            target = float(m.group(1))
        current_total = sum(float(v or 0) for v in bd.values()) or 1
        scale = (target / current_total) if target else 0.8
        plan["budget_breakdown"] = {k: max(1, int(float(v) * scale)) for k, v in bd.items()}
        if target:
            plan.setdefault("trip_summary", {})["total_budget"] = int(target)
            reply = f"已按比例压缩预算到 {int(target)} 元。"
        else:
            reply = "已按比例压缩预算，住宿和餐饮已调整为更经济方案。"
        diff = {"type": "budget", "new_budget": int(target or current_total * scale)}

    # 加景点
    elif any(k in message for k in ("加", "增加", "添", "加一个")):
        city = plan.get("trip_summary", {}).get("city", "武汉")
        name = poi or ("陕西历史博物馆" if city == "西安" else "湖北省博物馆")
        target = target_day or len(days_list)
        if days_list and 1 <= target <= len(days_list):
            diff = _insert_visit(plan, name, target)
            reply = f"已在 Day {target} 追加「{name}」。"

    # 加住宿
    elif any(k in message for k in ("住", "酒店", "订房")):
        if days_list:
            d = days_list[-1]
            d.setdefault("items", []).append({
                "time": "20:00", "type": "住宿", "name": "经济型酒店",
                "duration_hours": 8, "cost": 300, "emoji": "🏨",
            })
            _recalc_day_cost(d)
            bd["住宿"] = int(bd.get("住宿", 0)) + 300
            plan["budget_breakdown"] = bd
            diff = {"day": len(days_list), "added": "经济型酒店"}
            reply = f"已在 Day {len(days_list)} 追加住宿（¥300）。"

    if not reply:
        if poi:
            diff = _insert_visit(plan, poi, target_day or 1)
            reply = f"已记录您的需求，并在 Day {diff['day']} 加入「{poi}」。"
        else:
            reply = (
                f"收到：「{message}」。"
                "当前为 Mock 对话模式，支持：换景点 / 加目的地 / 减预算 / 加景点 / 加住宿。"
                "后端 `/api/chat` 接入后将走 Agent 真实修改。"
            )

    enrich_plan(plan)
    return {"success": True, "reply": reply, "updated_plan": plan, "diff": diff}


def get_mock_chat_response(message: str, current_plan: dict | None = None) -> dict:
    if current_plan:
        plan = deepcopy(current_plan)
    else:
        from utils.mock_data import _build_wuhan_plan
        plan = _build_wuhan_plan()["plan"]
    return _mock_modify_chat(message, plan)
