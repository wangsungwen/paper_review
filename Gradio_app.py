"""Gradio UI for the multi-agent paper review system.

The application keeps API keys in per-request temporary configuration files and
never writes them to the repository configuration.  The former Streamlit UI is
kept in ``streamlit_app.py`` for local backwards compatibility.
"""

from __future__ import annotations

import asyncio
import copy
import html
import json
import os
import tempfile
from pathlib import Path
from typing import Iterable

import gradio as gr
import requests

try:
    import spaces

    gpu_task = spaces.GPU(duration=120)
except (ImportError, RuntimeError):
    def gpu_task(function):
        return function

from core.orchestrator import PaperReviewOrchestrator
from llm.interface import LLMInterface
from models.paper import Paper
from models.reviewer import ReviewerAgent
from services import config_service
from services.file_service import apply_text_filters, extract_text_from_file


APP_TITLE = "多代理人論文審查系統"
DEFAULT_REVIEWERS = [
    ["Dr. Alan", "電腦視覺與深度學習", "輕量化神經網路架構", "嚴格，要求完整數據驗證"],
    ["Prof. Lin", "嵌入式與邊緣運算", "微控制器整合與邊緣 AI", "務實且具建設性，重視落地性"],
]


class UploadedFileAdapter:
    """Give a Gradio filepath the small file API expected by file_service."""

    def __init__(self, path: str):
        self.path = path
        self.name = Path(path).name
        self._handle = open(path, "rb")

    def seek(self, offset: int):
        return self._handle.seek(offset)

    def read(self, size: int = -1):
        return self._handle.read(size)

    def getvalue(self):
        position = self._handle.tell()
        self._handle.seek(0)
        data = self._handle.read()
        self._handle.seek(position)
        return data

    def close(self):
        self._handle.close()


def _extract_path(path: str | None) -> str:
    if not path:
        return ""
    adapter = UploadedFileAdapter(path)
    try:
        return extract_text_from_file(adapter)
    finally:
        adapter.close()


def parse_paper_file(path: str | None):
    if not path:
        return "", "尚未上傳檔案。"
    try:
        content = _extract_path(path)
        return content, f"✅ 已解析 **{Path(path).name}**，共 {len(content):,} 個字元。"
    except Exception as exc:
        return "", f"❌ {exc}"


def parse_reference_files(paths: Iterable[str] | None):
    paths = list(paths or [])
    if not paths:
        return "", "未加入參考文獻。"
    blocks, errors = [], []
    for path in paths:
        try:
            blocks.append(f"【{Path(path).name}】\n{_extract_path(path)}")
        except Exception as exc:
            errors.append(f"{Path(path).name}: {exc}")
    status = f"✅ 已解析 {len(blocks)} 份參考文獻。"
    if errors:
        status += "\n\n⚠️ " + "；".join(errors)
    return "\n\n".join(blocks), status


def _build_config(
    provider: str,
    api_key: str,
    model_name: str,
    api_url: str,
    detector_mode: str,
    detector_key: str,
    detector_url: str,
    enable_rag: bool,
    enable_web: bool,
    enable_references: bool,
    tavily_key: str,
) -> dict:
    config = copy.deepcopy(config_service.DEFAULT_CONFIG)
    provider_code = {"Gemini": "gemini", "OpenAI 相容 API": "openai", "模擬模式": "mock"}[provider]
    config["llm_mode"] = "mock" if provider_code == "mock" else "cloud"
    config["cloud"].update({
        "provider": provider_code,
        "api_key": (api_key or "").strip(),
        "model_name": (model_name or "").strip(),
        "api_url": (api_url or "").strip(),
    })
    config["ai_detector"].update({
        # Cloud mode without a key intentionally falls back to the deterministic
        # mock report without importing/downloading the Hugging Face model.
        "mode": {"ZeroGPU 模型": "hf_model", "GPTZero API": "cloud", "模擬偵測": "cloud"}[detector_mode],
        "api_key": (detector_key or "").strip(),
        "api_url": (detector_url or "").strip(),
        "force_cpu": False,
    })
    config["knowledge_update"].update({
        "enable_rag": bool(enable_rag),
        "enable_web_search": bool(enable_web),
        "enable_reference_upload": bool(enable_references),
        "tavily_api_key": (tavily_key or "").strip(),
    })
    return config


