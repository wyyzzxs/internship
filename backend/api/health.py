from fastapi import APIRouter
from backend.config import settings

router = APIRouter()

@router.get("/health")
def health_check():
    # If using mock, weather api status can be simulated
    weather_status = "ok" if not settings.USE_MOCK else "degraded - using mock"
    return {
        "success": True,
        "status": "ok",
        "version": "1.0.0",
        "components": {
            "llm": "ok" if settings.DASHCOPE_API_KEY else "not_configured",
            "chromadb": "ok",
            "weather_api": weather_status
        }
    }
