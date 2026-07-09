import uuid
import json
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel

from backend.db.sqlite import get_db
from backend.db.models import SharedPlanModel

router = APIRouter()

class ShareCreateRequest(BaseModel):
    plan: Dict[str, Any]

@router.post("/share")
def create_share_link(req: ShareCreateRequest, db: Session = Depends(get_db)):
    # Generate unique 8-char short code
    share_id = f"sh_{uuid.uuid4().hex[:8]}"
    
    try:
        db_share = SharedPlanModel(
            share_id=share_id,
            plan_json=json.dumps(req.plan, ensure_ascii=False)
        )
        db.add(db_share)
        db.commit()
        
        # Format a Streamlit frontend URL for sharing
        share_url = f"http://localhost:8501/?share={share_id}"
        return {
            "success": True,
            "share_id": share_id,
            "share_url": share_url
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to generate share link: {str(e)}")

@router.get("/share/{share_id}")
def get_shared_plan(share_id: str, db: Session = Depends(get_db)):
    db_share = db.query(SharedPlanModel).filter(SharedPlanModel.share_id == share_id).first()
    if not db_share:
        raise HTTPException(status_code=404, detail=f"Shared plan {share_id} not found")
        
    try:
        plan = json.loads(db_share.plan_json)
        return {
            "success": True,
            "share_id": share_id,
            "plan": plan
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse shared plan: {str(e)}")
