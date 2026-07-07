# API 接口文档

> 详细字段定义见项目方案 §7。
> Swagger 文档:启动后端后访问 http://localhost:8000/docs

## 接口列表

| Method | URL | 用途 |
|---|---|---|
| POST | `/api/plan` | 生成行程 |
| POST | `/api/chat` | 多轮对话修改 |
| GET | `/api/weather` | 查询天气 |
| GET | `/api/cities` | 城市列表 |
| GET | `/api/tags` | 偏好标签 + 人群类型 |
| GET | `/api/health` | 健康检查 |
| POST | `/api/plans` | 保存行程 |
| GET | `/api/plans` | 查询已保存行程 |
| DELETE | `/api/plans/{id}` | 删除行程 |
| POST | `/api/share` | 生成分享链接 |
| POST | `/api/qa` | 城市旅行知识问答 |

## 完整请求/响应示例

详见项目方案 §7.2-§7.7。