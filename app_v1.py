# app.py

import streamlit as st
import asyncio
import json
import os
from models.paper import Paper
from models.reviewer import ReviewerAgent
from llm.interface import LLMInterface
from core.orchestrator import PaperReviewOrchestrator
from core.ai_detector import AIDetector

import sys
import tkinter as tk
from tkinter import filedialog

def select_file(current_path=""):
    """ 開啟檔案選擇視窗並返回路徑 """
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        # 嘗試從目前路徑所在資料夾開始瀏覽
        initial_dir = os.path.dirname(current_path) if current_path and os.path.exists(os.path.dirname(current_path)) else os.getcwd()
        file_path = filedialog.askopenfilename(
            initialdir=initial_dir,
            title="選擇 GGUF 模型檔案",
            filetypes=[("GGUF files", "*.gguf"), ("All files", "*.*")]
        )
        root.destroy()
        return file_path
    except Exception as e:
        return None

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

st.set_page_config(page_title="多代理人論文審查系統", page_icon="🎓", layout="wide")

# ----------------- 初始化 -----------------
# 優先讀取執行檔同級目錄下的 config.json (讓使用者可以修改)
# 如果不存在，才讀備份到打包內部的預設 config.json
config_name = "config.json"
if os.path.exists(config_name):
    config_path = config_name
else:
    config_path = resource_path(config_name)

if not os.path.exists(config_path):
    default_config = {
        "llm_mode": "mock",
        "cloud": {"api_key": "", "model_name": "gpt-4o"},
        "local": {"model_path": "./local_models/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf", "n_ctx": 4096, "max_tokens": 1024},
        "ai_detector": {"api_key": "", "api_url": "https://api.gptzero.me/v2/predict/text"}
    }
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, indent=4)

def load_config():
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config):
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

app_config = load_config()

if "review_history" not in st.session_state:
    st.session_state.review_history = None

if "reviewers" not in st.session_state:
    st.session_state.reviewers = [
        ReviewerAgent("Dr. Alan", "電腦視覺與深度學習", "輕量化神經網路", "嚴格，要求完整數據驗證。"),
        ReviewerAgent("Prof. Lin", "嵌入式與邊緣運算", "微控制器整合", "務實，重視硬體資源消耗。")
    ]

# ----------------- 側邊欄：功能導覽與快速切換 -----------------
with st.sidebar:
    st.header("🎮 功能選單")
    app_mode = st.radio("目前工作區", ["論文審查與分析", "⚙️ 參數設定"])
    
    st.divider()
    st.subheader("🤖 LLM 快速切換")
    mode_options = ["cloud", "local", "mock"]
    current_index = mode_options.index(app_config.get("llm_mode", "mock")) if app_config.get("llm_mode", "mock") in mode_options else 2
    
    selected_mode = st.selectbox(
        "切換 LLM 推論模式", 
        mode_options, 
        index=current_index,
        format_func=lambda x: {"cloud": "☁️ 雲端 API", "local": "💻 本地落地模型", "mock": "🛠️ 模擬測試"}[x]
    )

    if selected_mode != app_config.get("llm_mode"):
        app_config["llm_mode"] = selected_mode
        save_config(app_config)
        st.success(f"模式已切換為：{selected_mode}")
        st.rerun()

# ----------------- 分頁 1：參數設定 -----------------
if app_mode == "⚙️ 參數設定":
    st.title("⚙️ 系統參數設定")
    st.write("您可以在此修改模型、API Key 及偵測器的各項參數。")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("☁️ 雲端 LLM 設定 (OpenAI)")
        app_config["cloud"]["api_key"] = st.text_input("OpenAI API Key", value=app_config["cloud"].get("api_key", ""), type="password")
        app_config["cloud"]["model_name"] = st.text_input("模型名稱 (Model Name)", value=app_config["cloud"].get("model_name", "gpt-4o"))
        
        st.divider()
        st.subheader("🔍 AI Detector 設定")
        app_config["ai_detector"]["api_key"] = st.text_input("GPTZero API Key", value=app_config["ai_detector"].get("api_key", ""), type="password")
        app_config["ai_detector"]["api_url"] = st.text_input("API 端點 (Endpoint)", value=app_config["ai_detector"].get("api_url", "https://api.gptzero.me/v2/predict/text"))

    with col_b:
        st.subheader("💻 本地 LLM 設定 (GGUF)")
        
        # 初始化 Session State 中的路徑
        if "model_path_widget" not in st.session_state:
            st.session_state.model_path_widget = app_config["local"].get("model_path", "")
            
        def on_browse_click():
            """ 檔案選取按鈕的回呼函數 """
            picked_path = select_file(st.session_state.model_path_widget)
            if picked_path:
                st.session_state.model_path_widget = picked_path

        # 使用列佈局將輸入框與按鈕並排
        path_col1, path_col2 = st.columns([0.85, 0.15])
        with path_col1:
            # 使用 key 與 session_state 連動
            model_path_input = st.text_input("模型檔案路徑", key="model_path_widget")
        with path_col2:
            st.write(" ") # 垂直對齊用
            st.write(" ")
            # 使用 callback 方式更新狀態，避免 "cannot be modified after instantiated" 錯誤
            st.button("📂", help="瀏覽檔案", on_click=on_browse_click)

        # 更新回 app_config
        app_config["local"]["model_path"] = model_path_input
        app_config["local"]["n_ctx"] = st.number_input("上下文窗口 (n_ctx)", value=app_config["local"].get("n_ctx", 4096), step=1024)
        app_config["local"]["max_tokens"] = st.number_input("單次最大輸出 (max_tokens)", value=app_config["local"].get("max_tokens", 1024), step=256)

    if st.button("💾 儲存並套用設定", type="primary"):
        # 確保儲存前同步最新的輸入內容
        save_config(app_config)
        st.success("設定檔已成功更新！")
        st.rerun()

