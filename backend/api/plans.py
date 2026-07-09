import json
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from backend.db.sqlite import get_db
from backend.db.models import SavedPlanModel

router = APIRouter()

class SavedPlanCreate(BaseModel):
    user_id: str = Field(default="default_user", example="superju454-create")
    title: str = Field(..., example="武汉3天2晚经典游")
    plan: Dict[str, Any] = Field(...)

class SavedPlanResponse(BaseModel):
    id: int
    user_id: str
    title: str
    plan: Dict[str, Any]
    created_at: str

    model_config = {
        "from_attributes": True
    }

@router.post("/plans", status_code=status.HTTP_201_CREATED)
def save_plan(req: SavedPlanCreate, db: Session = Depends(get_db)):
    try:
        db_plan = SavedPlanModel(
            user_id=req.user_id,
            title=req.title,
            plan_json=json.dumps(req.plan, ensure_ascii=False)
        )
        db.add(db_plan)
        db.commit()
        db.refresh(db_plan)
        return {
            "success": True,
            "id": db_plan.id,
            "message": "Itinerary saved successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save plan: {str(e)}")

@router.get("/plans")
def list_plans(user_id: str = "default_user", db: Session = Depends(get_db)):
    try:
        plans = db.query(SavedPlanModel).filter(SavedPlanModel.user_id == user_id).order_by(SavedPlanModel.created_at.desc()).all()
        result = []
        for p in plans:
            result.append({
                "id": p.id,
                "user_id": p.user_id,
                "title": p.title,
                "plan": json.loads(p.plan_json) if p.plan_json else {},
                "created_at": p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else ""
            })
        return {
            "success": True,
            "count": len(result),
            "plans": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list plans: {str(e)}")

@router.delete("/plans/{plan_id}")
def delete_plan(plan_id: int, user_id: str = "default_user", db: Session = Depends(get_db)):
    db_plan = db.query(SavedPlanModel).filter(SavedPlanModel.id == plan_id, SavedPlanModel.user_id == user_id).first()
    if not db_plan:
        raise HTTPException(status_code=404, detail=f"Saved plan {plan_id} not found for user {user_id}")
        
    try:
        db.delete(db_plan)
        db.commit()
        return {
            "success": True,
            "message": f"Itinerary {plan_id} deleted successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete plan: {str(e)}")
