"""配置层 - 读取 .env,暴露全局 Config。

**A / D 职责边界**(项目方案 §8.3 / §12.4):
- **成员 A 阶段**(本文件当前实现):LLM 相关字段 + PROJECT_ROOT,供 LLMClient / PlanAgent 使用。
- **成员 D 接管后**应补全 / 接管:DB 路径、API 端口、CORS、SQLite、日志目录、Weather 字段等。
- 本文件字段全为类属性,模块加载时一次性确定。

设计原则:
1. 字段全部在模块加载时一次性读取(类属性,无副作用)。
2. MOCK_LLM/MOCK_WEATHER 在对应 Key 缺失时默认为 true(项目方案 §12.4)。
3. 路径全部基于 PROJECT_ROOT 计算,不依赖 cwd。
"""
from __future__ import annotations

import os
from pathlib import Path

# 项目根 = backend 的父目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 加载 .env(若存在)。本地 .env 不入库,但开发环境必备。
# 使用 override=False 防止覆盖已设置的系统环境变量(CI 优先)。
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv(PROJECT_ROOT / ".env", override=False)
except ImportError:  # pragma: no cover - dotenv 不可用时静默
    pass


def _bool(value: str | None, default: bool = False) -> bool:
    """宽松的布尔解析:1/true/yes/y/on → True;其他非空 → False。"""
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


class Config:
    """全局配置 - 所有字段在模块加载时一次性确定,后续不应运行时修改。"""

    # ---- LLM ----
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "").strip()
    # Key 缺失时默认 mock;否则看 MOCK_LLM 是否被显式开启
    _mock_default = not bool(os.getenv("DASHSCOPE_API_KEY", "").strip())
    MOCK_LLM: bool = _bool(os.getenv("MOCK_LLM"), default=_mock_default)
    LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen-plus")
    LLM_BASE_URL: str = os.getenv(
        "LLM_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "3"))

    # ---- Weather ----
    QWEATHER_API_KEY: str = os.getenv("QWEATHER_API_KEY", "").strip()
    _weather_default = not bool(os.getenv("QWEATHER_API_KEY", "").strip())
    MOCK_WEATHER: bool = _bool(os.getenv("MOCK_WEATHER"), default=_weather_default)

    # ---- App ----
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = _bool(os.getenv("DEBUG"), default=True)
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # ---- 路径 ----
    PROJECT_ROOT: Path = PROJECT_ROOT
    DATA_DIR: Path = PROJECT_ROOT / "data"
    MOCK_PLANS_DIR: Path = DATA_DIR / "mock_plans"
    LOGS_DIR: Path = PROJECT_ROOT / "logs"

    # ---- Agent ----
    AGENT_MAX_ITERATIONS: int = int(os.getenv("AGENT_MAX_ITERATIONS", "10"))
    AGENT_LLM_TEMPERATURE: float = float(os.getenv("AGENT_LLM_TEMPERATURE", "0.3"))


__all__ = ["Config", "PROJECT_ROOT"]