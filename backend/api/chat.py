import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from backend.config import settings
from backend.db.sqlite import get_db
from backend.db.models import SessionModel

router = APIRouter()

class ChatRequest(BaseModel):
    session_id: str = Field(..., example="ses_123456")
    message: str = Field(..., example="把第一天下午换成黄鹤楼")
    current_plan: Optional[Dict[str, Any]] = None

def mock_modify_plan(plan: dict, message: str) -> tuple[dict, str, dict]:
    # Rule-based simple mock adjustments
    reply = "好的，我已为您调整了行程。"
    diff = {"day": 1, "action": "modify"}
    
    # Try to determine which day is being talked about
    day_num = 1
    for word in ["第一天", "Day 1", "day 1", "day1"]:
        if word in message:
            day_num = 1
    for word in ["第二天", "Day 2", "day 2", "day2"]:
        if word in message:
            day_num = 2
    for word in ["第三天", "Day 3", "day 3", "day3"]:
        if word in message:
            day_num = 3

    # Ensure day_num is within range
    days_list = plan.get("days", [])
    if day_num > len(days_list):
        day_num = len(days_list)

    if day_num <= 0:
        day_num = 1

    day_index = day_num - 1
    
    # Check if keyword matches "黄鹤楼"
    if "黄鹤楼" in message:
        if day_index < len(days_list):
            items = days_list[day_index].get("items", [])
            # Find the first attraction
            for item in items:
                if item.get("type") == "景点":
                    old_name = item["name"]
                    item["name"] = "黄鹤楼"
                    item["cost"] = 80
                    item["lat"] = 30.5438
                    item["lng"] = 114.3055
                    item["description"] = "江南三大名楼之首，崔颢题诗名扬天下。"
                    item["emoji"] = "🏯"
                    reply = f"好的，已将第 {day_num} 天下午的景点替换为黄鹤楼，门票费用为 ¥80。"
                    diff = {"day": day_num, "removed": old_name, "added": "黄鹤楼"}
                    break
                    
    elif "博物馆" in message:
        if day_index < len(days_list):
            items = days_list[day_index].get("items", [])
            for item in items:
                if item.get("type") == "景点":
                    old_name = item["name"]
                    item["name"] = "湖北省博物馆"
                    item["cost"] = 0  # Museum is free
                    item["lat"] = 30.5619
                    item["lng"] = 114.3592
                    item["description"] = "国家一级博物馆，馆藏曾侯乙编钟、越王勾践剑等国宝。"
                    item["emoji"] = "🏛️"
                    reply = f"好的，已将第 {day_num} 天的景点改为湖北省博物馆，该场馆免费预约参观。"
                    diff = {"day": day_num, "removed": old_name, "added": "湖北省博物馆"}
                    break
                    
    elif "省博" in message:
        if day_index < len(days_list):
            items = days_list[day_index].get("items", [])
            for item in items:
                if item.get("type") == "景点":
                    old_name = item["name"]
                    item["name"] = "湖北省博物馆"
                    item["cost"] = 0
                    item["lat"] = 30.5619
                    item["lng"] = 114.3592
                    item["description"] = "曾侯乙编钟与越王勾践剑所在地。"
                    item["emoji"] = "🏛️"
                    reply = f"已为您将第 {day_num} 天上午安排为湖北省博物馆。"
                    diff = {"day": day_num, "removed": old_name, "added": "湖北省博物馆"}
                    break
                    
    elif "增加预算" in message or "预算增加" in message or "加预算" in message:
        # Increase budget
        summary = plan.get("trip_summary", {})
        old_budget = summary.get("total_budget", 1000)
        new_budget = old_budget + 200
        summary["total_budget"] = new_budget
        
        breakdown = plan.get("budget_breakdown", {})
        breakdown["住宿"] = breakdown.get("住宿", 200) + 150
        breakdown["餐饮"] = breakdown.get("餐饮", 100) + 50
        
        reply = f"已为您上调总预算至 ¥{new_budget}，增加了酒店和餐饮的配额，提升住宿及就餐品质。"
        diff = {"type": "budget_change", "old_budget": old_budget, "new_budget": new_budget}
        
    else:
        # Default mock response: change something slightly or just reply
        reply = f"收到指令：“{message}”。已对第 {day_num} 天行程进行微调，优化了路线顺序与游览时间分配。"
        diff = {"day": day_num, "action": "route_optimize"}
        
    # Recalculate day costs in the plan
    for day in plan.get("days", []):
        day["day_cost"] = sum(item.get("cost", 0) for item in day.get("items", []))
        
    return plan, reply, diff

@router.post("/chat")
def chat_modify(req: ChatRequest, db: Session = Depends(get_db)):
    # 1. Fetch Session from DB
    session = db.query(SessionModel).filter(SessionModel.session_id == req.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {req.session_id} not found")
        
    current_plan = json.loads(session.current_plan_json) if session.current_plan_json else {}
    history = json.loads(session.messages_json) if session.messages_json else []
    
    # If the request contains current_plan, prefer using it
    if req.current_plan:
        current_plan = req.current_plan

    if settings.USE_MOCK:
        updated_plan, reply, diff = mock_modify_plan(current_plan, req.message)
        
        # Save updated history
        history.append({"role": "user", "content": req.message})
        history.append({"role": "assistant", "content": reply})
        # Keep history under 10 rounds (20 messages)
        if len(history) > 20:
            history = history[-20:]
            
        session.current_plan_json = json.dumps(updated_plan, ensure_ascii=False)
        session.messages_json = json.dumps(history, ensure_ascii=False)
        db.commit()
        
        return {
            "success": True,
            "reply": reply,
            "updated_plan": updated_plan,
            "diff": diff
        }
        
    # Non-mock logic: Invoke Member A's Agent.modify()
    try:
        from backend.agents.plan_agent import PlanAgent
        agent = PlanAgent()
        
        # Build prompt or call modify method
        # Agent might accept plan, history, and message
        result = agent.modify(current_plan, history, req.message)
        # Assuming result contains {"reply": str, "updated_plan": dict, "diff": dict}
        if isinstance(result, str):
            result = json.loads(result)
            
        reply = result.get("reply", "行程已更新")
        updated_plan = result.get("updated_plan", current_plan)
        diff = result.get("diff", {})
        
        # Save updated history
        history.append({"role": "user", "content": req.message})
        history.append({"role": "assistant", "content": reply})
        if len(history) > 20:
            history = history[-20:]
            
        session.current_plan_json = json.dumps(updated_plan, ensure_ascii=False)
        session.messages_json = json.dumps(history, ensure_ascii=False)
        db.commit()
        
        return {
            "success": True,
            "reply": reply,
            "updated_plan": updated_plan,
            "diff": diff
        }
    except Exception as e:
        # Fallback to mock on error
        updated_plan, reply, diff = mock_modify_plan(current_plan, req.message)
        
        history.append({"role": "user", "content": req.message})
        history.append({"role": "assistant", "content": reply})
        
        session.current_plan_json = json.dumps(updated_plan, ensure_ascii=False)
        session.messages_json = json.dumps(history, ensure_ascii=False)
        db.commit()
        
        return {
            "success": True,
            "reply": reply,
            "updated_plan": updated_plan,
            "diff": diff,
            "warning": f"Agent modifier failed, fallback to mock used. Error: {str(e)}"
        }
