"""FastAPI entrypoint for AI Travel Planner."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.travel import router as travel_router


app = FastAPI(
    title="AI 智能旅游规划师",
    description="Travel planner backend with weather, POI and checklist tools.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(travel_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "AI 智能旅游规划师后端已启动", "docs": "/docs"}

