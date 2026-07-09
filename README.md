# AI 智能旅游规划师

> 中南财经政法大学 AI Agent 暑期实习 · 结课项目

## 项目简介

基于 AI Agent + RAG + Function Calling 的智能旅游规划系统,输入目的地/天数/预算/偏好,自动生成带时间轴、地图路线、景点卡片、预算饼图的可交互攻略,支持对话式修改。

## 技术栈

- **LLM**:qwen-plus(DashScope 兼容 OpenAI 模式)
- **Embedding**:text-embedding-v3
- **向量库**:ChromaDB
- **前端**:Streamlit **+ Flask**(双前端,功能一致,风格不同)
- **后端**:FastAPI + Uvicorn
- **地图**:高德 JS API 2.0 + Pyecharts
- **Agent**:LangChain `@tool` + 手写主循环 + 自反思(self-reflect)
- **数据库**:SQLite(会话历史 / 收藏行程 / 分享链接)

## 快速开始

### 1. 克隆 & 进入项目

```bash
git clone <repo>
cd internship
```

### 2. 创建虚拟环境并安装依赖

需要 Python 3.11.x。

```bash
python -m venv venv
# Windows
.\venv\Scripts\Activate.ps1
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# Windows
copy .env.example .env
# macOS / Linux
cp .env.example .env
```

然后编辑 `.env`,至少填入:

| Key | 必填 | 说明 |
| --- | :---: | --- |
| `DASHSCOPE_API_KEY` | ✅ | 阿里云百炼 API Key,免费注册 https://bailian.console.aliyun.com/ |
| `QWEATHER_API_KEY` | ✅ | 和风天气 API Key,免费注册 https://console.qweather.com/ |
| `QWEATHER_API_HOST` | ⬜ | 和风新版控制台的私有域名(如 `https://xxxx.qweatherapi.com`),老 key 留空即可 |
| `AMAP_JS_API_KEY` | ✅ | 高德地图 Web 端 JS API Key,https://lbs.amap.com/ |
| `AMAP_WEB_SERVICE_KEY` | ⬜ | 高德 Web 服务 API Key(POI 周边搜索);留空则用本地数据 |

完整字段说明见 `.env.example`。

### 4. 构建 ChromaDB 索引(首次必须)

```bash
python scripts/build_chroma_index.py
```

### 5. 启动服务(开三个终端)

```bash
# 终端 1 — 后端 (FastAPI :8000)
uvicorn backend.main:app --reload --port 8000

# 终端 2 — Streamlit 前端 (:8501)
streamlit run frontend/app.py --server.port 8501

# 终端 3 — Flask 前端 (:8502,功能与 Streamlit 一致,暗色卡片 + 3D 翻转)
python frontend_flask/app.py
```

启动后访问:

- **Streamlit**:`http://localhost:8501`
- **Flask**:`http://localhost:8502`
- **API 文档**:`http://localhost:8000/docs`

### 6. 一键停掉所有服务

```bash
# Windows (PowerShell)
Get-NetTCPConnection -LocalPort 8000,8501,8502 -State Listen `
  | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

## API 端点

后端统一前缀 `/api`,主要端点:

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 健康检查,返回 LLM / 天气等组件状态 |
| POST | `/plan` | 生成完整行程(LLM + 工具调用 + 自反思) |
| POST | `/chat` | 对话式修改行程(基于当前 plan + 历史) |
| GET | `/weather?city=...&start_date=...&days=...` | 真实天气(和风 API,有 key 时) |
| GET | `/nearby-poi?lat=...&lng=...&poi_type=...` | 周边 POI(高德 API,有 key 时) |
| POST | `/checklist` | 生成 Markdown 旅行清单 |
| GET / POST / DELETE | `/plans` | 收藏 / 列出 / 删除行程 |
| POST / GET | `/share` | 创建 / 获取分享链接 |
| POST | `/qa` | 城市知识问答(规则 + 可选 RAG) |

## 对外特性

- **实时天气 `/api/weather`**:`QWEATHER_API_KEY` + `QWEATHER_API_HOST` 都配置时调真实和风天气;否则降级到 `data/weather_cache.json` 本地缓存。
- **周边 POI `/api/nearby-poi`**:有 `AMAP_WEB_SERVICE_KEY` 时调高德真实 POI;否则从本地 `data/restaurants.json` / `hotels.json` / `attractions.json` 按距离筛选。
- **旅行 Checklist `/api/checklist`**:根据行程、天气、人群生成 Markdown checkbox 清单(雨天自动加雨具,亲子自动加儿童药品)。

## 项目结构

```
internship/
├── backend/                  # FastAPI 后端
│   ├── agents/               # Agent 主循环 + 自反思
│   ├── tools/                # 7 个 LangChain @tool(weather/poi/budget/...)
│   ├── rag/                  # Chroma 检索
│   ├── db/                   # SQLite 模型与初始化
│   ├── schemas/              # Pydantic Schema
│   ├── api/                  # FastAPI 路由
│   ├── llm/                  # DashScope 兼容模式客户端
│   └── config.py             # 集中配置
├── frontend/                 # Streamlit 前端(主题/组件/工具)
├── frontend_flask/           # Flask 前端(暗色主题,卡片翻转)
│   ├── templates/            # Jinja2 模板
│   ├── static/               # CSS / JS / 图片
│   ├── app.py                # Flask 入口
│   ├── helpers.py            # 后端 API 客户端 + 模板渲染辅助
│   └── plan_store.py         # 服务端行程缓存(session cookie 兜底)
├── data/                     # 静态数据(景点/美食/天气)
│   ├── attractions.json
│   ├── cities.json
│   ├── weather_cache.json    # 和风 API 不可用时的兜底
│   └── mock_plans/           # LLM 不可用时的演示行程
├── chroma_db/                # 向量库(运行时生成,已 gitignore)
├── scripts/
│   ├── build_chroma_index.py # 索引构建
│   ├── start_backend.sh      # Linux 启动脚本
│   └── start_frontend.sh     # Linux 启动脚本
├── tests/                    # pytest
├── docs/                     # 设计文档
├── slides/                   # 答辩 PPT(已 gitignore)
├── .env.example              # 环境变量模板
├── requirements.txt
└── README.md
```

## 文档

- [项目方案](项目方案.md)
- [API 文档](API.md)
- [答辩稿](答辩稿.md)

## 团队

6 人小组,分工见项目方案 §9。

## 常见问题

- **Q:LLM 返回超时 / 429 怎么办?**
  A:系统内置指数退避重试 3 次;若仍失败,会自动 fallback 到 `data/mock_plans/wuhan_3day_1500.json` 兜底行程。

- **Q:Flask 前端的 `cache_id` 每次刷新都变?**
  A:这是设计:Flask session cookie 默认 4KB,大型 plan JSON 单独写到 `.flask_plan_cache/{cache_id}/current.json`。换浏览器或清 cookie 会重置,正常。

- **Q:对话说"想吃食堂"没反应?**
  A:确认 `.env` 里 `USE_MOCK=false`,然后查看后端日志,正常应该会调 DashScope;如果看到 `MOCK 找到演示数据`,说明走了 mock fallback。

- **Q:ChromaDB 报 `Failed to send telemetry event`?**
  A:这是 ChromaDB 0.5.3 与新版 posthog SDK 的兼容问题,不影响功能,可忽略。