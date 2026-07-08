"""全局 logger 配置(第三轮新增)。

**职责范围**:本文件是 A 编写的工程化基建,不属于 D / 任何成员的范围。

设计:
- `RotatingFileHandler` 写 `logs/backend.log`(5MB × 3 备份,UTF-8)
- `StreamHandler` 控制台输出
- 统一时间戳 + 级别 + 名字格式
- 幂等:多次 import 不会重复加 handler

测试:
- 测试用 `tmp_path` fixture 临时改 cwd,避免污染真实 `logs/`
- 或用 `monkeypatch` 替换 `LOG_FILE` 路径
"""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

# 全局 logger 名字
LOGGER_NAME = "backend"

# 默认日志目录(相对 cwd,生产用绝对路径可由调用方覆盖)
DEFAULT_LOG_DIR = Path("logs")
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / "backend.log"

# 日志格式
_FILE_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_CONSOLE_FORMAT = "[%(levelname)s] %(name)s: %(message)s"


def setup_logging(
    log_file: Path | str | None = None,
    level: int = logging.INFO,
    max_bytes: int = 5 * 1024 * 1024,  # 5MB
    backup_count: int = 3,
    force: bool = False,
) -> logging.Logger:
    """配置全局 logger(幂等)。

    Args:
        log_file: 日志文件路径,默认 `logs/backend.log`(相对 cwd)
        level: 日志级别,默认 INFO
        max_bytes: 单文件最大字节,默认 5MB
        backup_count: 备份文件数,默认 3
        force: True 时强制重新配置(测试用),默认 False 幂等

    Returns:
        配好的 logger
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)

    # 幂等:已有 handler 且不强制 → 直接返回
    if logger.handlers and not force:
        return logger

    # 强制模式:清掉旧 handler
    if force:
        for h in list(logger.handlers):
            logger.removeHandler(h)

    # 文件 handler
    log_path = Path(log_file) if log_file else DEFAULT_LOG_FILE
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        fh.setLevel(level)
        fh.setFormatter(logging.Formatter(_FILE_FORMAT))
        logger.addHandler(fh)
    except OSError as exc:  # pragma: no cover - 权限不足等
        # 日志写不进文件不影响主流程,只警告
        print(f"[WARNING] 无法创建日志文件 {log_path}: {exc}")

    # 控制台 handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(logging.Formatter(_CONSOLE_FORMAT))
    logger.addHandler(ch)

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """便捷获取 logger。

    Args:
        name: 子模块名,默认 LOGGER_NAME;传子模块名(如 "agents.plan_agent")自动继承

    Returns:
        配好的 logger(如果父 logger 未配,自动调用 setup_logging)
    """
    parent = logging.getLogger(LOGGER_NAME)
    if not parent.handlers:
        setup_logging()
    if name is None or name == LOGGER_NAME:
        return parent
    return logging.getLogger(f"{LOGGER_NAME}.{name}")


__all__ = ["LOGGER_NAME", "get_logger", "setup_logging"]
