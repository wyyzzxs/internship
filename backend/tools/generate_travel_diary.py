"""generate_travel_diary 工具 - **真实版**(LLMClient 调大模型 + mock 退化)。

**职责范围**:项目方案 §9.2 列在"成员 B 工具函数"中(标注"Agent 集成由 A 负责")。
- 工具函数本身归 B 写
- 但本轮 B 未提交,A 先写真实 LLM 版供测试驱动

签名严格对齐方案 §2.4 P2-5:`(day_plan, mood="开心") -> str(Markdown)`
返回:300-500 字旅行日记 Markdown(用第二人称"你",1-2 emoji)。

实现逻辑:
- Config.MOCK_LLM=true → 返固定 200 字模板(够测试用)
- Config.MOCK_LLM=false → 调 LLMClient().chat(),用 SYSTEM_PROMPT_DIARY 提示词
"""
from __future__ import annotations

import json
import logging

from langchain_core.tools import tool

from backend.agents.prompts import SYSTEM_PROMPT_DIARY

logger = logging.getLogger("backend.tools.generate_travel_diary")


def _mock_diary(day_plan: dict) -> str:
    """MOCK 模式:固定 200 字模板(测试用,够覆盖基本字段即可)。"""
    items = day_plan.get("items", []) if isinstance(day_plan, dict) else []
    if items:
        first_name = items[0].get("name", "这座城市")
        first_desc = items[0].get("description", "")
    else:
        first_name = "这座城市"
        first_desc = ""
    day_num = day_plan.get("day", 1) if isinstance(day_plan, dict) else 1
    date = day_plan.get("date", "今天") if isinstance(day_plan, dict) else "今天"

    return (
        f"# Day {day_num} · 旅行日记(模拟)\n\n"
        f"**{date}**,清晨的阳光洒在窗前,你背起行囊,踏上了今天的旅程。\n\n"
        f"上午,你来到了 **{first_name}**。{first_desc} "
        f"眼前的景致让时间仿佛慢了下来,你忍不住按下快门,想把这一刻永远留住。\n\n"
        f"午餐时分,街边小店的烟火气扑面而来,热腾腾的当地特色驱散了所有的疲惫。\n\n"
        f"下午的时光慢慢流淌,每走过一个街角,都是新的惊喜与故事。\n\n"
        f"夕阳西下,你坐在江边,看着天空被染成橘红色。这一天的疲惫与满足交织在一起,成了记忆里最鲜活的一页。\n\n"
        f"> 一座城,一段路,一份心情。📝\n"
    )


@tool
def generate_travel_diary(day_plan: dict, mood: str = "开心") -> str:
    """基于当天行程生成 300-500 字旅行日记(Markdown 格式)。

    Args:
        day_plan: 当天行程(含 date/items)
        mood: 心情基调(开心/治愈/疲惫/惊喜)

    Returns:
        Markdown 字符串,日记内容。
    """
    from backend.config import Config  # 避免循环 import
    from backend.llm.llm_client import LLMClient

    if Config.MOCK_LLM:
        return _mock_diary(day_plan)

    # 真实 LLM 调用
    try:
        items_str = (
            json.dumps(day_plan.get("items", []), ensure_ascii=False, indent=2)
            if isinstance(day_plan, dict)
            else "[]"
        )
        prompt = (
            f"{SYSTEM_PROMPT_DIARY}\n\n"
            f"日期:{day_plan.get('date', '今天') if isinstance(day_plan, dict) else '今天'}\n"
            f"行程:\n{items_str}\n"
            f"心情基调:{mood}\n"
        )
        client = LLMClient()
        resp = client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,  # 写作需要创造性
        )
        content = (resp.get("content") or "").strip()
        if content:
            return content
        logger.warning("LLM 返回空,降级到 mock")
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM 生成日记失败(%s),降级到 mock", exc)

    return _mock_diary(day_plan)


__all__ = ["generate_travel_diary", "_mock_diary"]
