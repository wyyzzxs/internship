import os
import json
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/cities")
def get_cities():
    # Find data/cities.json in the repository root
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    cities_file = os.path.join(base_dir, "data", "cities.json")
    
    if not os.path.exists(cities_file):
        raise HTTPException(status_code=404, detail="cities.json file not found")
        
    try:
        with open(cities_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        cities = []
        for c in data.get("cities", []):
            cities.append({
                "code": c.get("id"),
                "name": c.get("name"),
                "lat": c.get("lat"),
                "lng": c.get("lng"),
                "tags": c.get("tags", [])
            })
            
        return {
            "success": True,
            "cities": cities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading cities data: {str(e)}")
