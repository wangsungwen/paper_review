# ui/theme.py
"""全站視覺主題：字體、配色、元件樣式與可重用的版面元件。

設計語言：學術專業風 (Academic Professional)
- 字體：Noto Sans TC (中文) + Inter (西文)，等寬用 JetBrains Mono
- 主色：學術深藍；輔助色系採 slate 灰階
- 支援深／淺色雙模式 (由側邊欄開關切換，palette 驅動)
"""

import streamlit as st

# ---------------------------------------------------------
# 配色權杖 (Design Tokens) — 淺色 / 深色雙 palette
# ---------------------------------------------------------
LIGHT = {
    "primary": "#1F4E79",
    "primary_hover": "#2A639A",
    "primary_soft": "#EAF1F8",
    "app_bg": "#FFFFFF",
    "surface": "#FFFFFF",
    "surface_alt": "#F7F9FC",
    "text": "#1A202C",
    "text_muted": "#64748B",
    "border": "#E2E8F0",
    "shadow": "rgba(15, 23, 42, .06)",
    "success": "#166534",
    "success_bg": "#F0FDF4",
    "success_border": "#BBF7D0",
    "danger": "#B91C1C",
    "danger_bg": "#FEF2F2",
    "danger_border": "#FECACA",
    "hero_from": "#1F4E79",
    "hero_to": "#2E6DA4",
    "badge_bg": "#EAF1F8",
    "badge_text": "#1F4E79",
    "input_bg": "#FFFFFF",
    "primary_text": "#FFFFFF",
    "btn_bg": "#FFFFFF",
    "btn_text": "#1F2937",
    "btn_border": "#94A3B8",
    "btn_primary_bg": "#1F4E79",
    "btn_primary_hover": "#2A639A",
    "btn_primary_text": "#FFFFFF",
}

DARK = {
    "primary": "#7EB0E0",
    "primary_hover": "#9CC4EA",
    "primary_soft": "#1E3A5F",
    "app_bg": "#0F172A",
    "surface": "#1E293B",
    "surface_alt": "#152238",
    "text": "#E2E8F0",
    "text_muted": "#94A3B8",
    "border": "#334155",
    "shadow": "rgba(0, 0, 0, .35)",
    "success": "#86EFAC",
    "success_bg": "#12291B",
    "success_border": "#1F4D31",
    "danger": "#FCA5A5",
    "danger_bg": "#2D1616",
    "danger_border": "#5B2424",
    "hero_from": "#16324F",
    "hero_to": "#1F4E79",
    "badge_bg": "#1E3A5F",
    "badge_text": "#AECDE8",
    "input_bg": "#0F1B2E",
    "primary_text": "#0F172A",
    "btn_bg": "#2A3B55",
    "btn_text": "#F8FAFC",
    "btn_border": "#64748B",
    "btn_primary_bg": "#2D6FB8",
    "btn_primary_hover": "#3D82CC",
    "btn_primary_text": "#FFFFFF",
}

