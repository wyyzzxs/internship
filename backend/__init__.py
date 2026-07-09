"""AI 智能旅游规划师 - 后端包。

**成员 A 职责**:backend 顶层 + Config + LLM Client + Agent + Schemas
**其他模块**(api / db / rag / tools / frontend)由对应成员负责。

**全局 logger**(第三轮扩展):
- import 本包即调用 `setup_logging()` 配好全局 logger
- 文件 handler 写 `logs/backend.log`(`RotatingFileHandler` 5MB × 3 备份)
- 控制台 handler 输出 INFO 以上
- 测试用 `monkeypatch` 替换 `LOG_FILE` 路径或 `tmp_path` 隔离
"""
from __future__ import annotations

import logging
import os
import sys

__version__ = "0.1.0"

# 兼容旧版 setup_logging(level: str) 签名
# 新版 _logging.setup_logging() 收 level=int 数字,我们做适配
_LEVEL_MAP: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def setup_logging(level: str | int | None = None) -> None:
    """配置项目根 logger(兼容旧版字符串签名,内部转 _logging.setup_logging)。

    Args:
        level: 日志级别(DEBUG/INFO/WARNING/ERROR 字符串或 int),默认读 LOG_LEVEL/INFO
    """
    # 解析 level
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")
    if isinstance(level, str):
        level_int = _LEVEL_MAP.get(level.upper(), logging.INFO)
    else:
        level_int = level

    # 惰性 import 避免循环
    from backend.log_setup import setup_logging as _setup

    _setup(level=level_int)


# 导入即生效,允许模块单独执行时也有 logger
setup_logging()

__all__ = ["__version__", "setup_logging"]
