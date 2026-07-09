# AI 智能旅游规划师

> 中南财经政法大学 AI Agent 暑期短期实习 · 结课项目

## 项目简介

基于 AI Agent + RAG + Function Calling 的智能旅游规划系统,输入目的地/天数/预算/偏好,自动生成带时间轴、地图路线、景点卡片、预算饼图的可交互攻略,支持对话式修改。

## 技术栈

- **LLM**:qwen-plus(DashScope 兼容模式)
- **Embedding**:text-embedding-v3
- **向量库**:ChromaDB
- **前端**:Streamlit + 高德地图 JS API + Pyecharts
- **后端**:FastAPI
- **Agent**:LangChain @tool + 手写循环
- **数据库**:SQLite

## 快速开始

```bash
# 1. 克隆仓库
git clone <repo>
cd internship

# 2. 创建虚拟环境
python -m venv venv
# Windows
.\venv\Scripts\Activate.ps1
# macOS/Linux
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env,填入 DASHSCOPE_API_KEY

# 5. 构建 ChromaDB 索引(首次必须)
python scripts/build_chroma_index.py

# 6. 启动后端
uvicorn backend.main:app --reload --port 8000

# 7. 启动前端(新终端)
streamlit run frontend/app.py --server.port 8501
```

访问 http://localhost:8501

## 成员 B 功能

- 实时天气 `/api/weather`:有 `QWEATHER_API_KEY` 时走和风天气,无 Key 时走本地缓存兜底;和风新版凭据可同时配置 `QWEATHER_API_HOST`。
- 周边 POI `/api/nearby-poi`:支持餐厅、酒店、景点、厕所;有高德 Web 服务 Key 时走真实 POI,无 Key 时走本地数据。
- 旅行 Checklist `/api/checklist`:根据行程、天气、人群生成 Markdown checkbox 清单。

## 项目结构

```
internship/
├── data/              # 静态数据(景点/美食/天气)
├── chroma_db/         # 向量库(运行时生成)
├── backend/           # FastAPI 后端
│   ├── agents/        # Agent 层
│   ├── tools/         # 7 个 FC 工具
│   ├── rag/           # RAG 检索
│   ├── db/            # SQLite
│   └── api/           # 路由
├── frontend/          # Streamlit 前端
│   ├── components/    # UI 组件
│   └── utils/         # 工具
├── scripts/           # 启动脚本
├── docs/              # 文档
└── tests/             # 测试
```

## 文档

- [项目方案](项目方案.md)
- [API 文档](API.md)
- [答辩稿](答辩稿.md)

## 团队

6 人小组,分工见项目方案 §9。
