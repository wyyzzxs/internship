# 内部接口文档(A 给 D)

> **目标读者**:成员 D(写 `backend/api/*.py` FastAPI 路由时直接抄字段名)
> **字段名严格对齐方案 §7.2**,不创造新名字,不省略必填字段。

---

## 1. POST /api/plan(生成行程)

### 1.1 请求体
```python
{
    "city": "武汉",          # str, 必填, 6 个预设城市之一
    "days": 3,                # int, 必填, 1-7
    "start_date": "2025-07-08",  # str, 必填, YYYY-MM-DD
    "budget": 1500,           # float, 必填, > 0
    "preferences": ["历史", "美食"],  # list[str], 可选, 默认 []
    "people": "情侣",         # str, 可选, 默认 "情侣"
    "departure": "武汉",      # str, 可选, 默认 "武汉"
    "session_id": null        # str, 可选, 留空表示新会话
}
```

### 1.2 成功响应(200)
**完全对齐方案 §7.2 PlanResponse + Plan 嵌套结构**:

> ⚠️ **session_id 字段**:第三轮起,后端 `plan()` 用 `ses_{YYYYMMDD}_{uuid4前8位}` 自动生成
> (消除"文档说返,代码不返"的冲突)。D 接管 FastAPI 后可以忽略这个字段,
> 自己用 `request.cookies.get("session_id")` 之类的方式生成。

```python
{
    "success": true,
    "session_id": "ses_20250708_a1b2c3d4",  # str | null,后端自动生成
    "plan": {
        "trip_summary": {
            "city": "武汉",              # str
            "days": 3,                    # int
            "start_date": "2025-07-08",  # str
            "end_date": "2025-07-10",    # str
            "total_budget": 1500.0,      # float
            "people": "情侣"              # str
        },
        "weather": [
            {
                "date": "2025-07-08",      # str
                "weather": "晴",          # str
                "temp_high": 33.0,        # float
                "temp_low": 26.0,         # float
                "suggestion": "适合户外",  # str
                "wind": null,             # str | null
                "icon": null              # str | null
            }
        ],
        "days": [
            {
                "day": 1,                # int
                "date": "2025-07-08",    # str
                "items": [
                    {
                        "time": "09:00",           # str, HH:MM
                        "type": "景点",              # str, 6 选 1: 景点/餐饮/住宿/交通/门票/其他
                        "name": "黄鹤楼",            # str
                        "duration_hours": 2.0,      # float
                        "cost": 80.0,                # float
                        "lat": 30.5438,              # float | null
                        "lng": 114.3055,             # float | null
                        "description": "江南三大名楼之首",  # str | null
                        "emoji": "🏯"                # str | null
                    }
                ],
                "day_cost": 250.0,        # float
                "weather": null           # WeatherDay | null
            }
        ],
        "budget_breakdown": {
            "交通": 200.0,    # 5 个键,顺序与方案一致
            "住宿": 600.0,
            "门票": 80.0,
            "餐饮": 330.0,
            "其他": 60.0
        },
        "tips": ["周一黄鹤楼闭馆,本次行程周二开始不受影响"]  # list[str]
    },
    "tools_called": ["search_attractions", "get_weather", "calculate_budget"],  # list[str]
    "fallback": false,         # bool
    "error": null              # str | null
}
```

### 1.3 失败响应
- **400**:`{"success": false, "error": "city 必填", "fallback": false}`
- **422**:`{"success": false, "error": "days 必须是 1-7", "fallback": false}`
- **500**:`{"success": false, "error": "AI 服务暂不可用(DashScope 超时/限流),已为您展示兜底行程。请稍后重试或联系管理员。", "fallback": true, "plan": {...兜底 plan...}}`

---

## 2. POST /api/chat(多轮对话修改)

### 2.1 请求体
```python
{
    "session_id": "ses_20250708_001",   # str, 必填
    "message": "把第 2 天下午改成湖北省博物馆",   # str, 必填
    "current_plan": {                     # dict, 可选(前端缓存的当前 plan)
        "trip_summary": {...},
        "days": [...]
    }
}
```

