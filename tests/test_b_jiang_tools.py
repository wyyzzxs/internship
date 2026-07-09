from backend.tools import generate_checklist_text, get_weather_forecast, search_nearby_poi_data


def test_weather_forecast_uses_requested_dates():
    payload = get_weather_forecast("武汉", "2026-07-08", 3)

    assert payload["city"] == "武汉"
    assert payload["days"] == 3
    assert [item["date"] for item in payload["forecast"]] == [
        "2026-07-08",
        "2026-07-09",
        "2026-07-10",
    ]
    assert payload["summary"]["source"] in {"local_cache", "qweather"}


def test_nearby_poi_finds_local_restaurants():
    payload = search_nearby_poi_data(
        lat=30.5438,
        lng=114.3055,
        radius_m=1000,
        poi_type="restaurant",
        city="武汉",
        limit=5,
    )

    assert payload["count"] >= 1
    assert payload["items"][0]["distance_m"] <= 1000
    assert payload["items"][0]["source"] in {"local_data", "amap"}


def test_checklist_adds_rain_and_people_specific_items():
    weather = {
        "forecast": [
            {"date": "2026-07-08", "weather": "小雨", "temp_high": 30, "temp_low": 24}
        ]
    }
    plan = {"itinerary": [{"items": [{"name": "黄鹤楼"}]}]}

    checklist = generate_checklist_text(plan=plan, weather=weather, people_type="亲子")

    assert "折叠伞" in checklist
    assert "儿童常用药" in checklist
    assert "黄鹤楼 门票/预约截图" in checklist

