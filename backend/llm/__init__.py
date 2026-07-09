"""LLM 客户端封装层(成员 A 负责)。"""
from backend.llm.llm_client import LLMClient, LLMUnavailable

__all__ = ["LLMClient", "LLMUnavailable"]