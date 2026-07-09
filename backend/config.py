"""Central configuration for the AI travel planner backend.

This module keeps the class-style Config used by member A/B/C code and also
provides a small settings compatibility object for member D's API/SQLite routes.
"""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv(PROJECT_ROOT / ".env", override=False)
except ImportError:  # pragma: no cover
    pass


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


class Config:
    # ---- LLM ----
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "").strip()
    _mock_default = not bool(DASHSCOPE_API_KEY)
    MOCK_LLM: bool = _bool(os.getenv("MOCK_LLM"), default=_mock_default)
    LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen-plus")
    LLM_BASE_URL: str = os.getenv(
        "LLM_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "3"))

    # ---- Weather / maps ----
    QWEATHER_API_KEY: str = os.getenv("QWEATHER_API_KEY", "").strip()
    HEFENG_KEY: str = os.getenv("HEFENG_KEY", QWEATHER_API_KEY).strip()
    _weather_default = not bool(QWEATHER_API_KEY or HEFENG_KEY)
    MOCK_WEATHER: bool = _bool(os.getenv("MOCK_WEATHER"), default=_weather_default)
    AMAP_JS_API_KEY: str = os.getenv("AMAP_JS_API_KEY", "").strip()
    AMAP_WEB_SERVICE_KEY: str = os.getenv("AMAP_WEB_SERVICE_KEY", "").strip()

    # ---- App ----
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = _bool(os.getenv("DEBUG"), default=True)
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # ---- Paths ----
    PROJECT_ROOT: Path = PROJECT_ROOT
    DATA_DIR: Path = PROJECT_ROOT / "data"
    MOCK_PLANS_DIR: Path = DATA_DIR / "mock_plans"
    LOGS_DIR: Path = PROJECT_ROOT / "logs"

    # ---- Agent ----
    AGENT_MAX_ITERATIONS: int = int(os.getenv("AGENT_MAX_ITERATIONS", "10"))
    AGENT_LLM_TEMPERATURE: float = float(os.getenv("AGENT_LLM_TEMPERATURE", "0.3"))

    # ---- Database / API ----
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./sessions.db")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    FRONTEND_PORT: int = int(os.getenv("FRONTEND_PORT", "8501"))


class _SettingsCompat:
    """Compatibility shim for D branch modules that import backend.config.settings."""

    DASHCOPE_API_KEY = Config.DASHSCOPE_API_KEY  # legacy alias (D 分支老代码用了 typo)
    DASHSCOPE_API_KEY = Config.DASHSCOPE_API_KEY
    AMAP_JS_API_KEY = Config.AMAP_JS_API_KEY
    AMAP_WEB_SERVICE_KEY = Config.AMAP_WEB_SERVICE_KEY
    HEFENG_KEY = Config.HEFENG_KEY
    QWEATHER_API_KEY = Config.QWEATHER_API_KEY
    USE_MOCK = Config.MOCK_LLM
    DATABASE_URL = Config.DATABASE_URL


settings = _SettingsCompat()

__all__ = ["Config", "PROJECT_ROOT", "settings"]
