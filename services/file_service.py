# services/file_service.py
"""檔案處理：文字萃取 (PDF/DOCX/TXT)、路徑工具、內容清洗。"""

import os
import re
import sys
from io import BytesIO

import docx
import pypdf


def resource_path(relative_path: str) -> str:
    """取得相對於執行路徑的絕對路徑 (支援 PyInstaller 打包環境)。"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def check_model_exists(path: str) -> bool:
    """檢查本地模型路徑是否有效 (含相對路徑轉換)。"""
    if not path:
        return False
    if os.path.exists(path):
        return True
    if os.path.exists(resource_path(path)):
        return True
    return False


def extract_text_from_file(uploaded_file) -> str:
    """根據檔案副檔名提取文字內容 (Streamlit UploadedFile 或類檔案物件)。"""
    file_extension = uploaded_file.name.split(".")[-1].lower()

    # 確保檔案指標在起始位置，防止二次讀取變為空
    uploaded_file.seek(0)

    raw_text = ""
    try:
        if file_extension == "txt":
            raw_text = uploaded_file.getvalue().decode("utf-8", errors="ignore")

        elif file_extension == "pdf":
            pdf_reader = pypdf.PdfReader(BytesIO(uploaded_file.read()))
            text_list = []
            for page in pdf_reader.pages:
                content = page.extract_text()
                if content:
                    text_list.append(content)
            raw_text = "\n".join(text_list)

        elif file_extension == "docx":
            try:
                doc = docx.Document(BytesIO(uploaded_file.read()))
                raw_text = "\n".join([para.text for para in doc.paragraphs])
            except Exception as e:
                if "no relationship of type" in str(e):
                    raise ValueError(
                        "該 Word 檔案結構不完整。請嘗試在 Word 中「另存新檔」"
                        "為標準 .docx 格式後再次上傳。"
                    )
                raise e

        # 過濾掉無法被 UTF-8 正常編碼的 Surrogate 或非法位元組，
        # 防止 Streamlit Websocket 傳輸時 Protobuf 崩潰
        if isinstance(raw_text, str):
            raw_text = raw_text.encode("utf-8", errors="ignore").decode("utf-8")
        return raw_text

    except Exception as e:
        raise Exception(f"解析 {file_extension.upper()} 失敗：{str(e)}")


def apply_text_filters(text: str, manual_exclusions=None, exclude_quotes=False,
                       exclusion_keywords: str = "") -> str:
    """內容預處理：移除指定字串、引用文字，並自 (參考文獻等) 截斷關鍵字處截斷。"""
    if not text:
        return text

    for me in (manual_exclusions or []):
        text = text.replace(me, "")

    if exclude_quotes:
        text = re.sub(r'["“”「」](.*?)["“”「」]', "", text)

    if exclusion_keywords and exclusion_keywords.strip():
        keywords = [k.strip() for k in exclusion_keywords.split("\n") if k.strip()]
        for kw in keywords:
            idx = text.lower().find(kw.lower())
            if idx != -1:
                text = text[:idx]

    return text
