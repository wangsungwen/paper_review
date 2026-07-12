# ui/theme.py
"""全站視覺主題：字體、配色、元件樣式與可重用的版面元件。

設計語言：學術專業風 (Academic Professional)
- 字體：Noto Sans TC (中文) + Inter (西文)，等寬用 JetBrains Mono
- 主色：學術深藍 #1F4E79；輔助色系採 slate 灰階
- 原則：低彩度、留白充足、以字重與階層取代大量 emoji
"""

import streamlit as st

# ---------------------------------------------------------
# 配色權杖 (Design Tokens)
# ---------------------------------------------------------
PRIMARY = "#1F4E79"       # 學術深藍
PRIMARY_LIGHT = "#EAF1F8"
ACCENT = "#B7791F"        # 點綴金 (評分/重點)
TEXT = "#1A202C"
TEXT_MUTED = "#64748B"
BORDER = "#E2E8F0"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F7F9FC"
SUCCESS = "#166534"
SUCCESS_BG = "#F0FDF4"
DANGER = "#B91C1C"
DANGER_BG = "#FEF2F2"

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+TC:wght@400;500;700&family=Noto+Serif+TC:wght@600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ---------- 全域字體 ---------- */
html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stSidebar"], button, input, textarea, select {{
    font-family: 'Inter', 'Noto Sans TC', 'Microsoft JhengHei', sans-serif !important;
}}
code, pre, [data-testid="stCode"] {{
    font-family: 'JetBrains Mono', 'Noto Sans TC', monospace !important;
}}

/* ---------- 標題階層 ---------- */
h1, h2, h3 {{
    color: {TEXT};
    letter-spacing: 0.01em;
}}

/* ---------- 側邊欄 ---------- */
[data-testid="stSidebar"] {{
    background: {SURFACE_ALT};
    border-right: 1px solid {BORDER};
}}
[data-testid="stSidebar"] h2 {{
    font-size: 1.05rem;
    font-weight: 700;
    color: {PRIMARY};
}}

/* ---------- 按鈕 ---------- */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
    border-radius: 8px;
    font-weight: 600;
    letter-spacing: 0.02em;
    border: 1px solid {BORDER};
    transition: all .15s ease;
}}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
    background: {PRIMARY};
    border-color: {PRIMARY};
}}
.stButton > button[kind="primary"]:hover {{
    background: #2A639A;
    border-color: #2A639A;
}}
.stButton > button:hover {{
    border-color: {PRIMARY};
    color: {PRIMARY};
}}

/* ---------- 輸入元件 ---------- */
.stTextInput input, .stNumberInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] {{
    border-radius: 8px !important;
}}

/* ---------- Metric 卡片化 ---------- */
[data-testid="stMetric"] {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 1rem 1.25rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, .06);
}}
[data-testid="stMetricLabel"] {{
    color: {TEXT_MUTED};
    font-weight: 500;
}}
[data-testid="stMetricValue"] {{
    color: {PRIMARY};
    font-weight: 700;
}}

/* ---------- Expander / 上傳區 ---------- */
[data-testid="stExpander"] {{
    border: 1px solid {BORDER};
    border-radius: 10px;
    background: {SURFACE};
}}
[data-testid="stFileUploaderDropzone"] {{
    border-radius: 10px;
    border: 1.5px dashed {BORDER};
    background: {SURFACE_ALT};
}}

/* ---------- 表格 ---------- */
[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER};
    border-radius: 10px;
}}

/* ---------- 分隔線 ---------- */
hr {{
    border-color: {BORDER};
}}

