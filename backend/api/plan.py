import os
import json
import uuid
import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.config import settings
from backend.db.sqlite import get_db
from backend.db.models import SessionModel
from backend.api.weather import get_mock_weather

router = APIRouter()

class PlanRequest(BaseModel):
    city: str = Field(..., example="武汉")
    days: int = Field(..., ge=1, le=7, example=3)
    start_date: str = Field(..., example="2025-07-08")
    budget: float = Field(..., ge=0, example=1500.0)
    preferences: List[str] = Field(default=[], example=["历史", "美食"])
    people: str = Field(..., example="情侣")
    departure: str = Field(default="武汉", example="武汉")

def generate_mock_itinerary(req: PlanRequest):
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    
    # 1. Load Attractions
    attr_file = os.path.join(base_dir, "data", "attractions.json")
    all_attrs = []
    if os.path.exists(attr_file):
        try:
            with open(attr_file, "r", encoding="utf-8") as f:
                all_attrs = json.load(f).get("attractions", [])
        except Exception:
            pass
            
    # Filter by city
    city_attrs = [a for a in all_attrs if a.get("city") == req.city]
    if not city_attrs:
        # Fallback to any city
        city_attrs = [a for a in all_attrs if a.get("city") == "武汉"]
    if not city_attrs:
        # Hard fallback dummy
        city_attrs = [{
            "id": "dummy_1", "name": "核心景区", "ticket_price": 50, "best_duration_hours": 2, 
            "description": "城市代表性景点", "image_emoji": "🌲", "lat": 30.5, "lng": 114.3, "tags": ["自然"]
        }]
        
    # Sort by preference score
    def get_score(attr):
        score = 0
        attr_tags = attr.get("tags", [])
        for pref in req.preferences:
            if pref in attr_tags or pref in attr.get("category", ""):
                score += 2
        # Slight boost for rating
        score += attr.get("rating", 4.0) * 0.1
        return score
        
    sorted_attrs = sorted(city_attrs, key=get_score, reverse=True)
    
    # 2. Load Restaurants and Hotels
    rest_file = os.path.join(base_dir, "data", "restaurants.json")
    hotel_file = os.path.join(base_dir, "data", "hotels.json")
    
    restaurants = []
    hotels = []
    
    if os.path.exists(rest_file):
        try:
            with open(rest_file, "r", encoding="utf-8") as f:
                restaurants = [r for r in json.load(f).get("restaurants", []) if r.get("city") == req.city]
        except:
            pass
    if os.path.exists(hotel_file):
        try:
            with open(hotel_file, "r", encoding="utf-8") as f:
                hotels = [h for h in json.load(f).get("hotels", []) if h.get("city") == req.city]
        except:
            pass
            
    # Fill defaults if empty
    if not restaurants:
        restaurants = [{"name": f"{req.city}特色餐饮店", "avg_cost_per_person": 50, "must_try": ["特色招牌菜"]}]
    if not hotels:
        hotels = [{"name": f"{req.city}品质舒适酒店", "price_per_night": 200}]
        
    # 3. Create Daily Schedule
    days_list = []
    attr_index = 0
    rest_index = 0
    hotel_choice = hotels[0]
    
    try:
        start_date = datetime.datetime.strptime(req.start_date, "%Y-%m-%d")
    except:
        start_date = datetime.datetime.today()
        
    total_ticket_cost = 0
    total_dining_cost = 0
    
    for d in range(1, req.days + 1):
        current_date_str = (start_date + datetime.timedelta(days=d-1)).strftime("%Y-%m-%d")
        items = []
        day_cost = 0
        
        # Morning Attraction
        if attr_index < len(sorted_attrs):
            attr = sorted_attrs[attr_index]
            attr_index += 1
            ticket = attr.get("ticket_price", 0)
            total_ticket_cost += ticket
            day_cost += ticket
            items.append({
                "time": "09:00",
                "type": "景点",
                "name": attr.get("name"),
                "duration_hours": attr.get("best_duration_hours", 2),
                "cost": ticket,
                "lat": attr.get("lat"),
                "lng": attr.get("lng"),
                "description": attr.get("description"),
                "emoji": attr.get("image_emoji", "📍")
            })
            
        # Lunch
        rest = restaurants[rest_index % len(restaurants)]
        rest_index += 1
        dining_cost = rest.get("avg_cost_per_person", 50)
        total_dining_cost += dining_cost
        day_cost += dining_cost
        items.append({
            "time": "12:00",
            "type": "餐饮",
            "name": rest.get("name"),
            "duration_hours": 1.5,
            "cost": dining_cost,
            "lat": rest.get("lat", items[-1]["lat"] if items else 30.5),
            "lng": rest.get("lng", items[-1]["lng"] if items else 114.3),
            "description": f"推荐品尝：{', '.join(rest.get('must_try', []))}",
            "emoji": "🍜"
        })
        
        # Afternoon Attraction
        if attr_index < len(sorted_attrs):
            attr = sorted_attrs[attr_index]
            attr_index += 1
            ticket = attr.get("ticket_price", 0)
            total_ticket_cost += ticket
            day_cost += ticket
            items.append({
                "time": "14:30",
                "type": "景点",
                "name": attr.get("name"),
                "duration_hours": attr.get("best_duration_hours", 2),
                "cost": ticket,
                "lat": attr.get("lat"),
                "lng": attr.get("lng"),
                "description": attr.get("description"),
                "emoji": attr.get("image_emoji", "📍")
            })
            
        # Dinner
        rest = restaurants[rest_index % len(restaurants)]
        rest_index += 1
        dining_cost = rest.get("avg_cost_per_person", 60)
        total_dining_cost += dining_cost
        day_cost += dining_cost
        items.append({
            "time": "18:00",
            "type": "餐饮",
            "name": rest.get("name"),
            "duration_hours": 1.5,
            "cost": dining_cost,
            "lat": rest.get("lat", items[-1]["lat"] if items else 30.5),
            "lng": rest.get("lng", items[-1]["lng"] if items else 114.3),
            "description": f"享受当地晚间美食",
            "emoji": "🍲"
        })
        
        # Evening Hotel/Rest
        if d < req.days:
            hotel_cost = hotel_choice.get("price_per_night", 200)
            day_cost += hotel_cost
            items.append({
                "time": "20:00",
                "type": "住宿",
                "name": hotel_choice.get("name"),
                "duration_hours": 12,
                "cost": hotel_cost,
                "lat": hotel_choice.get("lat", items[-1]["lat"] if items else 30.5),
                "lng": hotel_choice.get("lng", items[-1]["lng"] if items else 114.3),
                "description": f"办理入住并休息",
                "emoji": "🏨"
            })
            
        days_list.append({
            "day": d,
            "date": current_date_str,
            "items": items,
            "day_cost": day_cost
        })
        
    # 4. Budget Calculation
    transport_cost = 100 + 50 * req.days  # Mock transport
    accommodation_cost = hotel_choice.get("price_per_night", 200) * (req.days - 1) if req.days > 1 else 0
    other_cost = 50
    
    budget_breakdown = {
        "交通": transport_cost,
        "住宿": accommodation_cost,
        "门票": total_ticket_cost,
        "餐饮": total_dining_cost,
        "其他": other_cost
    }
    
    total_calc = sum(budget_breakdown.values())
    
    # Simple check and adjust to budget if we are heavily over
    if total_calc > req.budget * 1.1:
        # Scale down hotel or transport
        budget_breakdown["住宿"] = max(100 * (req.days - 1), budget_breakdown["住宿"] * 0.7)
        budget_breakdown["餐饮"] = max(40 * req.days, budget_breakdown["餐饮"] * 0.8)
        total_calc = sum(budget_breakdown.values())

    # Get weather
    weather_data = get_mock_weather(req.city, req.start_date, req.days)
    
    # Tips
    tips = [
        f"建议提前预订{req.city}段大交通门票及酒店",
        "部分热门景点需要提前3-7天在线预约，请注意提前锁定入场名额"
    ]
    if any("雨" in w.get("weather", "") for w in weather_data):
        tips.append("行程期间可能有雨，请随身携带雨具")
        
    end_date_str = (start_date + datetime.timedelta(days=req.days-1)).strftime("%Y-%m-%d")
    
    plan_data = {
        "trip_summary": {
            "city": req.city,
            "days": req.days,
            "start_date": req.start_date,
            "end_date": end_date_str,
            "total_budget": req.budget,
            "people": req.people
        },
        "weather": weather_data,
        "days": days_list,
        "budget_breakdown": budget_breakdown,
        "tips": tips
    }
    
    return plan_data

