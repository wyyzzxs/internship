from __future__ import annotations

import random

from langchain_core.embeddings import Embeddings

from backend.config import Config

try:  # optional dependency path used when a real DashScope key is configured
    from langchain_community.embeddings import DashScopeEmbeddings
except Exception:  # pragma: no cover
    DashScopeEmbeddings = None  # type: ignore[assignment]


class MockEmbeddings(Embeddings):
    """Deterministic local embeddings for mock/offline development."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    @staticmethod
    def _vector(text: str) -> list[float]:
        state = sum(ord(char) for char in text)
        rng = random.Random(state)
        return [rng.random() for _ in range(1536)]


def get_embeddings() -> Embeddings:
    """Return DashScope embeddings when configured, otherwise local mock embeddings."""

    api_key = Config.DASHSCOPE_API_KEY.strip()
    if Config.MOCK_LLM or not api_key or api_key.startswith("sk-") or DashScopeEmbeddings is None:
        return MockEmbeddings()

    try:
        return DashScopeEmbeddings(model="text-embedding-v3", dashscope_api_key=api_key)
    except Exception:
        return MockEmbeddings()


__all__ = ["MockEmbeddings", "get_embeddings"]
