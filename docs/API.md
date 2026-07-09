# API 接口文档

> 详细字段定义见项目方案 §7。
> Swagger 文档:启动后端后访问 http://localhost:8000/docs

## 接口列表

| Method | URL | 用途 |
|---|---|---|
| POST | `/api/plan` | 生成行程 |
| POST | `/api/chat` | 多轮对话修改 |
| GET | `/api/weather` | 查询天气 |
| GET | `/api/nearby-poi` | 查询景点周边 POI |
| POST | `/api/checklist` | 根据行程和天气生成旅行清单 |
| GET | `/api/cities` | 城市列表 |
| GET | `/api/tags` | 偏好标签 + 人群类型 |
| GET | `/api/health` | 健康检查 |
| POST | `/api/plans` | 保存行程 |
| GET | `/api/plans` | 查询已保存行程 |
| DELETE | `/api/plans/{id}` | 删除行程 |
| POST | `/api/share` | 生成分享链接 |
| POST | `/api/qa` | 城市旅行知识问答 |

## 完整请求/响应示例

### GET `/api/weather`

查询行程日期范围内的天气。若配置 `QWEATHER_API_KEY`,优先调用和风天气;否则自动使用 `data/weather_cache.json` 兜底。和风新版控制台若提供项目专属 API Host,还需要在 `.env` 中配置 `QWEATHER_API_HOST`。

```bash
curl "http://localhost:8000/api/weather?city=武汉&start_date=2026-07-08&days=3"
```

返回要点:
- `forecast`:每日天气、最高/最低温、降雨风险、行程建议
- `summary`:降雨天数、最高/最低温、总体建议、数据来源

### GET `/api/nearby-poi`

查询指定坐标周边餐厅、酒店、厕所或景点。若配置 `AMAP_WEB_SERVICE_KEY`,优先调用高德 Web 服务;否则使用本地餐厅/酒店/景点数据兜底。

```bash
curl "http://localhost:8000/api/nearby-poi?lat=30.5438&lng=114.3055&city=武汉&poi_type=restaurant&radius_m=1000"
```

常用 `poi_type`:
- `restaurant`:餐厅/小吃
- `hotel`:住宿
- `attraction`:附近景点
- `toilet`:厕所,需要高德 Web 服务 Key 才能返回真实数据

### POST `/api/checklist`

根据行程、天气和人群生成 Markdown checkbox 清单。

```bash
curl -X POST "http://localhost:8000/api/checklist" \
  -H "Content-Type: application/json" \
  -d '{"plan":{"itinerary":[{"items":[{"name":"黄鹤楼"}]}]},"weather":{"forecast":[{"weather":"小雨","temp_high":30,"temp_low":24}]},"people_type":"亲子"}'
```

返回:
- `format`:固定为 `markdown`
- `content`:可直接在 Streamlit 中 `st.markdown()` 展示
