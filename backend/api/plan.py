from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.agents.plan_agent import PlanAgent
from backend.db.models import SessionModel
from backend.db.sqlite import get_db

router = APIRouter()


class PlanRequest(BaseModel):
    city: str = Field(..., example="武汉")
    days: int = Field(..., ge=1, le=7, example=3)
    start_date: str = Field(..., example="2026-07-10")
    budget: float = Field(..., gt=0, example=1500.0)
    preferences: list[str] = Field(default_factory=list, example=["历史", "美食"])
    people: str = Field(default="朋友", example="朋友")
    departure: str = Field(default="武汉", example="武汉")


def _fallback_minimal_plan(req: PlanRequest) -> dict[str, Any]:
    return {
        "trip_summary": {
            "city": req.city,
            "days": req.days,
            "start_date": req.start_date,
            "end_date": req.start_date,
            "total_budget": req.budget,
            "people": req.people,
        },
        "weather": [],
        "days": [],
        "budget_breakdown": {"交通": 0, "住宿": 0, "门票": 0, "餐饮": 0, "其他": 0},
        "tips": ["Agent fallback returned an empty display plan."],
    }


def _store_session(db: Session, session_id: str, plan: dict[str, Any]) -> None:
    row = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    payload = json.dumps(plan, ensure_ascii=False)
    if row:
        row.current_plan_json = payload
        row.messages_json = row.messages_json or json.dumps([], ensure_ascii=False)
    else:
        db.add(
            SessionModel(
                session_id=session_id,
                user_id=None,
                current_plan_json=payload,
                messages_json=json.dumps([], ensure_ascii=False),
            )
        )
    db.commit()


def _normalize_agent_response(result: dict[str, Any], req: PlanRequest) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise TypeError("PlanAgent.plan() must return a dict")

    plan = result.get("plan")
    if not isinstance(plan, dict):
        plan = _fallback_minimal_plan(req)

    session_id = result.get("session_id") or f"ses_{uuid.uuid4().hex[:12]}"
    success = bool(result.get("success", True))
    response: dict[str, Any] = {
        "success": True,
        "session_id": session_id,
        "plan": plan,
        "tools_called": result.get("tools_called", []),
        "fallback": bool(result.get("fallback", False)) or not success,
    }
    if result.get("error"):
        response["warning"] = result["error"]
    return response


@router.post("/plan")
def create_plan(req: PlanRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Generate and persist a travel plan through member A's PlanAgent."""

    try:
        result = PlanAgent().plan(req.model_dump())
        response = _normalize_agent_response(result, req)
    except Exception as exc:
        session_id = f"ses_{uuid.uuid4().hex[:12]}"
        response = {
            "success": True,
            "session_id": session_id,
            "plan": _fallback_minimal_plan(req),
            "tools_called": ["api_fallback"],
            "fallback": True,
            "warning": f"PlanAgent failed, API fallback used: {exc}",
        }

    _store_session(db, response["session_id"], response["plan"])
    return response