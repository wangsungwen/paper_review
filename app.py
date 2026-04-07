# app.py

import streamlit as st
import asyncio
import json
import os
import sys
import tkinter as tk
from tkinter import filedialog
from io import BytesIO

# 新增解析套件
import pypdf
import docx

# 匯入自定義模組
from models.paper import Paper
from models.reviewer import ReviewerAgent
from llm.interface import LLMInterface
from core.orchestrator import PaperReviewOrchestrator
from core.ai_detector import AIDetector

# ----------------- 工具函式 -----------------

def select_file(current_path=""):
    """ 開啟檔案選擇視窗並返回路徑 """
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        initial_dir = os.path.dirname(current_path) if current_path and os.path.exists(os.path.dirname(current_path)) else os.getcwd()
        file_path = filedialog.askopenfilename(
            initialdir=initial_dir,
            title="選擇 GGUF 模型檔案",
            filetypes=[("GGUF files", "*.gguf"), ("All files", "*.*")]
        )
        root.destroy()
        return file_path
    except Exception:
        return None

def resource_path(relative_path):
    """ 取得相對於執行路徑的絕對路徑 (支援 PyInstaller 打包環境) """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def extract_text_from_file(uploaded_file):
    """ 根據檔案副檔名提取文字內容 [新功能] """
    file_extension = uploaded_file.name.split('.')[-1].lower()
    
    if file_extension == "txt":
        return uploaded_file.getvalue().decode("utf-8")
    
    elif file_extension == "pdf":
        pdf_reader = pypdf.PdfReader(BytesIO(uploaded_file.read()))
        text = ""
        for page in pdf_reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
        return text
    
    elif file_extension == "docx":
        doc = docx.Document(BytesIO(uploaded_file.read()))
        return "\n".join([para.text for para in doc.paragraphs])
    
    return ""

# ----------------- 設定檔管理 -----------------

st.set_page_config(page_title="多代理人論文審查系統", page_icon="🎓", layout="wide")

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

# 初始化 Session State
if "review_history" not in st.session_state:
    st.session_state.review_history = None

if "reviewers" not in st.session_state:
    st.session_state.reviewers = [
        ReviewerAgent("Dr. Alan", "電腦視覺與深度學習", "輕量化神經網路", "嚴格，要求完整數據驗證。"),
        ReviewerAgent("Prof. Lin", "嵌入式與邊緣運算", "微控制器整合", "務實，重視硬體資源消耗。")
    ]

# ----------------- 側邊欄 -----------------

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
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("☁️ 雲端 LLM 設定 (OpenAI)")
        app_config["cloud"]["api_key"] = st.text_input("OpenAI API Key", value=app_config["cloud"].get("api_key", ""), type="password")
        app_config["cloud"]["model_name"] = st.text_input("模型名稱", value=app_config["cloud"].get("model_name", "gpt-4o"))
        
        st.divider()
        st.subheader("🔍 AI Detector 設定")
        app_config["ai_detector"]["api_key"] = st.text_input("GPTZero API Key", value=app_config["ai_detector"].get("api_key", ""), type="password")
        app_config["ai_detector"]["api_url"] = st.text_input("API 端點", value=app_config["ai_detector"].get("api_url", "https://api.gptzero.me/v2/predict/text"))

    with col_b:
        st.subheader("💻 本地 LLM 設定 (GGUF)")
        
        if "model_path_widget" not in st.session_state:
            st.session_state.model_path_widget = app_config["local"].get("model_path", "")
            
        def on_browse_click():
            picked_path = select_file(st.session_state.model_path_widget)
            if picked_path:
                st.session_state.model_path_widget = picked_path

        path_col1, path_col2 = st.columns([0.85, 0.15])
        with path_col1:
            model_path_input = st.text_input("模型檔案路徑", key="model_path_widget")
        with path_col2:
            st.write(" ")
            st.write(" ")
            st.button("📂", help="瀏覽檔案", on_click=on_browse_click)

        app_config["local"]["model_path"] = model_path_input
        app_config["local"]["n_ctx"] = st.number_input("上下文窗口 (n_ctx)", value=app_config["local"].get("n_ctx", 4096), step=1024)
        app_config["local"]["max_tokens"] = st.number_input("最大輸出 (max_tokens)", value=app_config["local"].get("max_tokens", 1024), step=256)

    if st.button("💾 儲存並套用設定", type="primary"):
        save_config(app_config)
        st.success("設定檔已成功更新！")
        st.rerun()

# ----------------- 分頁 2：主頁面 -----------------

