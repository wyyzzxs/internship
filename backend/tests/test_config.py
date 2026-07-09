"""Config 测试 - 验证 .env 读取和默认值。

注意:.env 文件里有真实的 DASHSCOPE_API_KEY,会影响 reload 测试。
本测试用 tmp_path 把 .env 临时挪走再 reload,避免污染。
"""
from __future__ import annotations

import importlib

import pytest

import backend.config as config_module
from backend.config import PROJECT_ROOT


def _reload_config(env_file_exists: bool):
    """重新执行 Config 类体以读取最新环境变量。

    Args:
        env_file_exists: 如果 False,临时把 .env 挪走,避免 load_dotenv 加载真 Key。
    """
    importlib.reload(config_module)
    return config_module.Config


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch, tmp_path):
    """每个测试隔离环境变量 + 临时挪走 .env。"""
    for key in [
        "DASHSCOPE_API_KEY",
        "MOCK_LLM",
        "QWEATHER_API_KEY",
        "MOCK_WEATHER",
        "DEBUG",
        "LLM_MODEL",
        "LLM_BASE_URL",
    ]:
        monkeypatch.delenv(key, raising=False)
    env_file = PROJECT_ROOT / ".env"
    backup = tmp_path / ".env.bak"
    moved = False
    if env_file.exists():
        env_file.rename(backup)
        moved = True
    yield
    # 还原 .env(万一异常也要复原)
    if moved and backup.exists():
        backup.rename(env_file)


def test_mock_llm_default_true_when_no_key():
    """Key 缺失时,MOCK_LLM 默认 true(项目方案 §12.4)。"""
    cfg = _reload_config(env_file_exists=False)
    assert cfg.MOCK_LLM is True
    assert cfg.DASHSCOPE_API_KEY == ""


def test_mock_llm_false_when_key_present(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test-fake")
    cfg = _reload_config(env_file_exists=False)
    assert cfg.MOCK_LLM is False


def test_mock_llm_explicit_override(monkeypatch):
    """即使有 Key,显式设 MOCK_LLM=true 也应开启 mock。"""
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test-fake")
    monkeypatch.setenv("MOCK_LLM", "true")
    cfg = _reload_config(env_file_exists=False)
    assert cfg.MOCK_LLM is True


def test_paths_and_defaults():
    cfg = _reload_config(env_file_exists=False)
    assert cfg.LLM_MODEL == "qwen-plus"
    assert "dashscope" in cfg.LLM_BASE_URL
    assert cfg.DATA_DIR.name == "data"
    assert cfg.MOCK_PLANS_DIR.name == "mock_plans"
    assert cfg.AGENT_MAX_ITERATIONS == 10


def test_mock_weather_defaults():
    cfg = _reload_config(env_file_exists=False)
    assert cfg.MOCK_WEATHER is True  # QWEATHER_API_KEY 未设
    assert cfg.DEBUG is True


def test_project_root_is_resolved_path():
    """PROJECT_ROOT 必须是 backend 的父目录。"""
    assert config_module.Config.PROJECT_ROOT.name == "internship"
    assert (config_module.Config.PROJECT_ROOT / "backend").is_dir()