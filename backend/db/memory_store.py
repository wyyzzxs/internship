"""MemorySessionStore - SQLAlchemy 内存会话存储(本轮临时)。

**职责边界**(项目方案 §8.3 / §9.2):
- 完整 SQLite 持久化 + `/api/chat` 路由由**成员 D**负责
- 本文件是 A 临时写的**内存版**占位实现,字段名严格对齐方案 §3.5,
  D 接管时只需把 `create_engine` 的 URL 改成真实 SQLite 路径,
  字段名/接口都不用改

字段名严格对齐方案 §3.5 sessions 表:
- session_id        TEXT PRIMARY KEY
- user_id           TEXT
- current_plan_json TEXT
- messages_json     TEXT         -- JSON 数组字符串
- created_at        TIMESTAMP
- updated_at        TIMESTAMP

接口(4 个方法):
- get_or_create(session_id)        -> dict
- save_plan(session_id, plan)      -> None
- append_message(session_id, msg)  -> None
- get_history(session_id, last_n)  -> list[dict]

**SQLAlchemy 兼容性**:用 `declarative_base` 经典接口(兼容 1.x/2.x),
D 接管后想升级到 2.x 风格可以无痛切换。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, String, Text, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger("backend.db.memory_store")

Base = declarative_base()


class Session(Base):  # type: ignore[misc, valid-type]
    """ORM 模型 - 字段对齐方案 §3.5 sessions 表。"""

    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True)
    user_id = Column(String, default="")
    current_plan_json = Column(Text, default="")
    messages_json = Column(Text, default="[]")  # JSON 数组字符串
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class MemorySessionStore:
    """SQLAlchemy 内存 store - 字段名与 D 的 SQLite store 一致。

    Args:
        db_url: SQLAlchemy URL,默认 `sqlite:///:memory:`(进程内临时)
                D 接管后可换 `sqlite:///sessions.db`
    """

    def __init__(self, db_url: str = "sqlite:///:memory:") -> None:
        # check_same_thread=False 解决 SQLAlchemy + SQLite 在 Windows 多线程锁
        # 内存模式下也安全,毕竟每个 store 是独立实例
        connect_args: dict[str, Any] = {}
        if db_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        self.engine = create_engine(db_url, connect_args=connect_args)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

    # ------------------------------------------------------------------ #
    # CRUD
    # ------------------------------------------------------------------ #
    def get_or_create(self, session_id: str, user_id: str = "") -> dict:
        """取会话,不存在则创建空会话。返回 dict(便于调用方处理)。"""
        with self.SessionLocal() as db:
            row = db.get(Session, session_id)
            if row is None:
                row = Session(
                    session_id=session_id,
                    user_id=user_id,
                    current_plan_json="",
                    messages_json="[]",
                )
                db.add(row)
                db.commit()
                db.refresh(row)
            return self._row_to_dict(row)

    def save_plan(self, session_id: str, plan: dict) -> None:
        """保存当前行程(PlanResponse.plan 序列化 JSON 字符串)。"""
        try:
            with self.SessionLocal() as db:
                row = db.get(Session, session_id)
                if row is None:
                    row = Session(
                        session_id=session_id,
                        current_plan_json=json.dumps(plan, ensure_ascii=False),
                        messages_json="[]",
                    )
                    db.add(row)
                else:
                    row.current_plan_json = json.dumps(plan, ensure_ascii=False)
                    row.updated_at = datetime.now()
                db.commit()
        except SQLAlchemyError as exc:
            logger.warning("save_plan 失败(%s): %s", session_id, exc)

    def append_message(self, session_id: str, message: dict) -> None:
        """追加一条消息到会话历史。

        message 形如 {"role": "user", "content": "..."} 或
        {"role": "assistant", "content": "..."}。
        """
        try:
            with self.SessionLocal() as db:
                row = db.get(Session, session_id)
                if row is None:
                    row = Session(
                        session_id=session_id,
                        current_plan_json="",
                        messages_json=json.dumps([message], ensure_ascii=False),
                    )
                    db.add(row)
                else:
                    msgs = json.loads(row.messages_json or "[]")
                    msgs.append(message)
                    row.messages_json = json.dumps(msgs, ensure_ascii=False)
                    row.updated_at = datetime.now()
                db.commit()
        except SQLAlchemyError as exc:
            logger.warning("append_message 失败(%s): %s", session_id, exc)

    def get_history(self, session_id: str, last_n: int = 10) -> list[dict]:
        """取最近 last_n 条消息(默认 10,避免上下文爆炸,见方案 §14 风险 10)。"""
        try:
            with self.SessionLocal() as db:
                row = db.get(Session, session_id)
                if row is None or not row.messages_json:
                    return []
                msgs = json.loads(row.messages_json)
                if not isinstance(msgs, list):
                    return []
                return msgs[-last_n:]
        except (SQLAlchemyError, json.JSONDecodeError) as exc:
            logger.warning("get_history 失败(%s): %s", session_id, exc)
            return []

    # ------------------------------------------------------------------ #
    # 辅助
    # ------------------------------------------------------------------ #
    def get_plan(self, session_id: str) -> dict | None:
        """取当前行程(已反序列化的 dict),不存在则 None。"""
        try:
            with self.SessionLocal() as db:
                row = db.get(Session, session_id)
                if row is None or not row.current_plan_json:
                    return None
                return json.loads(row.current_plan_json)
        except (SQLAlchemyError, json.JSONDecodeError) as exc:
            logger.warning("get_plan 失败(%s): %s", session_id, exc)
            return None

    def clear(self, session_id: str) -> None:
        """清空会话(测试用)。"""
        try:
            with self.SessionLocal() as db:
                row = db.get(Session, session_id)
                if row is not None:
                    row.current_plan_json = ""
                    row.messages_json = "[]"
                    row.updated_at = datetime.now()
                    db.commit()
        except SQLAlchemyError as exc:
            logger.warning("clear 失败(%s): %s", session_id, exc)

    @staticmethod
    def _row_to_dict(row: Session) -> dict:
        return {
            "session_id": row.session_id,
            "user_id": row.user_id,
            "current_plan_json": row.current_plan_json,
            "messages_json": row.messages_json,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }


__all__ = ["Base", "MemorySessionStore", "Session"]