def _temporary_config(config: dict) -> str:
    return config_service.write_temp_user_config(config)


def _reviewers_from_table(rows) -> list[ReviewerAgent]:
    reviewers = []
    # Gradio 6 returns a pandas.DataFrame.  Evaluating a DataFrame as a bool
    # (``rows or []``) raises: "The truth value of a DataFrame is ambiguous".
    if rows is None:
        normalized_rows = []
    elif hasattr(rows, "itertuples"):
        normalized_rows = rows.fillna("").itertuples(index=False, name=None)
    elif isinstance(rows, dict):
        normalized_rows = zip(*rows.values()) if rows else []
    else:
        normalized_rows = rows

    for row in normalized_rows:
        values = list(row) + ["", "", "", ""]
        name, expertise, focus, style = [str(value or "").strip() for value in values[:4]]
        if name:
            reviewers.append(ReviewerAgent(name, expertise, focus, style))
    if not reviewers:
        raise gr.Error("請至少設定一位審查委員。")
    return reviewers


def _openai_models_url(api_url: str) -> str:
    """Convert a chat-completions endpoint to its OpenAI-compatible models URL."""
    url = (api_url or "https://api.openai.com/v1/chat/completions").strip().rstrip("/")
    for suffix in ("/chat/completions", "/responses", "/completions"):
        if url.endswith(suffix):
            return url[: -len(suffix)] + "/models"
    return url if url.endswith("/models") else url + "/models"


def provider_defaults(provider: str):
    if provider == "Gemini":
        choices = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"]
        return gr.Dropdown(choices=choices, value=choices[0], allow_custom_value=True), gr.Textbox(value="https://api.openai.com/v1/chat/completions", visible=False)
    if provider == "OpenAI 相容 API":
        choices = ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"]
        return gr.Dropdown(choices=choices, value=choices[0], allow_custom_value=True), gr.Textbox(value="https://api.openai.com/v1/chat/completions", visible=True)
    return gr.Dropdown(choices=["mock"], value="mock", allow_custom_value=True), gr.Textbox(value="https://api.openai.com/v1/chat/completions", visible=False)


def detect_available_models(provider: str, api_key: str, api_url: str):
    """Validate the API key and populate the model dropdown."""
    if provider == "模擬模式":
        return gr.Dropdown(choices=["mock"], value="mock", allow_custom_value=True), "✅ 模擬模式不需要 API Key。"
    if not (api_key or "").strip():
        raise gr.Error("請先輸入 API Key。")

    try:
        if provider == "Gemini":
            response = requests.get(
                "https://generativelanguage.googleapis.com/v1beta/models",
                params={"key": api_key.strip(), "pageSize": 1000},
                timeout=20,
            )
            response.raise_for_status()
            models = []
            for item in response.json().get("models", []):
                methods = item.get("supportedGenerationMethods", [])
                if "generateContent" in methods:
                    models.append(item.get("name", "").removeprefix("models/"))
        else:
            response = requests.get(
                _openai_models_url(api_url),
                headers={"Authorization": f"Bearer {api_key.strip()}"},
                timeout=20,
            )
            response.raise_for_status()
            models = [str(item.get("id", "")).strip() for item in response.json().get("data", [])]

        models = sorted({model for model in models if model}, key=str.lower)
        if not models:
            raise ValueError("API 回應成功，但沒有可用模型。您仍可手動輸入模型名稱。")
        preferred = next((m for m in models if "flash" in m.lower()), models[0])
        return (
            gr.Dropdown(choices=models, value=preferred, allow_custom_value=True),
            f"✅ API Key 驗證成功，共找到 {len(models)} 個可用模型。",
        )
    except requests.HTTPError as exc:
        detail = ""
        try:
            detail = exc.response.json().get("error", {}).get("message", "")
        except Exception:
            detail = exc.response.text[:300] if exc.response is not None else ""
        raise gr.Error(f"模型偵測失敗（HTTP {exc.response.status_code}）：{detail or exc}") from exc
    except Exception as exc:
        raise gr.Error(f"模型偵測失敗：{exc}") from exc