/* ---------- 自訂元件 ---------- */
.prs-hero {{
    padding: 1.6rem 2rem 1.4rem;
    background: linear-gradient(135deg, {PRIMARY} 0%, #2E6DA4 100%);
    border-radius: 14px;
    margin-bottom: 1.2rem;
}}
.prs-hero .prs-hero-title {{
    font-family: 'Noto Serif TC', 'Inter', serif;
    font-size: 1.7rem;
    font-weight: 700;
    color: #FFFFFF;
    margin: 0;
    line-height: 1.3;
}}
.prs-hero .prs-hero-sub {{
    color: rgba(255,255,255,.82);
    font-size: .95rem;
    margin-top: .35rem;
    font-weight: 400;
}}

.prs-section {{
    display: flex;
    align-items: baseline;
    gap: .7rem;
    margin: 2rem 0 .4rem;
    padding-bottom: .45rem;
    border-bottom: 2px solid {PRIMARY_LIGHT};
}}
.prs-section .prs-step {{
    flex: none;
    background: {PRIMARY};
    color: #fff;
    font-weight: 700;
    font-size: .85rem;
    border-radius: 6px;
    padding: .15rem .55rem;
    letter-spacing: .03em;
}}
.prs-section .prs-title {{
    font-size: 1.25rem;
    font-weight: 700;
    color: {TEXT};
}}
.prs-section .prs-desc {{
    color: {TEXT_MUTED};
    font-size: .85rem;
    font-weight: 400;
}}

.prs-stat {{
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: .9rem 1rem;
    text-align: center;
    margin-bottom: .7rem;
    background: {SURFACE};
    box-shadow: 0 1px 3px rgba(15,23,42,.05);
}}
.prs-stat .prs-stat-label {{
    color: {TEXT_MUTED};
    font-size: .85rem;
    font-weight: 500;
    letter-spacing: .02em;
}}
.prs-stat .prs-stat-value {{
    font-size: 1.9rem;
    font-weight: 700;
    color: {TEXT};
    font-variant-numeric: tabular-nums;
}}
.prs-stat.prs-stat-danger {{
    background: {DANGER_BG};
    border-color: #FECACA;
}}
.prs-stat.prs-stat-danger .prs-stat-value {{ color: {DANGER}; }}
.prs-stat.prs-stat-success {{
    background: {SUCCESS_BG};
    border-color: #BBF7D0;
}}
.prs-stat.prs-stat-success .prs-stat-value {{ color: {SUCCESS}; }}

.prs-doc {{
    line-height: 1.9;
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 1.4rem 1.6rem;
    background: {SURFACE};
    color: {TEXT};
    font-size: 1rem;
    box-shadow: 0 1px 3px rgba(15,23,42,.05);
}}

.prs-badge {{
    display: inline-block;
    background: {PRIMARY_LIGHT};
    color: {PRIMARY};
    border-radius: 999px;
    padding: .12rem .7rem;
    font-size: .8rem;
    font-weight: 600;
    letter-spacing: .02em;
}}
</style>
"""


def inject_theme():
    """注入全站 CSS，於 st.set_page_config 之後呼叫一次。"""
    st.markdown(_CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str = ""):
    """頁面頂部主視覺標題。"""
    sub_html = f'<div class="prs-hero-sub">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div class="prs-hero"><div class="prs-hero-title">{title}</div>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def section_header(step: str, title: str, desc: str = ""):
    """章節標頭：步驟徽章 + 標題 + 補充說明。"""
    desc_html = f'<span class="prs-desc">{desc}</span>' if desc else ""
    st.markdown(
        f'<div class="prs-section"><span class="prs-step">{step}</span>'
        f'<span class="prs-title">{title}</span>{desc_html}</div>',
        unsafe_allow_html=True,
    )


def stat_card(label: str, value, kind: str = "default") -> str:
    """統計卡片 HTML (kind: default / danger / success)。"""
    cls = {"danger": " prs-stat-danger", "success": " prs-stat-success"}.get(kind, "")
    return (
        f'<div class="prs-stat{cls}">'
        f'<div class="prs-stat-label">{label}</div>'
        f'<div class="prs-stat-value">{value:,}</div></div>'
    )


def badge(text: str) -> str:
    """膠囊徽章 HTML。"""
    return f'<span class="prs-badge">{text}</span>'