# ----------------- 分頁 2：主頁面 -----------------
else:
    st.title("🎓 多代理人 AI 論文審查系統")

    # 區塊 1：論文資料填寫與上傳
    st.header("📄 1. 論文資料設定")
    col1, col2 = st.columns(2)
    with col1:
        paper_title = st.text_input("論文標題", placeholder="請輸入論文標題...")
    with col2:
        paper_field = st.text_input("主題領域", placeholder="例如：電腦視覺、邊緣運算")

    paper_content = ""
    uploaded_file = st.file_uploader("上傳論文檔案 (.txt)", type=["txt"])
    if uploaded_file is not None:
        paper_content = uploaded_file.getvalue().decode("utf-8")
    
    paper_content_input = st.text_area("或直接貼上論文內容", height=150)
    final_paper_content = paper_content if paper_content else paper_content_input

    # 區塊 2：AI 寫作偵測
    st.header("🔍 2. AI 寫作偵測")
    if st.button("執行 AI 寫作分析", icon="🔎"):
        if not final_paper_content.strip():
            st.warning("請先輸入或上傳論文內容！")
        else:
            detector = AIDetector()
            with st.spinner("正在進行 AI 風格分析..."):
                report = detector.analyze(final_paper_content)
                st.session_state.detector_report = report
                
                st.subheader("📊 偵測報告")
                st.write(f"**AI 生成比例：{report['ai_ratio']}%**")
                
                highlighted_html = "<div style='line-height:1.8; border:1px solid #ddd; padding:20px; border-radius:10px; background-color:#fafafa; color:#333; font-size:16px;'>"
                for seg in report['segments']:
                    if seg['type'] == 'AI':
                        highlighted_html += f"<span style='background-color:{seg['color']}; border-radius:3px;'>{seg['text']}</span>"
                    else:
                        highlighted_html += f"<span>{seg['text']}</span>"
                highlighted_html += "</div>"
                st.markdown(highlighted_html, unsafe_allow_html=True)

    # 區塊 3：審查委員配置
    st.header("👥 3. 審查委員配置")
    with st.expander("➕ 管理審查委員", expanded=False):
        for i, reviewer in enumerate(st.session_state.reviewers):
            st.text(f"委員 {i+1}: {reviewer.name} ({reviewer.expertise})")
        
        with st.form("add_reviewer_form"):
            r_name = st.text_input("委員名稱")
            r_expertise = st.text_input("專業領域")
            r_focus = st.text_input("研究重心")
            r_style = st.text_input("學術審查風格")
            if st.form_submit_button("加入名單") and r_name and r_expertise:
                st.session_state.reviewers.append(ReviewerAgent(r_name, r_expertise, r_focus, r_style))
                st.rerun()

    # 區塊 4：多代理人審查
    st.header("🚀 4. 執行多代理人學術審查")

    async def run_review_process():
        if not paper_title or not final_paper_content.strip():
            st.error("請提供論文標題與內容")
            return

        my_paper = Paper(title=paper_title, field=paper_field, content=final_paper_content)
        llm_service = LLMInterface(config_path="config.json")
        orchestrator = PaperReviewOrchestrator(paper=my_paper, reviewers=st.session_state.reviewers, llm=llm_service)

        st.divider()
        st.subheader(f"審查進度：{paper_title}")
        
        with st.status("第一輪：獨立深度審查...", expanded=True) as s1:
            r1 = await orchestrator.run_round_1()
            s1.update(label="✅ 第一輪：獨立深度審查完成", state="complete")
        
        with st.status("第二輪：交叉辯論...", expanded=True) as s2:
            r2 = await orchestrator.run_round_2()
            s2.update(label="✅ 第二輪：交叉辯論完成", state="complete")
            
        with st.status("第三輪：最終裁決...", expanded=True) as s3:
            r3 = await orchestrator.run_round_3()
            s3.update(label="✅ 第三輪：最終裁決完成", state="complete")
        
        st.session_state.review_history = orchestrator.history
        st.success("🎉 多輪審查已全數完成！請見下方結果或點擊匯出。")
        st.rerun()

    if st.button("啟動多輪 AI 審查", type="primary"):
        asyncio.run(run_review_process())

    # 審查結果展示與匯出
    if st.session_state.review_history:
        st.divider()
        st.header("📋 審查意見彙整與匯出")
        
        # 準備匯出內容
        export_text = f"# 論文審查報告：{paper_title}\n領域：{paper_field}\n\n"
        for rnd in ["round_1", "round_2", "round_3"]:
            export_text += f"## {'第一輪：獨立審查' if rnd=='round_1' else '第二輪：交叉辯論' if rnd=='round_2' else '第三輪：最終裁決'}\n"
            for name, content in st.session_state.review_history[rnd].items():
                export_text += f"### {name}\n{content}\n\n"
        
        col_exp1, col_exp2 = st.columns([3, 1])
        with col_exp1:
            st.info("審查已完成，您可以查看下方詳情或下載完整 Markdown 格式報告。")
        with col_exp2:
            st.download_button(
                label="📥 匯出完整報告 (.md)",
                data=export_text,
                file_name=f"Review_Report_{paper_title.replace(' ', '_')}.md",
                mime="text/markdown"
            )

        # 展開展示
        for rnd_id, rnd_name in [("round_1", "第一輪意見"), ("round_2", "第二輪辯論"), ("round_3", "最終裁決")]:
            with st.expander(rnd_name, expanded=(rnd_id == "round_3")):
                for name, content in st.session_state.review_history[rnd_id].items():
                    st.markdown(f"**{name}：**")
                    st.write(content)
                    st.divider()