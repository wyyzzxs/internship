from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from backend.db.sqlite import init_db
from backend.api import health, cities, tags, weather, plan, chat, plans, share, qa

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

app = FastAPI(
    title="AI Travel Planner API",
    description="Backend API for AI Travel Planner including itinerary generation, database storage, and QA",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all or specify ["http://localhost:8501"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database initialization on startup
@app.on_event("startup")
def on_startup():
    logger.info("Initializing SQLite database...")
    init_db()
    logger.info("Database initialized successfully.")

# Global Exception Handler
@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception occurred: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal Server Error",
            "detail": str(exc)
        }
    )

# Include Routers
app.include_router(health.router, prefix="/api", tags=["System"])
app.include_router(cities.router, prefix="/api", tags=["Metadata"])
app.include_router(tags.router, prefix="/api", tags=["Metadata"])
app.include_router(weather.router, prefix="/api", tags=["Services"])
app.include_router(plan.router, prefix="/api", tags=["Core"])
app.include_router(chat.router, prefix="/api", tags=["Core"])
app.include_router(plans.router, prefix="/api", tags=["User Collections"])
app.include_router(share.router, prefix="/api", tags=["Sharing"])
app.include_router(qa.router, prefix="/api", tags=["QA"])

@app.get("/")
def read_root():
    return {
        "message": "Welcome to AI Travel Planner API. Go to /docs for Swagger documentation."
    }
