from sqlalchemy import Column, String, Integer, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class SessionModel(Base):
    __tablename__ = "sessions"

    session_id = Column(String(100), primary_key=True, index=True)
    user_id = Column(String(100), nullable=True)
    current_plan_json = Column(Text, nullable=True)
    messages_json = Column(Text, nullable=True)  # Store serialized chat history
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SavedPlanModel(Base):
    __tablename__ = "saved_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), index=True)
    title = Column(String(200), nullable=False)
    plan_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class SharedPlanModel(Base):
    __tablename__ = "shared_plans"

    share_id = Column(String(100), primary_key=True, index=True)
    plan_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
