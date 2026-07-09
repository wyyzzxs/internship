"""FastAPI entrypoint for AI Travel Planner."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api import chat, plan, plans, qa, share
from backend.api.travel import router as travel_router
from backend.db.sqlite import init_db

# 注:backend.api 下原 health/cities/tags/weather 是早期 mock 版,
# 未被 include,会和 travel_router 的同名接口冲突,已删除。

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

app = FastAPI(
    title="AI 智能旅游规划师 API",
    description="Backend API for itinerary generation, travel tools, storage, sharing, and QA.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    logger.info("Initializing SQLite database...")
    init_db()
    logger.info("Database initialized successfully.")


@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Global exception occurred: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal Server Error", "detail": str(exc)},
    )


# B/C helper endpoints: /api/health, /api/cities, /api/tags, /api/weather,
# /api/nearby-poi, /api/checklist.
app.include_router(travel_router)

# D endpoints: /api/plan, /api/chat, /api/plans, /api/share, /api/qa.
app.include_router(plan.router, prefix="/api", tags=["Core"])
app.include_router(chat.router, prefix="/api", tags=["Core"])
app.include_router(plans.router, prefix="/api", tags=["User Collections"])
app.include_router(share.router, prefix="/api", tags=["Sharing"])
app.include_router(qa.router, prefix="/api", tags=["QA"])


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "AI 智能旅游规划师后端已启动", "docs": "/docs"}