def _round_markdown(title: str, entries: dict) -> str:
    parts = [f"## {title}"]
    for name, content in entries.items():
        parts.append(f"### {name}\n\n{content}")
    return "\n\n".join(parts)


def _report_file(title: str, history: dict, stats: dict) -> str:
    safe_title = "".join(c for c in title if c.isalnum() or c in "-_ ").strip() or "paper_review"
    fd, path = tempfile.mkstemp(prefix="paper_review_", suffix=".md")
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        file.write(f"# {safe_title}：多代理人審查報告\n\n")
        file.write("## 評分\n\n")
        file.write(json.dumps(stats, ensure_ascii=False, indent=2))
        for key, label in (("round_1", "第一輪：獨立審查"), ("round_2", "第二輪：交叉辯論"), ("round_3", "第三輪：最終裁決")):
            file.write("\n\n" + _round_markdown(label, history.get(key, {})))
    return path


def run_review(
    title, field, content, references, exclude_quotes, exclusion_keywords,
    manual_exclusions, reviewer_rows, provider, api_key, model_name, api_url,
    enable_rag, enable_web, enable_references, tavily_key,
):
    if not (title or "").strip():
        raise gr.Error("請輸入論文標題。")
    filtered = apply_text_filters(
        content or "",
        manual_exclusions=[line for line in (manual_exclusions or "").splitlines() if line.strip()],
        exclude_quotes=bool(exclude_quotes),
        exclusion_keywords=exclusion_keywords or "",
    )
    if not filtered.strip():
        raise gr.Error("請上傳論文或貼上論文內容。")
    config = _build_config(
        provider, api_key, model_name, api_url, "模擬偵測", "", "",
        enable_rag, enable_web, enable_references, tavily_key,
    )
    if config["llm_mode"] != "mock" and not config["cloud"]["api_key"]:
        raise gr.Error("請輸入所選推論服務的 API Key。")

    config_path = _temporary_config(config)
    try:
        paper = Paper(title.strip(), (field or "").strip(), filtered, references or "")
        llm = LLMInterface(config_path=config_path)
        orchestrator = PaperReviewOrchestrator(
            paper, _reviewers_from_table(reviewer_rows), llm,
            knowledge_config=config["knowledge_update"],
        )
        yield "⏳ 第一輪：獨立深度審查與外部知識檢索…", {}, "", "", "", None
        round_1 = asyncio.run(orchestrator.run_round_1())
        yield "⏳ 第二輪：審查委員交叉辯論…", {}, _round_markdown("第一輪：獨立審查", round_1), "", "", None
        round_2 = asyncio.run(orchestrator.run_round_2())
        yield "⏳ 第三輪：主席整合與最終裁決…", {}, _round_markdown("第一輪：獨立審查", round_1), _round_markdown("第二輪：交叉辯論", round_2), "", None
        round_3 = asyncio.run(orchestrator.run_round_3())
        history, stats = orchestrator.history, orchestrator.review_stats
        yield (
            "✅ 審查完成。", stats,
            _round_markdown("第一輪：獨立審查", round_1),
            _round_markdown("第二輪：交叉辯論", round_2),
            _round_markdown("第三輪：最終裁決", round_3),
            _report_file(title, history, stats),
        )
    except gr.Error:
        raise
    except Exception as exc:
        raise gr.Error(f"審查執行失敗：{exc}") from exc
    finally:
        try:
            os.remove(config_path)
        except OSError:
            pass


