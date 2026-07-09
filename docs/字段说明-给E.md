# 字段说明(给前端成员 E)

> **目标读者**:成员 E(写 `frontend/components/*.py` Streamlit 组件时查字段)
> **4 个核心组件的字段映射** + 3 个 demo 用例的 Plan 示例

---

## 1. 核心字段总览

Plan 响应(后端 `PlanAgent.plan()` 返回,详 `docs/API-internal.md`):
```
plan
├── trip_summary      (行程元信息)
├── weather           (每日天气)
├── days              (每日活动列表) ← 渲染主体
│   └── items         (每天的活动项) ← 卡片/时间轴/地图都从这里取
├── budget_breakdown  (预算分配)
└── tips              (温馨提示)
```

---

## 2. 时间轴组件(按天展开 + 时间排序)

**数据源**:`plan.days[i]`(i = 0, 1, 2, ...)

**关键字段**:
| 字段 | 类型 | 用途 |
|---|---|---|
| `days[i].day` | int | "Day 1" / "Day 2" 大标题 |
| `days[i].date` | str | "7月8日 周二" 副标题 |
| `days[i].items[].time` | str | "09:00" 左侧时间轴 |
| `days[i].items[].name` | str | "黄鹤楼" 标题 |
| `days[i].items[].duration_hours` | float | "2h" 时长 |
| `days[i].items[].cost` | float | "¥80" 价格 |
| `days[i].items[].type` | str | emoji 前缀(景点/餐饮/住宿/交通) |
| `days[i].day_cost` | float | "当日花费:¥340" |
| `days[i].items[].description` | str | 鼠标悬停 tooltip |

**建议样式**(方案 §2.2 P0-3):
```
📅 Day 1 (7月8日 · 周二)
08:30 - 09:30  🚄 武汉站 → 黄鹤楼 (地铁 30min)
10:00 - 12:00  🏯 黄鹤楼          (¥80)
12:30 - 13:30  🍜 户部巷午餐      (¥50)
...
💰 当日花费:¥340
```

**实现提示**:用 `st.columns([1, 4])` 左侧时间右侧内容,中间用 `st.divider()`。

---

## 3. 卡片墙组件(3D 翻转效果)

**数据源**:`plan.days[i].items[].name` 去重后(或自己用 `search_attractions` 返回的原始景点)

**关键字段**:
| 字段 | 类型 | 用途 |
|---|---|---|
| `items[].name` | str | 卡片标题(正面) |
| `items[].emoji` | str | 卡片大 emoji 占位图(可加 image) |
| `items[].description` | str | 卡片背面描述 |
| `items[].cost` | float | "¥80" 标签 |
| `items[].duration_hours` | float | "2h" 游览时长 |
| `items[].lat` / `items[].lng` | float | 地图标点(给 map 组件复用) |

**建议样式**(方案 §2.2 P0-4):
```
+------------------------+
| 🏯                    |  ← 正面(emoji + 名字)
| 黄鹤楼                 |
| ⭐ 4.5  |  ¥80  |  2h |
+------------------------+
| 江南三大名楼之首        |  ← 背面(悬停翻转)
| 🏷️ 历史  📍 武昌       |
+------------------------+
```

**实现提示**:
- `streamlit-card` 1.0.2 包(方案 §4.1 技术栈已锁)
- 正面/背面用 `st.session_state` 控制翻转动画
- 评分字段 `rating` 来自 `search_attractions` 工具返回,**不是** `items` 字段里(需要 E 在卡片渲染时去重景点后,自己从 `tools.search_attractions.invoke()` 拿)

---

## 4. 预算饼图组件(plotly.express.pie)

**数据源**:`plan.budget_breakdown` (dict)

**关键字段**:
| 字段 | 类型 | 用途 |
|---|---|---|
| `budget_breakdown["交通"]` | float | 饼图第一块 |
| `budget_breakdown["住宿"]` | float | 饼图第二块 |
| `budget_breakdown["门票"]` | float | 饼图第三块 |
| `budget_breakdown["餐饮"]` | float | 饼图第四块 |
| `budget_breakdown["其他"]` | float | 饼图第五块 |

**键名严格固定**!不要翻译,不要改大小写。后端 Pydantic `BudgetBreakdown` 校验。

**示例**:
```python
import plotly.express as px
fig = px.pie(
    values=list(plan["budget_breakdown"].values()),
    names=list(plan["budget_breakdown"].keys()),
    title="预算分配",
)
st.plotly_chart(fig)
```

