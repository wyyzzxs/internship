"""主题 — 参考 overview.html 暗色玻璃拟态 + 旅游配色。"""

from __future__ import annotations

THEMES = {
    "travel_night": {
        "label": "旅行暗色（推荐）",
        "bg": "#0b1020",
        "bg2": "#141c2f",
        "sidebar": "rgba(8, 12, 24, 0.96)",
        "text": "#e8ecf4",
        "muted": "#94a3b8",
        "accent": "#ff6b4a",
        "accent2": "#ffd166",
        "accent3": "#4cc9f0",
        "card": "rgba(16, 22, 38, 0.82)",
        "border": "rgba(255, 107, 74, 0.28)",
        "glow": "rgba(255, 107, 74, 0.45)",
    },
    "overview": {
        "label": "Overview 红",
        "bg": "#0a0a0a",
        "bg2": "#1a0a0a",
        "sidebar": "rgba(10, 0, 0, 0.95)",
        "text": "#e0e0e0",
        "muted": "#a0a0a0",
        "accent": "#ff3333",
        "accent2": "#c00000",
        "accent3": "#ff6666",
        "card": "rgba(20, 0, 0, 0.7)",
        "border": "rgba(200, 0, 0, 0.35)",
        "glow": "rgba(255, 50, 50, 0.5)",
    },
    "light": {
        "label": "浅色",
        "bg": "#f4f7fb",
        "bg2": "#e8eef5",
        "sidebar": "#ffffff",
        "text": "#1a1a2e",
        "muted": "#64748b",
        "accent": "#ff6b4a",
        "accent2": "#4cc9f0",
        "accent3": "#06d6a0",
        "card": "rgba(255, 255, 255, 0.92)",
        "border": "rgba(255, 107, 74, 0.2)",
        "glow": "rgba(255, 107, 74, 0.25)",
    },
}