def _segments_html(report: dict) -> str:
    blocks = []
    for segment in report.get("segments", []):
        text = html.escape(str(segment.get("text", "")))
        color = segment.get("color", "transparent")
        reason = html.escape(str(segment.get("reason", segment.get("type", ""))))
        blocks.append(f'<span title="{reason}" style="background:{color};padding:2px;border-radius:3px">{text}</span>')
    return '<div style="line-height:1.9;white-space:pre-wrap">' + "".join(blocks) + "</div>"


@gpu_task
def run_ai_detection(text, mode, api_key, api_url):
    if not (text or "").strip():
        raise gr.Error("請先貼上或載入要分析的文字。")
    config = _build_config(
        "模擬模式", "", "", "", mode, api_key, api_url,
        False, False, False, "",
    )
    config_path = _temporary_config(config)
    try:
        from core.ai_detector import AIDetector
        detector = AIDetector(config_path=config_path)
        report = detector.analyze(text)
        summary = {
            "AI 比例 (%)": report.get("ai_ratio", 0),
            "模型": report.get("model_name", "未知"),
            "摘要": report.get("summary", report.get("notice", "")),
        }
        return summary, _segments_html(report)
    except Exception as exc:
        raise gr.Error(f"AI 偵測失敗：{exc}") from exc
    finally:
        try:
            os.remove(config_path)
        except OSError:
            pass


CSS = """
.gradio-container {max-width: 1400px !important;}
.hero {padding: 1.2rem 1.4rem; border-radius: 16px; background: linear-gradient(120deg,#eaf2ff,#f7edff); margin-bottom: 1rem;}
.hero h1 {margin: 0; color: #173b64;}
.muted {color: #64748b;}
"""


