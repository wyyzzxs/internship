import os
import json
import datetime
from fastapi import APIRouter, HTTPException, Query
from backend.config import settings

router = APIRouter()

def get_mock_weather(city: str, start_date_str: str, days: int):
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    weather_file = os.path.join(base_dir, "data", "weather_cache.json")
    
    if not os.path.exists(weather_file):
        # Hard fallback
        return [
            {
                "date": (datetime.datetime.strptime(start_date_str, "%Y-%m-%d") + datetime.timedelta(days=i)).strftime("%Y-%m-%d"),
                "weather": "晴" if i % 2 == 0 else "多云",
                "temp_high": 30 + i,
                "temp_low": 22 + i,
                "wind": "东风 2 级",
                "suggestion": "适合户外活动"
            } for i in range(days)
        ]
        
    try:
        with open(weather_file, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
            
        # Get city weather cache
        city_cache = cache_data.get(city) or cache_data.get("武汉")
        if not city_cache:
            raise Exception("No weather cache data")
            
        weather_list = []
        try:
            start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        except:
            start_date = datetime.datetime.today()
            
        cache_dates = list(city_cache.keys())
        for i in range(days):
            current_date_str = (start_date + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            # Map to cache dates (modulo mapping to cycle through cache values if out of range)
            cache_key = cache_dates[i % len(cache_dates)]
            day_info = city_cache[cache_key].copy()
            day_info["date"] = current_date_str
            if "suggestion" not in day_info:
                # Add default suggestion based on weather
                if "雨" in day_info.get("weather", ""):
                    day_info["suggestion"] = "有雨，建议携带雨具，适当安排室内活动"
                else:
                    day_info["suggestion"] = "天气适宜，建议安排户外游览"
            weather_list.append(day_info)
            
        return weather_list
    except Exception as e:
        # Fallback to simple hardcode
        return [
            {
                "date": (datetime.datetime.today() + datetime.timedelta(days=i)).strftime("%Y-%m-%d"),
                "weather": "多云",
                "temp_high": 28,
                "temp_low": 21,
                "wind": "微风",
                "suggestion": "天气凉爽，适宜出行"
            } for i in range(days)
        ]

@router.get("/weather")
def get_weather_api(
    city: str = Query(..., description="城市名称"),
    start_date: str = Query(..., description="开始日期 (YYYY-MM-DD)"),
    days: int = Query(3, description="天气预报天数 (1-7)")
):
    if settings.USE_MOCK:
        weather_data = get_mock_weather(city, start_date, days)
        return {
            "success": True,
            "city": city,
            "source": "cache",
            "weather": weather_data
        }
    
    # Try calling Member B's actual weather tool if available
    try:
        from backend.tools.get_weather import get_weather
        # get_weather might return a JSON string or dict
        result = get_weather(city, start_date, days)
        if isinstance(result, str):
            result = json.loads(result)
        return {
            "success": True,
            "city": city,
            "source": "api",
            "weather": result
        }
    except Exception as e:
        # Fallback to mock if API fails
        weather_data = get_mock_weather(city, start_date, days)
        return {
            "success": True,
            "city": city,
            "source": "cache_fallback",
            "weather": weather_data
        }
