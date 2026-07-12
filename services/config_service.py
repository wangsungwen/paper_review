# services/config_service.py
"""全域設定檔管理：路徑解析、預設值、環境變數注入、臨時使用者設定檔。"""

import json
import os
import sys
import tempfile

CONFIG_NAME = "config.json"

DEFAULT_CONFIG = {
    "llm_mode": "mock",
    "cloud": {
        "provider": "openai",
        "api_key": "",
        "model_name": "gpt-4o",
        "api_url": "https://api.openai.com/v1/chat/completions",
    },
    "gemini_native": {
        "api_key": "",
        "model_name": "gemini-1.5-flash",
    },
    "local": {
        "model_path": "./local_models/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf",
        "n_ctx": 4096,
        "max_tokens": 1024,
        "n_gpu_layers": -1,
        "force_cpu_on_blackwell": False,
    },
    "ollama": {
        "model_name": "llama3.1",
        "base_url": "http://localhost:11434",
    },
    "ai_detector": {
        "api_key": "",
        "api_url": "https://api.gptzero.me/v2/predict/text",
        "mode": "hf_model",
        "force_cpu": False,
    },
    "knowledge_update": {
        "enable_rag": False,
        "enable_web_search": False,
        "enable_reference_upload": False,
        "web_search_provider": "auto",
        "tavily_api_key": "",
    },
}

# 環境變數 → 設定路徑對照 (金鑰不必寫入檔案，可由環境變數注入)
ENV_OVERRIDES = {
    "PRS_CLOUD_API_KEY": ("cloud", "api_key"),
    "PRS_GEMINI_API_KEY": ("gemini_native", "api_key"),
    "PRS_GPTZERO_API_KEY": ("ai_detector", "api_key"),
    "PRS_TAVILY_API_KEY": ("knowledge_update", "tavily_api_key"),
}


def get_config_path() -> str:
    """開發模式使用當前目錄；PyInstaller 打包後使用 exe 旁的 config.json。"""
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
        return os.path.join(base_dir, CONFIG_NAME)
    return os.path.abspath(CONFIG_NAME)


def ensure_config_exists(config_path: str = None) -> str:
    """若設定檔不存在，寫入預設範本。回傳實際路徑。"""
    path = config_path or get_config_path()
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
    return path


def apply_env_overrides(config: dict) -> dict:
    """將環境變數中的金鑰注入設定 (優先於檔案內容，避免金鑰落地)。"""
    for env_key, (section, field) in ENV_OVERRIDES.items():
        value = os.environ.get(env_key, "").strip()
        if value:
            config.setdefault(section, {})[field] = value
    return config


def load_global_config(config_path: str = None) -> dict:
    path = ensure_config_exists(config_path)
    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return apply_env_overrides(config)


def save_global_config(config: dict, config_path: str = None):
    path = config_path or get_config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


def write_temp_user_config(user_conf: dict, existing_path: str = None) -> str:
    """為線上使用者生成臨時設定檔，保護伺服器實體 config.json 不被污染。"""
    path = existing_path
    if not path:
        fd, path = tempfile.mkstemp(prefix="user_config_", suffix=".json")
        os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(user_conf, f, indent=4, ensure_ascii=False)
    return path