def get_theme_css(theme_key: str) -> str:
    t = THEMES.get(theme_key, THEMES["travel_night"])
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&display=swap');

    :root {{
        --accent: {t['accent']};
        --accent2: {t['accent2']};
        --accent3: {t['accent3']};
        --card-bg: {t['card']};
        --border: {t['border']};
        --text: {t['text']};
        --muted: {t['muted']};
        --glow: {t['glow']};
    }}

    html, body, [class*="css"] {{
        font-family: 'Noto Sans SC', 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
        color: {t['text']};
    }}

    /* ── 全局文字：主内容区亮白，强调色回归橙/金 ── */
    [data-testid="stAppViewContainer"] {{
        color: {t['text']};
    }}
    [data-testid="stMain"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stMain"] [data-testid="stMarkdownContainer"] li {{
        color: {t['text']};
    }}

    /* 侧边栏标题 — 橙金强调（不再全白） */
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1 {{
        color: {t['accent']} !important;
        font-weight: 700 !important;
        letter-spacing: 0.03em;
    }}
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2 {{
        color: {t['accent2']} !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
    }}
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
        color: {t['text']} !important;
    }}

    /* 表单标签 — 金色，提高对比度 */
    [data-testid="stWidgetLabel"], label[data-testid="stWidgetLabel"] {{
        color: {t['accent2']} !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.02em;
    }}
    [data-testid="stSidebar"] hr {{
        border-color: {t['border']} !important;
        opacity: 0.5;
    }}

    /* ── 下拉框：选中值橙金 + 弹出层暗底亮字 ── */
    [data-testid="stSelectbox"] [data-baseweb="select"] > div {{
        background: rgba(8, 12, 24, 0.75) !important;
        border-color: {t['border']} !important;
    }}
    [data-testid="stSelectbox"] [data-baseweb="select"] span,
    [data-testid="stMultiSelect"] [data-baseweb="select"] span {{
        color: {t['accent2']} !important;
        font-weight: 500 !important;
    }}

    /* 下拉弹出菜单（修复白底浅字看不见） */
    div[data-baseweb="popover"],
    div[data-baseweb="popover"] > div,
    ul[role="listbox"],
    [data-baseweb="menu"] {{
        background-color: #141c2f !important;
        border: 1px solid {t['border']} !important;
    }}
    ul[role="listbox"] li,
    [data-baseweb="menu"] li,
    [role="option"],
    [data-baseweb="menu"] [role="option"] {{
        color: {t['text']} !important;
        background-color: #141c2f !important;
        font-size: 0.92rem !important;
    }}
    ul[role="listbox"] li:hover,
    ul[role="listbox"] li[aria-selected="true"],
    [data-baseweb="menu"] li:hover,
    [role="option"]:hover,
    [aria-selected="true"][role="option"] {{
        background-color: rgba(255, 107, 74, 0.22) !important;
        color: {t['accent2']} !important;
    }}

    /* 多选标签 */
    [data-baseweb="tag"] {{
        background: {t['accent']}28 !important;
        border: 1px solid {t['accent']}66 !important;
        color: {t['accent2']} !important;
    }}
    [data-baseweb="tag"] span {{
        color: {t['accent2']} !important;
    }}

    /* 输入框选中文字 */
    .stTextInput input, .stNumberInput input, .stTextArea textarea {{
        color: {t['text']} !important;
        background: rgba(8, 12, 24, 0.75) !important;
        border: 1px solid {t['border']} !important;
        caret-color: {t['accent']};
    }}
    .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {{
        border-color: {t['accent']} !important;
        box-shadow: 0 0 0 1px {t['accent']}44 !important;
    }}

    /* 滑块 / 复选框 */
    .stSlider label, .stCheckbox label, .stCheckbox span,
    .stCheckbox p, .stSlider p {{
        color: {t['text']} !important;
    }}
    .stSlider [data-baseweb="slider"] div[data-testid="stTickBarMin"],
    .stSlider [data-baseweb="slider"] div[data-testid="stTickBarMax"] {{
        color: {t['accent2']} !important;
    }}

    /* 日期输入 */
    .stDateInput input {{
        color: {t['text']} !important;
        background: rgba(8, 12, 24, 0.75) !important;
    }}

    /* 提示框文字 */
    [data-testid="stAlert"] p, [data-testid="stAlert"] div {{
        color: {t['text']} !important;
    }}
    [data-testid="stAlert"][data-baseweb="notification"] {{
        background: {t['card']} !important;
    }}

    /* 对话输入 */
    [data-testid="stChatInput"] textarea {{
        background: rgba(8, 12, 24, 0.65) !important;
        color: {t['text']} !important;
        border: 1px solid {t['border']} !important;
    }}
    [data-testid="stChatMessageContent"] p {{
        color: {t['text']} !important;
    }}

    /* 折叠面板 */
    [data-testid="stExpander"] summary, [data-testid="stExpander"] p {{
        color: {t['text']} !important;
    }}

    /* 区块小标题 — 橙色强调 */
    .section-heading {{
        font-size: 1.15rem;
        font-weight: 600;
        color: {t['accent']};
        margin: 24px 0 14px;
        padding-bottom: 8px;
        border-bottom: 1px solid {t['border']};
        letter-spacing: 0.04em;
    }}

    /* 类型标签（替代 emoji） */
    .type-badge {{
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        padding: 2px 8px;
        border-radius: 4px;
        margin-right: 8px;
    }}

    /* 主背景渐变 */
    .stApp {{
        background: linear-gradient(135deg, {t['bg']} 0%, {t['bg2']} 100%);
        color: {t['text']};
    }}

    /* 氛围光晕 */
    .stApp::before {{
        content: '';
        position: fixed;
        inset: 0;
        background:
            radial-gradient(circle at 18% 28%, {t['accent']}14 0%, transparent 48%),
            radial-gradient(circle at 82% 72%, {t['accent3']}12 0%, transparent 50%),
            radial-gradient(circle at 50% 90%, {t['accent2']}0a 0%, transparent 45%);
        pointer-events: none;
        z-index: 0;
    }}

    /* 隐藏 Streamlit 默认顶栏 */
    header[data-testid="stHeader"] {{
        background: transparent;
    }}
    #MainMenu, footer, .stDeployButton {{
        visibility: hidden;
    }}

    /* 侧边栏 */
    [data-testid="stSidebar"] {{
        background: {t['sidebar']};
        backdrop-filter: blur(20px);
        border-right: 1px solid {t['border']};
        box-shadow: 4px 0 24px rgba(0,0,0,0.25);
    }}
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {{
        color: {t['text']};
    }}

    /* 主标题 */
    .main-header {{
        font-size: 2.4rem;
        font-weight: 700;
        letter-spacing: 1px;
        background: linear-gradient(90deg, {t['text']}, {t['accent']}, {t['accent2']});
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        text-shadow: none;
        margin-bottom: 0.25rem;
    }}

    /* Hero 区域 */
    .hero-panel {{
        text-align: center;
        padding: 28px 24px;
        margin-bottom: 24px;
        background: {t['card']};
        border: 1px solid {t['border']};
        border-radius: 14px;
        backdrop-filter: blur(12px);
        box-shadow: 0 8px 32px rgba(0,0,0,0.28);
        position: relative;
        overflow: hidden;
    }}
    .hero-panel::after {{
        content: '';
        position: absolute;
        bottom: 0;
        left: 25%;
        width: 50%;
        height: 2px;
        background: linear-gradient(90deg, transparent, {t['accent']}, transparent);
    }}
    .hero-subtitle {{
        color: {t['muted']};
        font-size: 1.05rem;
        margin-top: 8px;
    }}
    .mode-badge {{
        display: inline-block;
        margin-top: 12px;
        padding: 6px 16px;
        border-radius: 999px;
        font-size: 0.85rem;
        background: {t['accent']}22;
        border: 1px solid {t['border']};
        color: {t['accent']};
    }}

    /* 指标卡片 — 对齐 overview stat-card */
    .trip-metric-box {{
        background: {t['card']};
        border: 1px solid {t['border']};
        border-radius: 12px;
        padding: 22px 16px;
        text-align: center;
        backdrop-filter: blur(10px);
        transition: transform 0.25s, box-shadow 0.25s;
        position: relative;
        overflow: hidden;
    }}
    .trip-metric-box:hover {{
        transform: translateY(-4px);
        box-shadow: 0 12px 28px {t['glow']};
        border-color: {t['accent']}88;
    }}
    .trip-metric-value {{
        font-size: 2.2rem;
        font-weight: 700;
        color: {t['accent']};
        text-shadow: 0 0 12px {t['glow']};
    }}
    .trip-metric-icon {{
        display: none;
    }}
    .trip-metric-label {{
        font-size: 0.82rem;
        color: {t['accent2']};
        margin-top: 0;
        margin-bottom: 8px;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        font-weight: 600;
    }}

    /* 时间轴日卡片 */
    .day-card {{
        background: {t['card']};
        border: 1px solid {t['border']};
        border-left: 4px solid {t['accent']};
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 18px;
        backdrop-filter: blur(8px);
    }}

    /* Tabs — 类似 overview 导航 */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px;
        background: {t['card']};
        border: 1px solid {t['border']};
        border-radius: 12px;
        padding: 6px 8px;
        backdrop-filter: blur(10px);
    }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent;
        color: {t['muted']};
        border-radius: 8px;
        padding: 10px 18px;
        font-weight: 500;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        color: {t['accent2']} !important;
    }}
    .stTabs [aria-selected="true"] {{
        background: {t['accent']}22 !important;
        color: {t['accent']} !important;
        border-bottom: none !important;
        box-shadow: inset 0 -2px 0 {t['accent']};
        font-weight: 600 !important;
    }}

    /* 主按钮 */
    .stButton > button[kind="primary"] {{
        background: linear-gradient(90deg, {t['accent']}, {t['accent2']}) !important;
        color: #fff !important;
        border: 1px solid {t['accent']} !important;
        border-radius: 999px !important;
        font-weight: 600 !important;
        padding: 0.55rem 1.2rem !important;
        box-shadow: 0 4px 18px {t['glow']} !important;
        transition: all 0.25s !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        box-shadow: 0 6px 24px {t['glow']} !important;
        transform: translateY(-1px);
    }}

    /* 次级按钮 */
    .stButton > button[kind="secondary"] {{
        background: {t['accent']}18 !important;
        border: 1px solid {t['border']} !important;
        color: {t['text']} !important;
        border-radius: 999px !important;
    }}

    /* 输入框（不含 select 文字色，避免覆盖橙金） */
    .stTextInput input, .stNumberInput input, .stTextArea textarea {{
        background: rgba(8, 12, 24, 0.75) !important;
        border: 1px solid {t['border']} !important;
        color: {t['text']} !important;
        border-radius: 8px !important;
    }}
    .stSelectbox div[data-baseweb="select"] > div {{
        background: rgba(8, 12, 24, 0.75) !important;
        border: 1px solid {t['border']} !important;
        border-radius: 8px !important;
    }}

    /* Metric 原生组件 */
    [data-testid="stMetric"] {{
        background: {t['card']};
        border: 1px solid {t['border']};
        border-radius: 12px;
        padding: 16px;
        backdrop-filter: blur(8px);
    }}
    [data-testid="stMetricValue"] {{
        color: {t['accent']} !important;
    }}

    /* info / success 框 */
    .stAlert {{
        background: {t['card']} !important;
        border: 1px solid {t['border']} !important;
        border-radius: 10px !important;
    }}

    /* 分隔线 */
    hr {{
        border-color: {t['border']} !important;
    }}

    h2, h3, .stSubheader {{
        color: {t['accent']} !important;
    }}
    .stCaption {{
        color: {t['muted']} !important;
    }}

    /* 区块标题 — overview section-title */
    .section-title {{
        font-size: 1.45rem;
        font-weight: 700;
        color: {t['accent']};
        text-align: center;
        margin: 28px 0 18px;
        position: relative;
        padding-bottom: 12px;
    }}
    .section-title::after {{
        content: '';
        position: absolute;
        bottom: 0;
        left: 38%;
        width: 24%;
        height: 2px;
        background: linear-gradient(90deg, transparent, {t['accent']}, transparent);
    }}

    /* Plotly 图表玻璃卡片 */
    [data-testid="stPlotlyChart"] {{
        background: {t['card']};
        border: 1px solid {t['border']};
        border-radius: 14px;
        padding: 12px 8px 4px;
        backdrop-filter: blur(12px);
        box-shadow: 0 8px 28px rgba(0,0,0,0.22);
        position: relative;
        overflow: hidden;
    }}
    [data-testid="stPlotlyChart"]::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, {t['accent']}, transparent);
        z-index: 1;
        pointer-events: none;
    }}
    [data-testid="stPlotlyChart"] iframe {{
        background: transparent !important;
    }}

    /* 预算明细表格 */
    .glass-table-wrap {{
        background: {t['card']};
        border: 1px solid {t['border']};
        border-radius: 14px;
        padding: 8px 12px 16px;
        backdrop-filter: blur(12px);
        box-shadow: 0 8px 28px rgba(0,0,0,0.22);
        overflow-x: auto;
    }}
    .glass-table {{
        width: 100%;
        border-collapse: collapse;
        color: {t['text']};
        font-size: 0.95rem;
    }}
    .glass-table thead th {{
        color: {t['muted']};
        font-weight: 600;
        text-align: left;
        padding: 14px 12px 10px;
        border-bottom: 1px solid {t['border']};
        letter-spacing: 0.3px;
    }}
    .glass-table tbody tr {{
        transition: background 0.2s;
    }}
    .glass-table tbody tr:hover {{
        background: {t['accent']}12;
    }}
    .glass-table tbody td {{
        padding: 14px 12px;
        border-bottom: 1px solid {t['border']}55;
        vertical-align: middle;
    }}
    .glass-table tbody tr:last-child td {{
        border-bottom: none;
    }}
    .budget-cat {{
        display: flex;
        align-items: center;
        gap: 10px;
        font-weight: 500;
    }}
    .budget-dot {{
        width: 10px;
        height: 10px;
        border-radius: 50%;
        flex-shrink: 0;
        box-shadow: 0 0 8px currentColor;
    }}
    .budget-amt {{
        font-weight: 700;
        color: {t['accent']};
        font-size: 1.05rem;
    }}
    .budget-pct {{
        color: {t['muted']};
    }}
    .budget-bar-track {{
        height: 8px;
        background: rgba(255,255,255,0.06);
        border-radius: 999px;
        overflow: hidden;
        min-width: 80px;
    }}
    .budget-bar-fill {{
        height: 100%;
        border-radius: 999px;
        transition: width 0.4s ease;
    }}

    /* 预算提示条 */
    .budget-alert {{
        text-align: center;
        padding: 12px 16px;
        border-radius: 10px;
        margin: 12px 0 20px;
        font-size: 0.95rem;
        backdrop-filter: blur(8px);
    }}
    .budget-alert-ok {{
        background: rgba(6, 214, 160, 0.12);
        border: 1px solid rgba(6, 214, 160, 0.35);
        color: #06d6a0;
    }}
    .budget-alert-warn {{
        background: rgba(255, 107, 74, 0.12);
        border: 1px solid {t['border']};
        color: {t['accent']};
    }}

    /* Streamlit 原生表格兜底（其他页面若用到） */
    [data-testid="stTable"], [data-testid="stDataFrame"] {{
        background: {t['card']} !important;
        border: 1px solid {t['border']} !important;
        border-radius: 12px !important;
        overflow: hidden;
    }}
    [data-testid="stTable"] table, [data-testid="stDataFrame"] table {{
        color: {t['text']} !important;
    }}
    [data-testid="stTable"] th, [data-testid="stDataFrame"] th {{
        color: {t['muted']} !important;
        background: rgba(0,0,0,0.2) !important;
    }}
    [data-testid="stTable"] td, [data-testid="stDataFrame"] td {{
        color: {t['text']} !important;
    }}

    /* 对话气泡 */
    [data-testid="stChatMessage"] {{
        background: {t['card']} !important;
        border: 1px solid {t['border']} !important;
        border-radius: 12px !important;
    }}

    /* HTML 组件 iframe（景点卡片墙等） */
    iframe {{
        border-radius: 14px !important;
    }}
    [data-testid="stHtml"] {{
        background: transparent !important;
    }}
    </style>
    """
