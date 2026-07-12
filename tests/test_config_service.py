# tests/test_config_service.py
import json
import os

from services import config_service


def test_ensure_config_creates_default(tmp_path):
    path = str(tmp_path / "config.json")
    config_service.ensure_config_exists(path)
    assert os.path.exists(path)
    cfg = json.load(open(path, encoding="utf-8"))
    assert cfg["llm_mode"] == "mock"
    # 預設不得含任何金鑰
    assert cfg["cloud"]["api_key"] == ""
    assert cfg["ai_detector"]["api_key"] == ""


def test_env_override_injects_key(tmp_path, monkeypatch):
    path = str(tmp_path / "config.json")
    config_service.ensure_config_exists(path)
    monkeypatch.setenv("PRS_CLOUD_API_KEY", "env-secret-key")
    cfg = config_service.load_global_config(path)
    assert cfg["cloud"]["api_key"] == "env-secret-key"
    # 環境變數不寫回檔案
    on_disk = json.load(open(path, encoding="utf-8"))
    assert on_disk["cloud"]["api_key"] == ""


def test_save_and_reload_roundtrip(tmp_path):
    path = str(tmp_path / "config.json")
    config_service.ensure_config_exists(path)
    cfg = config_service.load_global_config(path)
    cfg["llm_mode"] = "ollama"
    config_service.save_global_config(cfg, path)
    assert config_service.load_global_config(path)["llm_mode"] == "ollama"


def test_temp_user_config_reuses_path(tmp_path):
    conf = {"llm_mode": "cloud"}
    p1 = config_service.write_temp_user_config(conf)
    p2 = config_service.write_temp_user_config({"llm_mode": "mock"}, existing_path=p1)
    assert p1 == p2
    assert json.load(open(p2, encoding="utf-8"))["llm_mode"] == "mock"
    os.unlink(p1)


def test_apply_text_filters():
    from services.file_service import apply_text_filters

    text = 'Intro "quoted words" body References\nSmith 2024'
    out = apply_text_filters(
        text,
        manual_exclusions=["Intro "],
        exclude_quotes=True,
        exclusion_keywords="References",
    )
    assert "quoted words" not in out
    assert "Smith 2024" not in out
    assert out.startswith("body") or "body" in out
