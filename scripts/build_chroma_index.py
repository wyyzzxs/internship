import os
import shutil
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.rag.loader import load_attractions
from backend.rag.splitter import split_documents
from backend.rag.embedder import get_embeddings
from langchain_community.vectorstores import Chroma

def build_index():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    persist_dir = os.path.join(base_dir, "chroma_db")
    
    print("====== 开始构建 Chroma 向量数据库 ======")
    
    # 1. Clear old DB
    if os.path.exists(persist_dir):
        print(f"清理旧数据库目录: {persist_dir}")
        shutil.rmtree(persist_dir)
        
    # 2. Load Documents
    print("加载景点数据中...")
    docs = load_attractions()
    if not docs:
        print("[错误] 未能加载任何景点数据，请确保 data/attractions.json 存在。")
        return
    print(f"成功加载 {len(docs)} 个景点文档。")
    
    # 3. Split Documents
    print("切分文档中...")
    chunks = split_documents(docs)
    print(f"切分完成，共生成 {len(chunks)} 个切片。")
    
    # 4. Initialize Embeddings
    print("初始化嵌入函数...")
    embeddings = get_embeddings()
    print(f"使用嵌入模型: {embeddings.__class__.__name__}")
    
    # 5. Build and Persist
    print("正在写入 Chroma 并构建索引 (这可能会耗费一些时间)...")
    try:
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=persist_dir
        )
        print("索引写入成功并已完成持久化！")
        
        # 6. Verify
        print("\n====== 验证查询测试 ======")
        query = "武汉 历史 景点"
        results = vectorstore.similarity_search(query, k=3, filter={"city": "武汉"})
        print(f"查询关键字: '{query}'")
        print(f"检索到相关景点数量: {len(results)}")
        for idx, doc in enumerate(results):
            print(f" {idx+1}. {doc.metadata.get('name')} (评分: {doc.metadata.get('rating')} · 类别: {doc.metadata.get('category')})")
            
        print("\n====== 向量数据库构建成功！ ======")
    except Exception as e:
        print(f"[严重错误] 构建向量库失败: {str(e)}")

if __name__ == "__main__":
    build_index()