@router.post("/plan")
def create_plan(req: PlanRequest, db: Session = Depends(get_db)):
    session_id = f"ses_{uuid.uuid4().hex[:12]}"
    
    if settings.USE_MOCK:
        plan = generate_mock_itinerary(req)
        # Store in DB
        db_session = SessionModel(
            session_id=session_id,
            user_id=None,
            current_plan_json=json.dumps(plan, ensure_ascii=False),
            messages_json=json.dumps([], ensure_ascii=False)
        )
        db.add(db_session)
        db.commit()
        
        return {
            "success": True,
            "session_id": session_id,
            "plan": plan,
            "tools_called": ["search_attractions", "get_weather", "calculate_budget", "optimize_route"]
        }
        
    # Non-mock: Invoke Member A's PlanAgent
    try:
        from backend.agents.plan_agent import PlanAgent
        # PlanAgent might be structured as a class with a plan method
        agent = PlanAgent()
        # Request dict
        request_dict = req.model_dump()
        plan = agent.plan(request_dict)
        if isinstance(plan, str):
            plan = json.loads(plan)
            
        # Store in DB
        db_session = SessionModel(
            session_id=session_id,
            user_id=None,
            current_plan_json=json.dumps(plan, ensure_ascii=False),
            messages_json=json.dumps([], ensure_ascii=False)
        )
        db.add(db_session)
        db.commit()
        
        return {
            "success": True,
            "session_id": session_id,
            "plan": plan,
            "tools_called": ["search_attractions", "get_weather", "calculate_budget", "optimize_route"]
        }
    except Exception as e:
        # Fallback to mock and log error
        plan = generate_mock_itinerary(req)
        # Store in DB
        db_session = SessionModel(
            session_id=session_id,
            user_id=None,
            current_plan_json=json.dumps(plan, ensure_ascii=False),
            messages_json=json.dumps([], ensure_ascii=False)
        )
        db.add(db_session)
        db.commit()
        
        return {
            "success": True,
            "session_id": session_id,
            "plan": plan,
            "tools_called": ["search_attractions", "get_weather", "calculate_budget_fallback"],
            "warning": f"Agent failed, fallback to mock used. Error: {str(e)}"
        }
