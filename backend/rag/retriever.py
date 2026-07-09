from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_community.vectorstores import Chroma

from backend.config import Config
from backend.rag.embedder import get_embeddings


class TouristRetriever:
    """Chroma-backed attraction retriever with JSON fallback."""

    def __init__(self, persist_dir: str | Path | None = None) -> None:
        self.persist_dir = Path(persist_dir) if persist_dir else Config.PROJECT_ROOT / "chroma_db"
        self.embeddings = get_embeddings()
        self.vectorstore = None

        if self.persist_dir.exists():
            try:
                self.vectorstore = Chroma(
                    persist_directory=str(self.persist_dir),
                    embedding_function=self.embeddings,
                )
            except Exception:
                self.vectorstore = None

    def search(self, city: str, tags: list[str] | None = None, top_k: int = 8) -> list[dict[str, Any]]:
        """Search attractions by city and optional preference tags."""

        top_k = max(1, min(int(top_k), 30))
        if self.vectorstore is not None:
            try:
                query = f"{city} attractions"
                if tags:
                    query += " " + " ".join(tags)
                docs = self.vectorstore.similarity_search(query, k=top_k, filter={"city": city})
                results = [self._normalize_metadata(doc.metadata) for doc in docs]
                if results:
                    return results
            except Exception:
                pass

        return self._json_fallback(city, tags or [], top_k)

    @staticmethod
    def _normalize_metadata(meta: dict[str, Any]) -> dict[str, Any]:
        row = dict(meta)
        for key in ("tags", "recommended_season", "suitable_for"):
            if isinstance(row.get(key), str):
                row[key] = [item for item in row[key].split(",") if item]
        return row

    def _json_fallback(self, city: str, tags: list[str], top_k: int) -> list[dict[str, Any]]:
        attr_file = Config.DATA_DIR / "attractions.json"
        if not attr_file.exists():
            return []

        try:
            with attr_file.open("r", encoding="utf-8") as file:
                attractions = json.load(file).get("attractions", [])
        except (OSError, json.JSONDecodeError):
            return []

        city_rows = [row for row in attractions if row.get("city") == city]
        if not city_rows:
            city_rows = attractions

        def score(row: dict[str, Any]) -> float:
            row_tags = row.get("tags", []) or []
            row_category = str(row.get("category", ""))
            tag_score = 0
            for tag in tags:
                if tag in row_tags or tag in row_category:
                    tag_score += 2
            return tag_score + float(row.get("rating", 4.0) or 4.0) * 0.1

        return sorted(city_rows, key=score, reverse=True)[:top_k]


def retrieve_answer(city: str, question: str) -> tuple[str, list[str]]:
    """Answer a city travel question with retrieved attraction references.

    This lightweight implementation avoids depending on unfinished API modules.
    It returns a useful mock-style answer when LLM access is unavailable.
    """

    retriever = TouristRetriever()
    references = [row.get("name") for row in retriever.search(city, top_k=3) if row.get("name")]

    if Config.MOCK_LLM or not Config.DASHSCOPE_API_KEY:
        answer = (
            f"### {city}旅行问答\n\n"
            f"你的问题是：{question}\n\n"
            "根据当前景点知识库，建议优先参考："
            + "、".join(references or ["核心景点数据"])
            + "。可结合天气、预算和同行人群再做细化安排。"
        )
        return answer, references[:3]

    try:
        from openai import OpenAI

        client = OpenAI(api_key=Config.DASHSCOPE_API_KEY, base_url=Config.LLM_BASE_URL)
        context_rows = retriever.search(city, top_k=3)
        context = "\n".join(
            f"- {row.get('name')}: {row.get('description') or row.get('tips') or ''}"
            for row in context_rows
        )
        prompt = (
            f"你是智能旅游助手。请基于以下{city}资料回答用户问题。\n"
            f"资料：\n{context}\n\n问题：{question}\n"
            "要求：回答简洁、实用，并列出参考景点。"
        )
        response = client.chat.completions.create(
            model=Config.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        return response.choices[0].message.content or "", references[:3]
    except Exception:
        answer = f"### {city}旅行问答\n\n建议参考：" + "、".join(references[:3])
        return answer, references[:3]


__all__ = ["TouristRetriever", "retrieve_answer"]
