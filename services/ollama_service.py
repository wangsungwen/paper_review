# services/ollama_service.py
"""Ollama 伺服器偵測、模型清單與自動安裝。"""

import os
import subprocess
import sys
import urllib.request

import requests

OLLAMA_WIN_URL = "https://ollama.com/download/OllamaSetup.exe"
OLLAMA_UNIX_INSTALL = "curl -fsSL https://ollama.com/install.sh | sh"


def is_running(base_url: str = "http://localhost:11434", timeout: int = 2) -> bool:
    try:
        r = requests.get(f"{base_url}/api/tags", timeout=timeout)
        r.raise_for_status()
        return True
    except requests.exceptions.RequestException:
        return False


def list_local_models(base_url: str = "http://localhost:11434", timeout: int = 2) -> list:
    """回傳本地 Ollama 可用模型名稱清單；連不上時拋出例外。"""
    r = requests.get(f"{base_url}/api/tags", timeout=timeout)
    r.raise_for_status()
    data = r.json()
    return [m["name"] for m in data.get("models", [])]


def install(progress_callback=None) -> tuple:
    """自動下載並啟動 Ollama 安裝。

    回傳 (success: bool, message: str)。
    progress_callback(percent: float) 用於回報下載進度 (僅 Windows)。
    """
    try:
        if sys.platform != "win32":
            res = subprocess.run(
                OLLAMA_UNIX_INSTALL, shell=True, capture_output=True, text=True
            )
            if res.returncode == 0:
                return True, (
                    "Ollama 安裝完成！建議您透過終端機執行 `ollama serve` "
                    "來確保背景服務活著。"
                )
            return False, (
                f"安裝腳本執行失敗，請手動在終端機執行: {OLLAMA_UNIX_INSTALL}\n\n{res.stderr}"
            )

        setup_path = os.path.abspath("OllamaSetup.exe")

        def report_progress(block_num, block_size, total_size):
            if total_size > 0 and progress_callback:
                percent = min(100, block_num * block_size * 100 / total_size)
                progress_callback(percent)

        urllib.request.urlretrieve(OLLAMA_WIN_URL, setup_path, reporthook=report_progress)
        subprocess.Popen([setup_path])
        return True, "下載完成！正在為您啟動安裝程式...請注意快顯視窗"

    except Exception as e:
        return False, f"自動下載或啟動失敗：{e}"