**每日花费对比**(可选 P0-6):用 `days[i].day_cost` 画条形图。
```python
day_costs = [d["day_cost"] for d in plan["days"]]
day_labels = [f"Day {d['day']}" for d in plan["days"]]
st.bar_chart({"花费": day_costs}, x=day_labels)
```

**超支提示**:`sum(plan["budget_breakdown"].values()) > plan["trip_summary"]["total_budget"] * 1.05` 时显示红色 warning。

---

## 5. 地图组件(高德 JS API)

**数据源**:`plan.days[i].items[].lat/lng`(用经纬度去重得到景点列表)

**关键字段**:
| 字段 | 类型 | 用途 |
|---|---|---|
| `items[].lat` | float | 纬度(必填,无值跳过) |
| `items[].lng` | float | 经度(必填,无值跳过) |
| `items[].name` | str | marker 标题 |
| `items[].description` | str | 信息窗体 content |
| `items[].cost` | float | "门票:¥80" 标签 |
| `items[].duration_hours` | float | "游览:2h" 标签 |
| `items[].time` | str | marker tooltip("09:00 黄鹤楼") |

**建议样式**(方案 §2.2 P0-7):
```python
import streamlit.components.v1 as components
amap_html = f"""
<script src="https://webapi.amap.com/maps?v=2.0&key={amap_key}"></script>
<div id="map" style="width:100%; height:600px;"></div>
<script>
  var map = new AMap.Map('map', {{zoom: 11, center: [114.3055, 30.5928]}});
  var attractions = {json.dumps(extract_attractions(plan))};
  attractions.forEach((a, i) => {{
    var marker = new AMap.Marker({{
      position: [a.lng, a.lat],
      title: a.name,
    }});
    map.add(marker);
  }});
  // 绘制路线连线
  var path = attractions.map(a => [a.lng, a.lat]);
  var polyline = new AMap.Polyline({{path: path, strokeColor: "#FF33FF", strokeWeight: 6, strokeStyle: "dashed"}});
  map.add(polyline);
</script>
"""
components.html(amap_html, height=620)
```

**注意**:`extract_attractions()` 函数从 `plan.days[*].items[*]` 去重提取,按出现顺序保留即可。

---

## 6. 对话框组件(多轮修改)

**数据源**:`plan` + 后端 `/api/chat` 返回

**请求**:
```python
payload = {
    "session_id": st.session_state.session_id,  # 后端会话 ID
    "message": user_input,
    "current_plan": current_plan,  # 前端缓存的最新 plan
}
response = requests.post(API_URL + "/api/chat", json=payload).json()
```

**响应**(参考 `docs/API-internal.md` §2.2):
```python
new_plan = response["updated_plan"]    # 更新前端 state
diff = response["diff"]                # 提示用户改了哪个 day
reply = response["reply"]              # 显示在聊天框
```

---

## 7. 3 个 demo 用例的 Plan JSON 示例

**Demo 1:武汉 2 天 800 元学生党**
- `data/mock_plans/wuhan_3day_1500.json`(`_fallback_plan` 终极兜底,但 days 不匹配)
- 集成测试 `test_integration.py::test_demo_case[武汉-2-800-...]` 包含完整 sample

**Demo 2:西安 3 天 3500 元亲子**
- `data/mock_plans/xian_3day_3500.json`(本仓库,完整数据)
- 包含兵马俑/博物馆/大雁塔/华清宫/骊山

**Demo 3:成都 2 天 2000 元朋友**
- `data/mock_plans/chengdu_2day_2000.json`(本仓库,完整数据)
- 包含宽窄巷子/锦里/火锅/熊猫基地/春熙路

**前端调试时**:从 `data/mock_plans/` 读 JSON,直接当 mock plan 用即可。

---

## 8. 字段类型速查表

| 字段路径 | Python 类型 | Streamlit 渲染建议 |
|---|---|---|
| `plan.trip_summary.city` | str | `st.subheader` |
| `plan.days[i].day` | int | "Day 1" 拼接 |
| `plan.days[i].items[].name` | str | `st.markdown` 或卡片标题 |
| `plan.days[i].items[].time` | str | `st.code` 等宽字体 |
| `plan.days[i].items[].cost` | float | `f"¥{cost:.0f}"` |
| `plan.days[i].items[].lat` | float | 地图 marker |
| `plan.budget_breakdown.{k}` | float | 饼图/条形图 |
| `plan.tips` | list[str] | `for tip in tips: st.info(tip)` |

---

**版本**:v0.3.0(第三轮)
**维护者**:成员 A
**对应 commit**:`feat/agent-minimal-loop-v2` 分支