### 2.2 成功响应(200)
```python
{
    "reply": "已将 Day 2 末尾活动从「汉口江滩」改为「湖北省博物馆」。",  # str
    "updated_plan": {                     # 完整 Plan dict(不是 diff patch!)
        "trip_summary": {...},
        "weather": [...],
        "days": [...],
        "budget_breakdown": {...},
        "tips": [...]
    },
    "diff": {
        "day": 2,                         # int | null
        "removed": "汉口江滩",            # str | null
        "added": "湖北省博物馆"           # str | null
    }
}
```

**关键约束**:`updated_plan` 必须是**完整 Plan JSON**(Pydantic `Plan` 可校验),**不是 diff patch**。D 存数据库时直接覆盖 `sessions.current_plan_json`。

---

## 3. PlanAgent 内部方法(供 D 写路由时直接调用)

### 3.1 `plan(request: dict) -> dict`
- 输入:见 §1.1
- 输出:见 §1.2
- 错误处理:成功 → success=True,失败 → success=False + error(中文友好)+ fallback plan

### 3.2 `modify(session_id: str, message: str, current_plan: dict) -> dict`
- 输入:见 §2.1
- 输出:见 §2.2
- 内部自动调 `session_store.append_message()` + `save_plan()`

### 3.3 `reflect(plan: dict, request: dict) -> dict`
- 输入:plan dict + 原始 request dict
- 输出:`{"is_satisfied": bool, "issues": [str, ...], "suggestion": str}`
- **D 一般不需要直接调**,PlanAgent 主循环内部已用

---

## 4. SessionStore 接口(供 D 写 `backend/db/sqlite.py` 时对齐字段)

```python
from backend.db.memory_store import MemorySessionStore

store = MemorySessionStore()  # 内存版,D 接管后换 sqlite:///sessions.db

# 4 个核心方法
store.get_or_create(session_id: str, user_id: str = "") -> dict
store.save_plan(session_id: str, plan: dict) -> None
store.append_message(session_id: str, message: dict) -> None
store.get_history(session_id: str, last_n: int = 10) -> list[dict]

# 2 个辅助方法
store.get_plan(session_id: str) -> dict | None
store.clear(session_id: str) -> None
```

**字段名严格对齐方案 §3.5 sessions 表**:
- `session_id` (TEXT PK)
- `user_id` (TEXT)
- `current_plan_json` (TEXT, JSON 字符串)
- `messages_json` (TEXT, JSON 数组字符串)
- `created_at` / `updated_at` (TIMESTAMP)

**D 接管时**:把 `create_engine` URL 换成真实 SQLite 路径即可,字段/接口零修改。

---

## 5. 错误码总表(对齐方案 §7.2)

| 状态码 | 触发条件 | 响应字段 |
|---|---|---|
| 200 | 成功 | `success: true` |
| 400 | 参数缺失/无效 | `error: "请求参数错误:xxx"` |
| 422 | 类型/范围错误 | `error: "请求参数校验失败:字段 days 必须是 1-7"` |
| 500 | LLM 不可达 | `success: false`, `error: "AI 服务暂不可用..."`, `fallback: true`, `plan: {...}` |
| 503 | 上游不可用 | 同 500 |

---

## 6. 测试命令

```powershell
# ⚠️ PowerShell 行续行陷阱:命令末尾不要加 `\`
# 否则 `--cov-report=term-missing\` 会被 PowerShell 当行续行,
# 实际传 pytest 的是 `--cov-report=term-missing"`(带引号)→ 报错

# 单元测试(56 个,含 3 城 mock 回归测试)
$env:MOCK_LLM = "true"
& "E:\myapp\anaconda\envs\internship\python.exe" -m pytest backend/tests/ -v

# 集成测试(3 个 demo + 2 兜底,5 用例)
& "E:\myapp\anaconda\envs\internship\python.exe" -m pytest backend/tests/test_integration.py -v

# 全部 + 覆盖率
& "E:\myapp\anaconda\envs\internship\python.exe" -m pytest backend/tests/ --cov=backend --cov-report=term-missing
```

---

**版本**:v0.3.0(第三轮)
**维护者**:成员 A
**对应 commit**:`feat/agent-minimal-loop-v2` 分支
