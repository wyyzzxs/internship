"""行程对比 — P2-7。"""

from __future__ import annotations

import streamlit as st


def render_trip_compare(plan_a: dict | None, plan_b: dict | None) -> None:
    if not plan_a or not plan_b:
        st.info("生成两次不同行程后，可在此对比方案。")
        return

    def _stats(plan: dict) -> dict:
        bd = plan.get("budget_breakdown", {})
        spent = sum(bd.values())
        attractions = sum(
            1 for d in plan.get("days", []) for i in d.get("items", []) if i.get("type") == "景点"
        )
        return {
            "city": plan.get("trip_summary", {}).get("city", ""),
            "days": plan.get("trip_summary", {}).get("days", 0),
            "spent": spent,
            "budget": plan.get("trip_summary", {}).get("total_budget", 0),
            "attractions": attractions,
        }

    sa, sb = _stats(plan_a), _stats(plan_b)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 方案 A")
        st.write(f"**{sa['city']}** · {sa['days']} 天")
        st.metric("预计花费", f"¥{sa['spent']}")
        st.metric("景点数", sa["attractions"])
    with col2:
        st.markdown("#### 方案 B")
        st.write(f"**{sb['city']}** · {sb['days']} 天")
        st.metric("预计花费", f"¥{sb['spent']}")
        st.metric("景点数", sb["attractions"])

    diff = sa["spent"] - sb["spent"]
    if diff > 0:
        st.success(f"方案 B 比方案 A 省 ¥{diff}")
    elif diff < 0:
        st.success(f"方案 A 比方案 B 省 ¥{-diff}")
    else:
        st.info("两方案花费相同")
