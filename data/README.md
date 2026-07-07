# 数据目录说明

本目录存放静态数据,**所有文件可提交到 Git**(无需保密)。

## 目录内容

| 文件 | 谁负责 | 说明 |
|---|---|---|
| `cities.json` | 成员 F | 6 个城市的坐标、简介、标签 |
| `attractions.json` | 成员 F | 60-80 个景点(含 photo_spots 字段,给 P2-6 用) |
| `restaurants.json` | 成员 F | 30-40 个美食推荐 |
| `hotels.json` | 成员 F | 30-40 个酒店推荐 |
| `weather_cache.json` | 成员 F | 6 城 × 7 天天气缓存(API 失败时兜底) |
| `tags.json` | 成员 F | 6 偏好标签 + 5 人群类型 |
| `heatmap_mock.json` | 成员 F | 人流密度 mock 数据(给 P2-9 用) |

## 数据来源

- 景点/美食/酒店:从携程、马蜂窝、大众点评复制整理
- 天气:和风天气 API(失败时用历史平均)
- 标签:课程材料 + 自己总结

## 字段示例

```json
{
  "id": "wuhan_huanghelou",
  "city": "武汉",
  "name": "黄鹤楼",
  "category": "历史",
  "tags": ["历史", "文化", "地标"],
  "description": "江南三大名楼之首...",
  "best_duration_hours": 2,
  "ticket_price": 80,
  "open_hours": "8:30-18:00",
  "lat": 30.5438,
  "lng": 114.3055,
  "suitable_for": ["情侣", "亲子", "独自"],
  "tips": "周一闭馆;傍晚登楼可看落日和夜景",
  "rating": 4.5,
  "photo_spots": [
    {"location": "西门广场", "angle": "正面仰拍", "best_time": "黄昏", "tip": "用长焦拍飞檐"}
  ]
}
```

## 制作流程

1. Day 1 上午启动会后,成员 F 立刻开始
2. 先做武汉 1 城数据,跑通完整流程
3. Day 1 下午完成其余 5 城
4. 全部 JSON 完成后,成员 C 跑 `python scripts/build_chroma_index.py` 入库