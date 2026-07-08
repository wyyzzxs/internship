# 答辩稿 — 成员 A(技术架构,1.5min)

> **时长**:严格 1.5min,约 600 字
> **结构**:5 段(架构 / Agent 主循环 / 8 工具分工 / 多轮+反思 / 兜底)+ 评委高频问题预案

---

## 1. 架构三层(10s)

我们的项目分三层:

- **前端**:Streamlit 跑 `frontend/app.py`,收集用户需求(城市/天数/预算/偏好)
- **后端**:FastAPI 跑 `backend/main.py`,接收 `/api/plan` 请求,转给 PlanAgent
- **数据**:ChromaDB 存 60-80 个景点向量 + SQLite 存会话历史 + JSON 存静态数据

整体调用链:**前端 → FastAPI → PlanAgent → 8 个工具 → LLM + RAG**

---

## 2. PlanAgent 主循环(20s)

核心是 `PlanAgent._call_llm_with_tools_loop`,while 循环最多 10 次:

1. 拼 messages(系统提示词 + 用户需求)
2. 调 LLM,看返不返 `tool_calls`
3. **有 tool_calls** → 执行工具,把结果塞回 messages,继续循环
4. **无 tool_calls** → LLM 给出最终 JSON,提取 + Pydantic 校验
5. 拿不到合法 JSON 就重试或 fallback

LangChain `@tool` 装饰器从函数 docstring **自动生成 JSON Schema**,LLM 看 schema 决定调不调、调哪个。

---

## 3. 8 个工具的分工(15s)

按方案 §8.3,我们 6 个成员严格分工:

- **A(我)**:负责 self_reflect 反思工具 + Agent 编排
- **B**:负责 7 个 FC 工具(search_attractions / get_weather / calculate_budget / optimize_route / search_nearby_poi / generate_checklist / generate_travel_diary)

**关键约束**:A 设计工具的接口契约(JSON Schema),B 写真实实现。这样我们 6 个人能并行开发,合并时不冲突。

---

## 4. 多轮对话 + 反思机制(20s)

**多轮对话**(P1-4):用户说"把第 2 天下午改成湖北省博物馆",前端调 `/api/chat`,后端:
1. 从 MemorySessionStore 拿最近 10 轮历史
2. 把"当前行程 + 用户指令"喂给 LLM
3. LLM 给增量修改,后端 Pydantic 校验返 `updated_plan`(完整 plan,不是 diff)
4. 写回 session_store

**反思机制**(P2-7):主循环拿到 plan 后,调 self_reflect 工具自查,**最多 3 次**:
- 第一次发现"超支 200 元"→ 规则修复,缩放 budget_breakdown 到 95% 预算
- 第二次发现"景点不足 1 天"→ append 免费景点补全
- 第三次如果还不通过,**强制返回**防止死循环

---

## 5. 兜底策略(15s)

LLM 不可用时:
1. DashScope 429/超时 → 指数退避重试 3 次
2. 仍失败 → `_fallback_plan()` 读 `data/mock_plans/{city}.json` 3 城演示数据轮换
3. 都没了 → 内存最小 plan 占位,前端照样能渲染
4. 返 `success: false` + 中文友好 message("AI 服务暂不可用,已为您展示兜底行程")

工具异常(模拟和风 API 挂、高德 API 挂)→ 主循环 try/except,工具返 `{"error": ..., "fallback": ...}`,跳过这个工具,**不让整个 plan 崩**。

---

## 评委高频问题预案(从 A 视角)

### Q1:"为什么不支持更多城市?"
> 时间约束,选了 6 个武汉/西安/成都/北京/杭州/厦门。**架构上无城市数限制**,加城市只要在 `data/cities.json` + `data/attractions.json` 加数据 + 跑 `build_chroma_index.py` 重建向量库即可。**前端表单**用下拉选,加新城市只要改 `cities.json`。

### Q2:"Agent 怎么知道调用哪个工具?"
> LangChain `@tool` 装饰器从函数 docstring 的 `Args:` 段**自动生成 OpenAI function-calling schema**。LLM 看 schema 决定调不调。Prompt 里有"按需调用工具"引导,大模型有原生 tool selection 能力,比硬编码路由灵活。

### Q3:"怎么避免编造景点?"
> 3 层防护:
> 1. Prompt 约束:"景点只从工具检索结果中选,禁止编造"
> 2. 后端 Pydantic 校验,景点名不在 mock 数据里就触发 fallback
> 3. 数据源真实:60-80 个景点从马蜂窝/携程手整理进 ChromaDB,**不是 LLM 编的**

### Q4:"多轮对话上下文爆炸怎么办?"
> MemorySessionStore 用 `last_n=10` 截断,只保留最近 10 轮。早期消息丢弃,模型不爆 token。

### Q5:"反思机制会不会死循环?"
> 三道防线:
> 1. reflect-loop **最多 3 次**
> 2. 主循环 **最多 10 次** LLM 调用
> 3. 工具内部 catch 异常返友好 dict,不抛错打断主流程
> 即使反射 3 次都失败,也强制返回当前 plan,前端照常展示。

---

## 演示台词提示

- **多轮**:用户输入"把第 2 天下午改成湖北省博物馆" → 系统 2 秒内返新 plan
- **反思**:故意构造超支场景,看 reflect-loop 自动修复
- **兜底**:断网时 LLM 不可用,3 秒后系统自动展示兜底行程,前端 UI 仍然完整

---

**版本**:v0.3.0(第三轮)
**维护者**:成员 A
**预计演讲时长**:1min 30s ~ 2min(念稿速度可调)
