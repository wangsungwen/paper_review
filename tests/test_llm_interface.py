# tests/test_llm_interface.py
"""LLMInterface 介面完整性回歸測試 (防止方法遺失造成 AttributeError)。"""
from llm.interface import LLMInterface

REQUIRED_METHODS = [
    "generate_response",
    "_generate_cloud_async",
    "_generate_cloud_sync",       # 曾因檔案損毀遺失 → 雲端 OpenAI 模式全掛
    "_generate_gemini_sync",
    "_generate_gemini_native_async",
    "_generate_ollama_sync",
    "_generate_local_sync",
    "_generate_mock_async",
    "list_models",
    "list_openai_models",
    "get_input_token_budget",
]


def test_all_engine_methods_exist():
    missing = [m for m in REQUIRED_METHODS if not hasattr(LLMInterface, m)]
    assert not missing, f"LLMInterface 缺少方法: {missing}"


def test_models_endpoint_derivation():
    f = LLMInterface.models_endpoint_from_chat_url
    assert f("https://api.openai.com/v1/chat/completions") == "https://api.openai.com/v1/models"
    assert f("https://api.deepseek.com/v1/chat/completions") == "https://api.deepseek.com/v1/models"
    assert f("https://api.groq.com/openai/v1/chat/completions/") == "https://api.groq.com/openai/v1/models"
    assert f("https://openrouter.ai/api/v1") == "https://openrouter.ai/api/v1/models"


def test_list_openai_models_requires_key(tmp_path):
    llm = LLMInterface(config_path=str(tmp_path / "nonexistent.json"))
    result = llm.list_openai_models("")
    assert isinstance(result, str) and "API Key" in result
