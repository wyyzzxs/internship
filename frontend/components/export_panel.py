"""攻略导出 — P1-5：Markdown / JSON / PDF。"""

from __future__ import annotations

import json
from io import BytesIO

import streamlit as st


def _plan_to_markdown(plan: dict) -> str:
    s = plan.get("trip_summary", {})
    lines = [
        f"# {s.get('city', '')} {s.get('days', '')} 日游攻略",
        "",
        f"- **日期**: {s.get('start_date', '')} ~ {s.get('end_date', '')}",
        f"- **预算**: ¥{s.get('total_budget', 0)}",
        f"- **同行**: {s.get('people', '')}",
        "",
    ]
    for day in plan.get("days", []):
        lines.append(f"## Day {day.get('day')} ({day.get('date')})")
        lines.append("")
        for item in day.get("items", []):
            cost = "免费" if item.get("cost", 0) == 0 else f"¥{item['cost']}"
            lines.append(
                f"- **{item.get('time', '')}** {item.get('emoji', '')} "
                f"{item.get('name', '')} ({cost}) — {item.get('description', '')}"
            )
        lines.append(f"- 当日花费: ¥{day.get('day_cost', 0)}")
        lines.append("")
    bd = plan.get("budget_breakdown", {})
    if bd:
        lines.append("## 预算明细")
        for k, v in bd.items():
            lines.append(f"- {k}: ¥{v}")
    tips = plan.get("tips", [])
    if tips:
        lines.append("")
        lines.append("## 贴士")
        for t in tips:
            lines.append(f"- {t}")
    return "\n".join(lines)


def render_export_panel(plan: dict) -> None:
    st.subheader("📥 导出攻略")
    md = _plan_to_markdown(plan)
    js = json.dumps(plan, ensure_ascii=False, indent=2)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("📄 Markdown", md, file_name="travel_plan.md", mime="text/markdown", use_container_width=True)
    with c2:
        st.download_button("📋 JSON", js, file_name="travel_plan.json", mime="application/json", use_container_width=True)
    with c3:
        try:
            from markdown_pdf import MarkdownPdf, Section

            pdf = MarkdownPdf()
            pdf.add_section(Section(md))
            buf = BytesIO()
            pdf.save(buf)
            st.download_button(
                "📕 PDF",
                buf.getvalue(),
                file_name="travel_plan.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception:
            st.download_button(
                "📕 PDF（MD 替代）",
                md,
                file_name="travel_plan.txt",
                mime="text/plain",
                use_container_width=True,
                help="PDF 引擎不可用，下载 Markdown 文本",
            )
