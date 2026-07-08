import os
import json
from langchain_community.vectorstores import Chroma
from backend.rag.embedder import get_embeddings
from backend.config import settings

class TouristRetriever:
    def __init__(self, persist_dir=None):
        if not persist_dir:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            persist_dir = os.path.join(base_dir, "chroma_db")
        
        self.persist_dir = persist_dir
        self.embeddings = get_embeddings()
        
        # Load ChromaDB only if it has been built or we are running in non-mock
        # (Otherwise it might fail if directory doesn't exist, we will handle it gracefully)
        self.vectorstore = None
        if os.path.exists(persist_dir):
            try:
                self.vectorstore = Chroma(
                    persist_directory=persist_dir,
                    embedding_function=self.embeddings
                )
            except Exception:
                pass

    def search(self, city: str, tags: list[str] = None, top_k: int = 8) -> list[dict]:
        # If vectorstore is initialized and we have indexed documents, use it
        if self.vectorstore:
            try:
                query = f"{city} 景点"
                if tags:
                    query += " " + " ".join(tags)
                    
                docs = self.vectorstore.similarity_search(
                    query,
                    k=top_k,
                    filter={"city": city}
                )
                
                results = []
                for doc in docs:
                    meta = doc.metadata.copy()
                    # Deserialize fields
                    if "tags" in meta and isinstance(meta["tags"], str):
                        meta["tags"] = meta["tags"].split(",") if meta["tags"] else []
                    if "recommended_season" in meta and isinstance(meta["recommended_season"], str):
                        meta["recommended_season"] = meta["recommended_season"].split(",") if meta["recommended_season"] else []
                    if "suitable_for" in meta and isinstance(meta["suitable_for"], str):
                        meta["suitable_for"] = meta["suitable_for"].split(",") if meta["suitable_for"] else []
                        
                    results.append(meta)
                if results:
                    return results
            except Exception:
                pass
                
        # JSON fallback if ChromaDB fails, doesn't exist, or is empty
        return self._json_fallback(city, tags, top_k)

    def _json_fallback(self, city: str, tags: list[str], top_k: int) -> list[dict]:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        attr_file = os.path.join(base_dir, "data", "attractions.json")
        
        if not os.path.exists(attr_file):
            return []
            
        try:
            with open(attr_file, "r", encoding="utf-8") as f:
                all_attrs = json.load(f).get("attractions", [])
        except Exception:
            return []
            
        city_attrs = [a for a in all_attrs if a.get("city") == city]
        if not city_attrs:
            return []
            
        # Score based on tag matches
        def get_score(attr):
            score = 0
            attr_tags = attr.get("tags", [])
            if tags:
                for t in tags:
                    if t in attr_tags or t in attr.get("category", ""):
                        score += 2
            score += attr.get("rating", 4.0) * 0.1
            return score
            
        sorted_attrs = sorted(city_attrs, key=get_score, reverse=True)
        return sorted_attrs[:top_k]

def retrieve_answer(city: str, question: str) -> tuple[str, list[str]]:
    retriever = TouristRetriever()
    
    # 1. Retrieve relevant attractions
    docs = []
    references = []
    if retriever.vectorstore:
        try:
            docs = retriever.vectorstore.similarity_search(
                f"{city} {question}",
                k=3,
                filter={"city": city}
            )
            references = [doc.metadata.get("name") for doc in docs if doc.metadata.get("name")]
        except Exception:
            pass
            
    if not references:
        # Fallback references
        fallback_attrs = retriever.search(city, top_k=3)
        references = [a.get("name") for a in fallback_attrs if a.get("name")]

    # 2. Return mock or LLM response
    if settings.USE_MOCK or not settings.DASHCOPE_API_KEY or settings.DASHCOPE_API_KEY.startswith("sk-请填"):
        from backend.api.qa import mock_qa
        answer, refs = mock_qa(city, question)
        return answer, list(set(refs + references))[:3]
        
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=settings.DASHCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        
        context = ""
        if docs:
            context = "\n\n".join([f"【{doc.metadata.get('name')}】：\n{doc.page_content}" for doc in docs])
        else:
            # Fallback text
            context = "暂无具体背景景点资料。"
            
        prompt = f"""你是一个智能旅游助手。请根据以下关于【{city}】的景点/美食等背景资料，回答用户的问题。
        
背景资料：
{context}

用户问题：
{question}

要求：
1. 你的回答必须基于背景资料，如果背景资料没有提到相关信息，你可以适当扩展，但要声明哪些是背景资料有的。
2. 回答要条理清晰，使用 Markdown 格式。
3. 给出实用性强的旅游建议。
"""
        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "You are a helpful travel assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        answer = response.choices[0].message.content
        return answer, references
    except Exception as e:
        from backend.api.qa import mock_qa
        answer, refs = mock_qa(city, question)
        return answer, list(set(refs + references))[:3]
