from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.agents.plan_agent import PlanAgent
from backend.db.models import SessionModel
from backend.db.sqlite import get_db

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str = Field(..., example="ses_123456")
    message: str = Field(..., example="把第一天下午换成黄鹤楼")
    current_plan: dict[str, Any] | None = None


def _load_json_dict(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        data = json.loads(value)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _load_json_list(value: str | None) -> list[dict[str, Any]]:
    if not value:
        return []
    try:
        data = json.loads(value)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _fallback_reply(plan: dict[str, Any], message: str) -> dict[str, Any]:
    return {
        "reply": f"收到修改需求：{message}。当前演示环境已保留原行程，请稍后重试 Agent 修改。",
        "updated_plan": plan,
        "diff": {"day": None, "removed": None, "added": None},
    }


@router.post("/chat")
def chat_modify(req: ChatRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    session = db.query(SessionModel).filter(SessionModel.session_id == req.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {req.session_id} not found")

    current_plan = req.current_plan or _load_json_dict(session.current_plan_json)
    history = _load_json_list(session.messages_json)

    try:
        result = PlanAgent().modify(
            session_id=req.session_id,
            message=req.message,
            current_plan=current_plan,
        )
        if isinstance(result, str):
            result = json.loads(result)
    except Exception as exc:
        result = _fallback_reply(current_plan, req.message)
        result["warning"] = f"PlanAgent.modify failed, API fallback used: {exc}"

    reply = result.get("reply") or "行程已更新。"
    updated_plan = result.get("updated_plan") or current_plan
    diff = result.get("diff") or {"day": None, "removed": None, "added": None}

    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": reply})
    if len(history) > 20:
        history = history[-20:]

    session.current_plan_json = json.dumps(updated_plan, ensure_ascii=False)
    session.messages_json = json.dumps(history, ensure_ascii=False)
    db.commit()

    response = {
        "success": True,
        "reply": reply,
        "updated_plan": updated_plan,
        "diff": diff,
    }
    if result.get("warning"):
        response["warning"] = result["warning"]
    return response