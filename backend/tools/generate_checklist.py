"""generate_checklist 工具 - 临时 mock 实现。

⚠️ **临时越界 mock** - 方案 §8.3 / §9.2 P2-4 此工具由**成员 B**负责接入 LLM 生成智能清单。
   本文件由成员 A 在第二轮临时编写,仅供测试。
   B 接入真实 LLM 实现后,本文件应被删除。

签名严格对齐方案 §3.3 Tool 6 / §2.4 P2-4:`(plan, weather, people_type) -> str(Markdown)`
"""
from __future__ import annotations

from langchain_core.tools import tool


# mock 固定清单(10-15 项,含 Markdown checkbox 格式)
_MOCK_CHECKLIST: str = """# 旅行装备清单

- [ ] 身份证 / 护照
- [ ] 现金 + 银行卡
- [ ] 手机 + 充电宝 + 数据线
- [ ] 雨具(根据天气预报)
- [ ] 防晒霜 + 太阳镜
- [ ] 舒适步行鞋(每日 1.5 万步+)
- [ ] 常用药品(感冒/肠胃/创可贴)
- [ ] 相机 / 拍照设备
- [ ] 行李箱(建议 24 寸以内)
- [ ] 当地交通卡 / App(微信/支付宝)
- [ ] 保温杯
- [ ] 一次性毛巾 / 洗漱用品
- [ ] 笔记本 + 笔(记录旅程)
- [ ] 备用塑料袋(脏衣物/防雨)

> mock - 真实版由成员 B 接 LLM 动态生成(项目方案 §2.4 P2-4)
"""


@tool
def generate_checklist(plan: dict, weather: list, people_type: str) -> str:
    """根据行程、天气、人群生成装备清单(mock,B 接 LLM 后替换)。

    Args:
        plan: 完整行程 JSON
        weather: 天气数据列表
        people_type: 人群类型(独自/情侣/亲子/朋友/商务)

    Returns:
        Markdown 字符串,Checklist 列表。
    """
    return _MOCK_CHECKLIST


__all__ = ["generate_checklist"]
