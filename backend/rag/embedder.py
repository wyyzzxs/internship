import os
import random
from langchain_core.embeddings import Embeddings
from langchain_community.embeddings import DashScopeEmbeddings
from backend.config import settings

class MockEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            # Deterministic pseudo-random vector based on text content hash
            state = sum(ord(c) for c in text)
            random.seed(state)
            vectors.append([random.random() for _ in range(1536)])
        return vectors

    def embed_query(self, text: str) -> list[float]:
        state = sum(ord(c) for c in text)
        random.seed(state)
        return [random.random() for _ in range(1536)]

def get_embeddings():
    if settings.USE_MOCK or not settings.DASHCOPE_API_KEY or settings.DASHCOPE_API_KEY.startswith("sk-请填"):
        return MockEmbeddings()
    try:
        return DashScopeEmbeddings(
            model="text-embedding-v3",
            dashscope_api_key=settings.DASHCOPE_API_KEY
        )
    except Exception:
        # Fallback to mock if API initialization fails
        return MockEmbeddings()
