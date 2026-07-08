"""generate_checklist 工具 - mock 实现(B 后续接入真实 LLM,项目方案 §2.4 P2-4)。"""
from __future__ import annotations

from langchain_core.tools import tool


_MOCK_CHECKLIST = """- [ ] 身份证 / 护照
- [ ] 现金 + 银行卡
- [ ] 手机 + 充电宝
- [ ] 雨具(根据天气预报)
- [ ] 防晒霜 + 太阳镜
- [ ] 舒适步行鞋
- [ ] 常用药品(感冒/肠胃/创可贴)
- [ ] 相机 / 拍照设备
- [ ] 行李箱(建议 24 寸以内)
- [ ] 当地交通卡 / App
"""


@tool
def generate_checklist(plan: dict, weather: list, people_type: str = "情侣") -> str:
    """根据行程、天气、人群生成装备清单(B 后续接入真实 LLM,本轮 mock)。

    Args:
        plan: 完整行程 JSON
        weather: 天气数据列表
        people_type: 人群类型

    Returns:
        Markdown 字符串,Checklist 列表。
    """
    return _MOCK_CHECKLIST


__all__ = ["generate_checklist"]