else:
    st.title("🎓 多代理人 AI 論文審查系統")

    # 1. 論文資料設定
    st.header("📄 1. 論文資料設定")
    col1, col2 = st.columns(2)
    with col1:
        paper_title = st.text_input("論文標題", placeholder="請輸入論文標題...")
    with col2:
        paper_field = st.text_input("主題領域", placeholder="例如：電腦視覺、人工智慧")

    paper_content = ""
    # 更新支援格式：txt, pdf, docx
    uploaded_file = st.file_uploader("上傳論文檔案 (.txt, .pdf, .docx)", type=["txt", "pdf", "docx"])
    
    if uploaded_file is not None:
        with st.spinner("正在解析檔案內容..."):
            try:
                paper_content = extract_text_from_file(uploaded_file)
                if paper_content.strip():
                    st.success(f"檔案「{uploaded_file.name}」解析成功！")
                else:
                    st.warning("檔案解析完成，但未偵測到有效文字。")
            except Exception as e:
                st.error(f"解析失敗：{e}")
    
    paper_content_input = st.text_area("或直接貼上/編輯論文內容", value=paper_content, height=200)
    final_paper_content = paper_content_input

    # 2. AI 寫作偵測
    st.header("🔍 2. AI 寫作偵測")
    if st.button("執行 AI 寫作分析", icon="🔎"):
        if not final_paper_content.strip():
            st.warning("請先輸入或上傳論文內容！")
        else:
            detector = AIDetector()
            with st.spinner("分析中..."):
                report = detector.analyze(final_paper_content)
                st.subheader(f"📊 偵測報告 (AI 比例：{report['ai_ratio']}%)")
                
                # 渲染顏色標示
                highlighted_html = "<div style='line-height:1.8; border:1px solid #ddd; padding:20px; border-radius:10px; background-color:#fafafa; color:#333; font-size:16px;'>"
                for seg in report['segments']:
                    if seg['type'] == 'AI':
                        highlighted_html += f"<span style='background-color:{seg['color']}; border-radius:3px;'>{seg['text']}</span>"
                    else:
                        highlighted_html += f"<span>{seg['text']}</span>"
                highlighted_html += "</div>"
                st.markdown(highlighted_html, unsafe_allow_html=True)

    # 3. 審查委員配置
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

    # 4. 執行多代理人審查
    st.header("🚀 4. 執行多代理人學術審查")

    async def run_review_process():
        if not paper_title or not final_paper_content.strip():
            st.error("請提供論文標題與內容")
            return

        my_paper = Paper(title=paper_title, field=paper_field, content=final_paper_content)
        llm_service = LLMInterface(config_path="config.json")
        orchestrator = PaperReviewOrchestrator(paper=my_paper, reviewers=st.session_state.reviewers, llm=llm_service)

        st.divider()
        st.subheader(f"審查進行中：{paper_title}")
        
        with st.status("第一輪：獨立深度審查...", expanded=True) as s1:
            await orchestrator.run_round_1()
            s1.update(label="✅ 第一輪完成", state="complete")
        
        with st.status("第二輪：交叉辯論...", expanded=True) as s2:
            await orchestrator.run_round_2()
            s2.update(label="✅ 第二輪完成", state="complete")
            
        with st.status("第三輪：最終裁決...", expanded=True) as s3:
            await orchestrator.run_round_3()
            s3.update(label="✅ 第三輪完成", state="complete")
        
        st.session_state.review_history = orchestrator.history
        st.rerun()

    if st.button("啟動多輪 AI 審查", type="primary"):
        asyncio.run(run_review_process())

    # 結果展示與匯出
    if st.session_state.review_history:
        st.divider()
        st.header("📋 審查結果展示")
        
        export_text = f"# 論文審查報告：{paper_title}\n領域：{paper_field}\n\n"
        for rnd in ["round_1", "round_2", "round_3"]:
            title = "第一輪：獨立審查" if rnd=="round_1" else "第二輪：交叉辯論" if rnd=="round_2" else "第三輪：最終裁決"
            export_text += f"## {title}\n"
            for name, content in st.session_state.review_history[rnd].items():
                export_text += f"### {name}\n{content}\n\n"
        
        st.download_button(
            label="📥 下載完整 Markdown 報告",
            data=export_text,
            file_name=f"Review_Report_{paper_title}.md",
            mime="text/markdown"
        )

        for rnd_id, rnd_name in [("round_1", "第一輪意見"), ("round_2", "第二輪辯論"), ("round_3", "最終裁決")]:
            with st.expander(rnd_name, expanded=(rnd_id == "round_3")):
                for name, content in st.session_state.review_history[rnd_id].items():
                    st.markdown(f"**{name}：**")
                    st.write(content)
                    st.divider()