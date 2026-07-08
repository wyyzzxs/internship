"""AI 智能旅游规划师 - 后端包

成员 A 职责:backend 顶层 + Config + LLM Client + Agent + Schemas
其他模块(api / db / rag / tools / frontend)由对应成员负责。
"""
from __future__ import annotations

import logging
import os
import sys

__version__ = "0.1.0"

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_logging(level: str | None = None) -> None:
    """配置项目根 logger,幂等可重入。

    Args:
        level: 日志级别字符串 (DEBUG/INFO/WARNING/ERROR);默认读 LOG_LEVEL,缺省 INFO。
    """
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    root = logging.getLogger("backend")
    root.setLevel(log_level)
    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        root.addHandler(handler)
        root.propagate = False


# 导入即生效,允许模块单独执行时也有 logger
setup_logging()

__all__ = ["__version__", "setup_logging"]