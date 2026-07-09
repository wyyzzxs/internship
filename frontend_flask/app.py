"""Flask 版前端 — 旅行暗色主题，与 Streamlit 并行。"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
FLASK_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

sys.path.insert(0, str(FLASK_DIR))
sys.path.insert(0, str(ROOT / "frontend"))

from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from helpers import (
    chat_api,
    collect_attractions,
    collect_map_points,
    compare_plans,
    fetch_checklist,
    fetch_plan_api,
    form_context,
    form_from_plan,
    form_stale,
    export_filename,
    get_city_center,
    get_heatmap_data,
    load_preset,
    plan_stats,
    plan_to_json,
    plan_to_markdown,
    plan_to_pdf_bytes,
    resolve_form,
    weather_for_day,
)
from plan_store import (
    cache_id,
    clear_plans,
    get_plan,
    get_previous_plan,
    resolve_plan,
    set_plan,
    trim_chat_messages,
    update_plan,
)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-travel-planner-secret-change-me")


def _amap_config() -> dict:
    return {
        "key": os.getenv("AMAP_JS_API_KEY", ""),
        "security": os.getenv("AMAP_SECURITY_JS_CODE", ""),
    }


def _pop_flash() -> dict:
    return {
        "error": session.pop("flash_error", None),
        "success": session.pop("flash_success", None),
    }


def _plan_context(plan: dict | None) -> dict:
    if not plan:
        return {}
    bd = plan.get("budget_breakdown", {})
    total_spent = sum(bd.values()) if bd else 0
    summary = plan.get("trip_summary", {})
    total_budget = summary.get("total_budget", 0)
    return {
        "attractions": collect_attractions(plan),
        "map_points": collect_map_points(plan),
        "total_spent": total_spent,
        "days_cost": [d.get("day_cost", 0) for d in plan.get("days", [])],
        "budget_usage_pct": round(total_spent / total_budget * 100, 1) if total_budget else 0,
        "city_center": get_city_center(plan),
        "heatmap_data": get_heatmap_data(summary.get("city", "")),
        "stats": plan_stats(plan),
    }


def _parse_generate_form() -> dict:
    prefs = request.form.getlist("preferences")
    start_date = (request.form.get("start_date") or "").strip()
    if not start_date:
        start_date = date.today().isoformat()
    return {
        "city": request.form.get("city", "武汉"),
        "days": int(request.form.get("days", 3)),
        "start_date": start_date,
        "budget": int(request.form.get("budget", 1500)),
        "preferences": prefs,
        "people": request.form.get("people", "情侣出游"),
        "departure": request.form.get("departure", "武汉"),
        "special": request.form.get("special") or None,
    }


@app.route("/")
def index():
    plan = get_plan()
    form = resolve_form(session, plan)
    ctx = form_context()
    ctx.update({
        "plan": plan,
        "plan_b": get_previous_plan(),
        "compare": compare_plans(plan, get_previous_plan()),
        "chat_messages": session.get("chat_messages", []),
        "amap": _amap_config(),
        "form": form,
        "today": date.today().isoformat(),
        "form_stale": form_stale(form, plan),
        "cache_id": cache_id() if plan else session.get("cache_id", ""),
        "active_tab": request.args.get("tab", "itinerary"),
        "show_heatmap": session.get("show_heatmap", False),
        "flash": _pop_flash(),
        "weather_for_day": weather_for_day,
    })
    ctx.update(_plan_context(plan))
    return render_template("index.html", **ctx)


@app.route("/generate", methods=["POST"])
def generate():
    form = _parse_generate_form()
    session["last_form"] = form
    session["show_heatmap"] = request.form.get("show_heatmap") == "on"
    try:
        resp = fetch_plan_api(form)
        if resp.get("success"):
            set_plan(resp["plan"], track_previous=True)
            session["session_id"] = resp.get("session_id", "")
            session.setdefault("chat_messages", [])
            session["flash_success"] = "行程生成成功"
        else:
            session["flash_error"] = resp.get("error", "生成失败")
    except Exception as exc:
        session["flash_error"] = str(exc)
    return redirect(url_for("index", tab="itinerary"))


@app.route("/preset", methods=["POST"])
def preset():
    key = request.form.get("preset_key", "")
    data = load_preset(key)
    if data:
        set_plan(data["plan"], track_previous=True)
        session["session_id"] = data.get("session_id", "")
        session["last_form"] = form_from_plan(data["plan"])
        session["flash_success"] = f"已加载预设：{key}"
    else:
        session["flash_error"] = "预设不存在"
    return redirect(url_for("index", tab="itinerary"))


@app.route("/settings", methods=["POST"])
def settings():
    session["show_heatmap"] = request.form.get("show_heatmap") == "on"
    return redirect(url_for("index", tab=request.form.get("return_tab", "map")))


@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(force=True, silent=True) or {}
    message = (payload.get("message") or "").strip()
    if not message:
        return jsonify({"success": False, "reply": "消息不能为空"})
    plan = get_plan()
    if not plan:
        return jsonify({"success": False, "reply": "请先生成行程"})
    sid = session.get("session_id", "")
    try:
        result = chat_api(sid, message, plan)
    except Exception as exc:
        return jsonify({"success": False, "reply": f"请求失败：{exc}"})
    msgs = session.setdefault("chat_messages", [])
    msgs.append({"role": "user", "content": message})
    msgs.append({"role": "assistant", "content": result.get("reply", "")})
    if result.get("updated_plan"):
        update_plan(result["updated_plan"])
        session["last_form"] = form_from_plan(result["updated_plan"])
    session["chat_messages"] = trim_chat_messages(msgs)
    return jsonify(result)


@app.route("/export/<fmt>")
def export(fmt: str):
    cid = request.args.get("cid", "")
    plan = resolve_plan(cid or None)
    if not plan:
        session["flash_error"] = "暂无行程可导出，请先生成或加载预设"
        return redirect(url_for("index", tab="itinerary"))

    city = plan.get("trip_summary", {}).get("city", "travel")
    try:
        if fmt == "md":
            _, headers = export_filename(city, "plan.md")
            return Response(plan_to_markdown(plan), mimetype="text/markdown; charset=utf-8", headers=headers)
        if fmt == "json":
            _, headers = export_filename(city, "plan.json")
            return Response(plan_to_json(plan), mimetype="application/json; charset=utf-8", headers=headers)
        if fmt == "pdf":
            pdf = plan_to_pdf_bytes(plan)
            if pdf:
                _, headers = export_filename(city, "plan.pdf")
                return Response(pdf, mimetype="application/pdf", headers=headers)
            _, headers = export_filename(city, "plan.txt")
            return Response(plan_to_markdown(plan), mimetype="text/plain; charset=utf-8", headers=headers)
        if fmt == "checklist":
            people = plan.get("trip_summary", {}).get("people", "朋友")
            _, headers = export_filename(city, "checklist.md")
            return Response(
                fetch_checklist(plan, people),
                mimetype="text/markdown; charset=utf-8",
                headers=headers,
            )
    except Exception as exc:
        session["flash_error"] = f"导出失败：{exc}"
        return redirect(url_for("index", tab="export"))

    session["flash_error"] = "不支持的导出格式"
    return redirect(url_for("index", tab="export"))


@app.route("/clear-chat", methods=["POST"])
def clear_chat():
    session["chat_messages"] = []
    return redirect(url_for("index", tab="chat"))


@app.route("/clear")
def clear():
    clear_plans()
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", "8502"))
    app.run(host="127.0.0.1", port=port, debug=True)
