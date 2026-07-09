"""服务端行程缓存 — 避免 Flask session cookie 超过 4KB。"""

from __future__ import annotations

import json
import secrets
import shutil
from copy import deepcopy
from pathlib import Path

from flask import session

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / ".flask_plan_cache"


def _ensure_dir() -> None:
    CACHE_DIR.mkdir(exist_ok=True)


def cache_id() -> str:
    if "cache_id" not in session:
        session["cache_id"] = secrets.token_hex(12)
    return session["cache_id"]


def _user_dir() -> Path:
    _ensure_dir()
    path = CACHE_DIR / cache_id()
    path.mkdir(exist_ok=True)
    return path


def _read(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def get_plan() -> dict | None:
    return _read(_user_dir() / "current.json")


def get_plan_by_cache_id(cache_id_value: str) -> dict | None:
    if not cache_id_value:
        return None
    return _read(CACHE_DIR / cache_id_value / "current.json")


def resolve_plan(cache_id_hint: str | None = None) -> dict | None:
    """优先用 session，其次用页面链接携带的 cache_id。"""
    if cache_id_hint:
        session["cache_id"] = cache_id_hint
    return get_plan()


def get_previous_plan() -> dict | None:
    return _read(_user_dir() / "previous.json")


def set_plan(plan: dict, *, track_previous: bool = False) -> None:
    user = _user_dir()
    current_path = user / "current.json"
    if track_previous:
        current = _read(current_path)
        if current:
            (user / "previous.json").write_text(
                json.dumps(current, ensure_ascii=False),
                encoding="utf-8",
            )
    current_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")


def update_plan(plan: dict) -> None:
    """对话修改：只更新当前行程，不影响对比用的 previous。"""
    (_user_dir() / "current.json").write_text(
        json.dumps(plan, ensure_ascii=False),
        encoding="utf-8",
    )


def clear_plans() -> None:
    user = _user_dir()
    if user.exists():
        shutil.rmtree(user, ignore_errors=True)
    session.pop("cache_id", None)


def trim_chat_messages(messages: list, limit: int = 30) -> list:
    return messages[-limit:] if len(messages) > limit else messages
