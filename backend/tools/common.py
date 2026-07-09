"""Shared helpers for backend tools."""

from __future__ import annotations

import json
import math
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
except Exception:
    pass


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@lru_cache(maxsize=16)
def load_json(filename: str) -> dict[str, Any]:
    path = DATA_DIR / filename
    return json.loads(path.read_text(encoding="utf-8"))


def tool_decorator(*args: Any, **kwargs: Any):
    """Return LangChain's @tool when available, otherwise a no-op decorator."""

    try:
        from langchain_core.tools import tool

        return tool(*args, **kwargs)
    except Exception:
        if args and callable(args[0]) and not kwargs:
            return args[0]

        def _decorator(func):
            return func

        return _decorator


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371.0088
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