_CSS_TEMPLATE = """
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

/* ---------- 背景與全域文字 (深淺模式核心) ---------- */
.stApp, [data-testid="stAppViewContainer"] {{
    background: {app_bg};
    color: {text};
}}
header[data-testid="stHeader"] {{
    background: {app_bg};
}}
h1, h2, h3, h4, h5, h6, p, li, label,
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"] {{
    color: {text};
}}
[data-testid="stCaptionContainer"], .stCaption, small {{
    color: {text_muted} !important;
}}

/* ---------- 側邊欄 ---------- */
[data-testid="stSidebar"] {{
    background: {surface_alt};
    border-right: 1px solid {border};
}}
[data-testid="stSidebar"] h2 {{
    font-size: 1.05rem;
    font-weight: 700;
    color: {primary};
}}

/* ---------- 按鈕 (涵蓋新舊版 Streamlit DOM，強制高對比) ---------- */
[data-testid="stButton"] button, [data-testid="stDownloadButton"] button,
[data-testid="stFormSubmitButton"] button,
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
    border-radius: 8px !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em;
    border: 1.5px solid {btn_border} !important;
    background: {btn_bg} !important;
    color: {btn_text} !important;
    transition: all .15s ease;
}}
/* 按鈕內層所有元素 (p/span/div) 一律繼承按鈕文字色 */
[data-testid="stButton"] button *, [data-testid="stDownloadButton"] button *,
[data-testid="stFormSubmitButton"] button *,
.stButton > button *, .stDownloadButton > button *, .stFormSubmitButton > button * {{
    color: inherit !important;
}}
/* 主要按鈕 (雙屬性選擇器壓過上方通用規則) */
[data-testid="stButton"] button[kind="primary"],
[data-testid="stButton"] [data-testid="stBaseButton-primary"],
[data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"],
[data-testid="stFormSubmitButton"] [data-testid="stBaseButton-primaryFormSubmit"],
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
    background: {btn_primary_bg} !important;
    border-color: {btn_primary_bg} !important;
    color: {btn_primary_text} !important;
    box-shadow: 0 1px 4px {shadow};
}}
[data-testid="stButton"] button[kind="primary"]:hover,
[data-testid="stButton"] [data-testid="stBaseButton-primary"]:hover,
[data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"]:hover,
.stButton > button[kind="primary"]:hover {{
    background: {btn_primary_hover} !important;
    border-color: {btn_primary_hover} !important;
    color: {btn_primary_text} !important;
}}
/* 次要按鈕 hover：主色描邊 + 主色文字 */
[data-testid="stButton"] button:hover, [data-testid="stDownloadButton"] button:hover,
[data-testid="stFormSubmitButton"] button:hover,
.stButton > button:hover, .stDownloadButton > button:hover {{
    border-color: {primary} !important;
    color: {primary} !important;
}}
[data-testid="stButton"] button:disabled {{
    opacity: .45;
}}

/* ---------- Popover(當前參數)、上傳(Browse files) 及其他 BaseButton 補漏 ---------- */
/* 通用安全網：主畫面與側邊欄內所有 stBaseButton-* (popover 觸發鈕、uploader 按鈕...) */
[data-testid="stAppViewContainer"] button[data-testid^="stBaseButton"],
[data-testid="stSidebar"] button[data-testid^="stBaseButton"],
[data-testid="stPopover"] button,
[data-testid="stFileUploaderDropzone"] button,
[data-testid="stFileUploader"] button {{
    background: {btn_bg} !important;
    color: {btn_text} !important;
    border: 1.5px solid {btn_border} !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}}
[data-testid="stAppViewContainer"] button[data-testid^="stBaseButton"] *,
[data-testid="stSidebar"] button[data-testid^="stBaseButton"] *,
[data-testid="stPopover"] button *,
[data-testid="stFileUploader"] button * {{
    color: inherit !important;
}}
[data-testid="stAppViewContainer"] button[data-testid^="stBaseButton"]:hover,
[data-testid="stSidebar"] button[data-testid^="stBaseButton"]:hover,
[data-testid="stPopover"] button:hover,
[data-testid="stFileUploader"] button:hover {{
    border-color: {primary} !important;
    color: {primary} !important;
}}
/* Popover 彈出面板本體 */
[data-testid="stPopoverBody"] {{
    background: {surface} !important;
    color: {text} !important;
    border: 1px solid {border} !important;
    border-radius: 10px !important;
}}
[data-testid="stPopoverBody"] p, [data-testid="stPopoverBody"] label {{
    color: {text} !important;
}}
/* 上傳區說明文字與已上傳檔名 */
[data-testid="stFileUploaderDropzoneInstructions"],
[data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stFileUploaderDropzoneInstructions"] small {{
    color: {text_muted} !important;
}}
[data-testid="stFileUploaderFileName"],
[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] * {{
    color: {text} !important;
}}

/* ---------- 輸入元件 ---------- */
.stTextInput input, .stNumberInput input, .stTextArea textarea {{
    border-radius: 8px !important;
    background: {input_bg} !important;
    color: {text} !important;
}}
.stSelectbox [data-baseweb="select"] > div {{
    border-radius: 8px !important;
    background: {input_bg} !important;
    color: {text} !important;
}}
[data-baseweb="popover"] [role="listbox"] {{
    background: {surface} !important;
    color: {text} !important;
}}

/* ---------- Metric 卡片化 ---------- */
[data-testid="stMetric"] {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 12px;
    padding: 1rem 1.25rem;
    box-shadow: 0 1px 3px {shadow};
}}
[data-testid="stMetricLabel"] {{
    color: {text_muted};
    font-weight: 500;
}}
[data-testid="stMetricValue"] {{
    color: {primary};
    font-weight: 700;
}}

/* ---------- Expander / 上傳區 / 表格 ---------- */
[data-testid="stExpander"] {{
    border: 1px solid {border};
    border-radius: 10px;
    background: {surface};
}}
[data-testid="stExpander"] summary {{
    color: {text};
}}
[data-testid="stFileUploaderDropzone"] {{
    border-radius: 10px;
    border: 1.5px dashed {border};
    background: {surface_alt};
    color: {text};
}}
[data-testid="stDataFrame"] {{
    border: 1px solid {border};
    border-radius: 10px;
}}

/* ---------- 分隔線 ---------- */
hr {{
    border-color: {border};
}}

/* ---------- 自訂元件 ---------- */
.prs-hero {{
    padding: 1.6rem 2rem 1.4rem;
    background: linear-gradient(135deg, {hero_from} 0%, {hero_to} 100%);
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
    border-bottom: 2px solid {primary_soft};
}}
.prs-section .prs-step {{
    flex: none;
    background: {primary};
    color: {primary_text};
    font-weight: 700;
    font-size: .85rem;
    border-radius: 6px;
    padding: .15rem .55rem;
    letter-spacing: .03em;
}}
.prs-section .prs-title {{
    font-size: 1.25rem;
    font-weight: 700;
    color: {text};
}}
.prs-section .prs-desc {{
    color: {text_muted};
    font-size: .85rem;
    font-weight: 400;
}}

.prs-stat {{
    border: 1px solid {border};
    border-radius: 12px;
    padding: .9rem 1rem;
    text-align: center;
    margin-bottom: .7rem;
    background: {surface};
    box-shadow: 0 1px 3px {shadow};
}}
.prs-stat .prs-stat-label {{
    color: {text_muted};
    font-size: .85rem;
    font-weight: 500;
    letter-spacing: .02em;
}}
.prs-stat .prs-stat-value {{
    font-size: 1.9rem;
    font-weight: 700;
    color: {text};
    font-variant-numeric: tabular-nums;
}}
.prs-stat.prs-stat-danger {{
    background: {danger_bg};
    border-color: {danger_border};
}}
.prs-stat.prs-stat-danger .prs-stat-value {{ color: {danger}; }}
.prs-stat.prs-stat-success {{
    background: {success_bg};
    border-color: {success_border};
}}
.prs-stat.prs-stat-success .prs-stat-value {{ color: {success}; }}

.prs-doc {{
    line-height: 1.9;
    border: 1px solid {border};
    border-radius: 12px;
    padding: 1.4rem 1.6rem;
    background: {surface};
    color: {text};
    font-size: 1rem;
    box-shadow: 0 1px 3px {shadow};
}}

.prs-badge {{
    display: inline-block;
    background: {badge_bg};
    color: {badge_text};
    border-radius: 999px;
    padding: .12rem .7rem;
    font-size: .8rem;
    font-weight: 600;
    letter-spacing: .02em;
}}
</style>
"""


def inject_theme(dark: bool = None):
    """注入全站 CSS，於 st.set_page_config 之後呼叫一次。

    dark=None 時自動讀取 st.session_state["dark_mode"] (側邊欄開關)。
    """
    if dark is None:
        dark = bool(st.session_state.get("dark_mode", False))
    palette = DARK if dark else LIGHT
    st.markdown(_CSS_TEMPLATE.format(**palette), unsafe_allow_html=True)


def theme_toggle():
    """側邊欄的深／淺色切換開關 (放在 sidebar 區塊內呼叫)。

    字樣與圖示隨當前模式切換：淺色時顯示「🌙 深色模式」(切過去)，
    深色時顯示「☀️ 淺色模式」(切回來)。
    """
    dark = bool(st.session_state.get("dark_mode", False))
    label = "☀️ 淺色模式" if dark else "🌙 深色模式"
    st.toggle(
        label,
        key="dark_mode",
        help="切換介面深淺配色，設定僅保存於本次瀏覽器會話。",
    )


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
