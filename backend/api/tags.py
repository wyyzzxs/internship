import os
import json
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/tags")
def get_tags():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    tags_file = os.path.join(base_dir, "data", "tags.json")
    
    if not os.path.exists(tags_file):
        raise HTTPException(status_code=404, detail="tags.json file not found")
        
    try:
        with open(tags_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        emojis = {
            "history": "🏯",
            "nature": "🌊",
            "food": "🍜",
            "family": "🎡",
            "trending": "📸",
            "hidden": "🌿",
            "night": "🌃",
            "shopping": "🛍️"
        }
        
        tags = []
        for t in data.get("preference_tags", []):
            tags.append({
                "code": t.get("id"),
                "name": t.get("name"),
                "emoji": emojis.get(t.get("id"), "📍")
            })
            
        people_types = []
        people_emojis = {
            "solo": "🧳",
            "couple": "💑",
            "family": "👨‍👩‍👧",
            "friends": "👯",
            "business": "💼"
        }
        for p in data.get("people_types", []):
            people_types.append({
                "code": p.get("id"),
                "name": p.get("name"),
                "emoji": people_emojis.get(p.get("id"), "👤")
            })
            
        return {
            "success": True,
            "tags": tags,
            "people_types": people_types
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading tags data: {str(e)}")
