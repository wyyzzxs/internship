# 工具层(成员 B 负责)
# 7 个 @tool 函数:
#   1. search_attractions - RAG 检索景点
#   2. get_weather       - 天气查询(含 hourly)
#   3. calculate_budget  - 预算计算
#   4. optimize_route    - 路线优化
#   5. search_nearby_poi - 周边 POI 搜索(P1-2)
#   6. generate_checklist - 智能装备清单(P2-4)
#   7. generate_travel_diary - AI 旅行日记(P2-5,函数由 B 实现,集成由 A)