import os
import json
from langchain_core.documents import Document

def load_attractions(file_path: str = None) -> list[Document]:
    if not file_path:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        file_path = os.path.join(base_dir, "data", "attractions.json")
        
    if not os.path.exists(file_path):
        return []
        
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    docs = []
    for attr in data.get("attractions", []):
        name = attr.get("name", "")
        city = attr.get("city", "")
        category = attr.get("category", "")
        tags = attr.get("tags", [])
        description = attr.get("description", "")
        suitable_for = attr.get("suitable_for", [])
        open_hours = attr.get("open_hours", "")
        address = attr.get("address", "")
        ticket_price = attr.get("ticket_price", 0)
        
        # Serialize fields for Chroma metadata (which only accepts str, int, float, bool)
        metadata = {
            "id": attr.get("id", ""),
            "city": city,
            "name": name,
            "category": category,
            "tags": ",".join(tags),
            "ticket_price": float(ticket_price),
            "lat": float(attr.get("lat", 0.0)),
            "lng": float(attr.get("lng", 0.0)),
            "image_emoji": attr.get("image_emoji", ""),
            "rating": float(attr.get("rating", 4.0)),
            "open_hours": open_hours,
            "address": address,
            "best_duration_hours": float(attr.get("best_duration_hours", 2.0)),
            "recommended_season": ",".join(attr.get("recommended_season", [])),
            "suitable_for": ",".join(suitable_for),
            "tips": attr.get("tips", "")
        }
        
        content = (
            f"景点名称: {name}\n"
            f"城市: {city}\n"
            f"类别: {category}\n"
            f"标签: {', '.join(tags)}\n"
            f"介绍: {description}\n"
            f"适合人群: {', '.join(suitable_for)}\n"
            f"开放时间: {open_hours}\n"
            f"地址: {address}"
        )
        
        docs.append(Document(page_content=content, metadata=metadata))
        
    return docs
