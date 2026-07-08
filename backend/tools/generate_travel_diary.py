"""generate_travel_diary 工具 - mock 实现(B 后续接入真实 LLM,项目方案 §2.4 P2-5)。"""
from __future__ import annotations

from langchain_core.tools import tool


_MOCK_DIARY = """# Day {day} · 旅行日记

清晨阳光洒在窗前,你收拾好行囊,踏上了今天的旅程。

上午你漫步在 **{place}**,感受着这座城市的脉搏与温度。{desc}

午餐时分,你品尝了当地特色,味蕾在舌尖跳舞。

下午的时光慢慢流淌,每一处转角都是新的惊喜。

夕阳西下,今日的旅程画上句点,但记忆永远鲜活。

> 一座城,一段路,一份心情。
"""


@tool
def generate_travel_diary(day_plan: dict, mood: str = "开心") -> str:
    """基于当天行程生成旅行日记(本轮 mock,B 后续接 LLM)。

    Args:
        day_plan: 当天行程(含 date/items)
        mood: 心情基调

    Returns:
        Markdown 字符串,日记内容。
    """
    items = day_plan.get("items", []) if isinstance(day_plan, dict) else []
    place = items[0].get("name", "这座城市") if items else "这座城市"
    desc = items[0].get("description", "") if items else ""
    day_num = day_plan.get("day", "?") if isinstance(day_plan, dict) else "?"
    return _MOCK_DIARY.format(day=day_num, place=place, desc=desc)


__all__ = ["generate_travel_diary"]