with gr.Blocks(title=APP_TITLE) as demo:
    gr.HTML("<div class='hero'><h1>🎓 多代理人論文審查系統</h1><div class='muted'>Gradio / Hugging Face Spaces 版 · API Key 僅存於單次工作階段</div></div>")

    with gr.Accordion("⚙️ 推論與知識設定", open=True):
        with gr.Row():
            provider = gr.Radio(["Gemini", "OpenAI 相容 API", "模擬模式"], value="Gemini", label="推論服務")
            model_name = gr.Dropdown(
                choices=["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
                value="gemini-2.5-flash", allow_custom_value=True,
                label="模型名稱（可從偵測結果選擇或自行輸入）",
            )
        api_key = gr.Textbox(label="API Key", type="password", placeholder="不會寫入儲存庫或永久磁碟")
        with gr.Row():
            detect_models_button = gr.Button("🔍 驗證 API Key 並偵測可用模型")
            model_detection_status = gr.Markdown("輸入 API Key 後可自動取得模型清單。")
        api_url = gr.Textbox(value="https://api.openai.com/v1/chat/completions", label="OpenAI 相容 API Endpoint", visible=False)
        provider.change(provider_defaults, provider, [model_name, api_url])
        detect_models_button.click(
            detect_available_models,
            [provider, api_key, api_url],
            [model_name, model_detection_status],
        )
        with gr.Row():
            enable_rag = gr.Checkbox(value=True, label="Arxiv 最新文獻")
            enable_web = gr.Checkbox(value=False, label="聯網搜尋")
            enable_references = gr.Checkbox(value=True, label="使用上傳參考文獻")
        tavily_key = gr.Textbox(label="Tavily API Key（選填）", type="password")

    with gr.Tabs():
        with gr.Tab("📝 多代理人審查"):
            with gr.Row():
                title = gr.Textbox(label="論文標題")
                field = gr.Textbox(label="主題領域", placeholder="例如：電腦視覺、人工智慧")
            paper_file = gr.File(label="上傳論文（TXT / PDF / DOCX）", file_types=[".txt", ".pdf", ".docx"], type="filepath")
            paper_status = gr.Markdown("尚未上傳檔案。")
            content = gr.Textbox(label="論文內容（可直接編輯）", lines=16)
            paper_file.change(parse_paper_file, paper_file, [content, paper_status])

            with gr.Accordion("內容清理", open=False):
                exclude_quotes = gr.Checkbox(value=False, label="排除引號內文字")
                exclusion_keywords = gr.Textbox(label="遇到以下章節標題時截斷（每行一項）", value="Bibliography\nReferences\n參考文獻")
                manual_exclusions = gr.Textbox(label="移除特定字串（每行一項）", lines=3)

            reference_files = gr.File(label="補充參考文獻（可多選）", file_types=[".txt", ".pdf", ".docx"], file_count="multiple", type="filepath")
            reference_status = gr.Markdown("未加入參考文獻。")
            references = gr.Textbox(label="參考文獻解析內容", lines=6, visible=False)
            reference_files.change(parse_reference_files, reference_files, [references, reference_status])

            reviewers = gr.Dataframe(
                headers=["委員名稱", "專業領域", "研究重心", "審查風格"],
                value=DEFAULT_REVIEWERS, row_count=(2, "dynamic"), column_count=(4, "fixed"),
                datatype=["str", "str", "str", "str"], label="審查委員（可新增或刪除列）",
            )
            review_button = gr.Button("🚀 啟動三輪 AI 審查", variant="primary")
            review_status = gr.Markdown()
            score_output = gr.JSON(label="最終評分")
            with gr.Tabs():
                with gr.Tab("第一輪"):
                    round_1_output = gr.Markdown()
                with gr.Tab("第二輪"):
                    round_2_output = gr.Markdown()
                with gr.Tab("最終裁決"):
                    round_3_output = gr.Markdown()
            report_download = gr.File(label="下載完整 Markdown 報告")
            review_button.click(
                run_review,
                inputs=[title, field, content, references, exclude_quotes, exclusion_keywords,
                        manual_exclusions, reviewers, provider, api_key, model_name, api_url,
                        enable_rag, enable_web, enable_references, tavily_key],
                outputs=[review_status, score_output, round_1_output, round_2_output, round_3_output, report_download],
                concurrency_limit=2,
            )

        with gr.Tab("🔍 AI 文字偵測"):
            detector_file = gr.File(
                label="上傳待偵測論文（TXT / PDF / DOCX）",
                file_types=[".txt", ".pdf", ".docx"], type="filepath",
            )
            detector_file_status = gr.Markdown("可上傳論文，或直接在下方貼上文字。")
            detector_text = gr.Textbox(label="待分析文字", lines=16)
            detector_file.change(parse_paper_file, detector_file, [detector_text, detector_file_status])
            with gr.Row():
                detector_mode = gr.Radio(["ZeroGPU 模型", "GPTZero API", "模擬偵測"], value="模擬偵測", label="偵測方式")
                detector_key = gr.Textbox(label="GPTZero API Key", type="password")
            detector_url = gr.Textbox(value="https://api.gptzero.me/v2/predict/text", label="GPTZero Endpoint")
            detector_button = gr.Button("🔎 執行 AI 偵測", variant="primary")
            detector_summary = gr.JSON(label="偵測結果")
            detector_highlight = gr.HTML(label="逐句分析")
            detector_button.click(
                run_ai_detection,
                [detector_text, detector_mode, detector_key, detector_url],
                [detector_summary, detector_highlight],
                concurrency_limit=1,
            )

        with gr.Tab("ℹ️ 使用說明"):
            gr.Markdown("""
### 使用方式

1. 選擇 Gemini 或 OpenAI 相容服務，輸入自己的 API Key 與模型名稱。
2. 上傳 TXT、PDF 或 DOCX 論文，也可以直接貼上文字。
3. 調整審查委員角色後啟動三輪審查。
4. AI 文字偵測可使用 ZeroGPU 模型、GPTZero，或不耗用配額的模擬模式。

API Key 只會寫入單次請求使用的臨時檔案，請求結束後立即刪除。免費 Space 不提供 Ollama 或 GGUF 本機模型服務。
""")


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=2, max_size=20).launch(css=CSS)
