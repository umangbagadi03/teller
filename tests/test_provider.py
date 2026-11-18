import pytest

from teller import config
from teller.llm.provider import (
    OFFLINE_MODEL,
    get_model_name,
    make_key_settings,
    make_model_name,
    pick_provider,
)


def clear_settings(monkeypatch):
    monkeypatch.setattr(config, "LLM_PROVIDER", "")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")
    monkeypatch.setattr(config, "OLLAMA_MODEL", "")


def test_no_key_runs_offline(monkeypatch):
    clear_settings(monkeypatch)
    assert pick_provider() == "offline"
    assert get_model_name() == OFFLINE_MODEL


def test_named_ollama_model_uses_ollama(monkeypatch):
    clear_settings(monkeypatch)
    monkeypatch.setattr(config, "OLLAMA_MODEL", "llama3.2")
    assert pick_provider() == "ollama"
    assert get_model_name() == "ollama_chat/llama3.2"


def test_own_key_settings_carry_the_key():
    settings = make_key_settings("test-key-1234567890")
    assert settings["api_key"] == "test-key-1234567890"
    assert make_model_name("gemini", "").startswith("gemini/")
    assert make_model_name("openai", "gpt-test") == "openai/gpt-test"


def test_gemini_key_uses_gemini(monkeypatch):
    clear_settings(monkeypatch)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-value")
    assert pick_provider() == "gemini"
    assert get_model_name().startswith("gemini/")


def test_anthropic_key_uses_anthropic(monkeypatch):
    clear_settings(monkeypatch)
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-value")
    assert pick_provider() == "anthropic"
    assert get_model_name().startswith("anthropic/")


def test_openai_key_uses_openai(monkeypatch):
    clear_settings(monkeypatch)
    monkeypatch.setattr(config, "OPENAI_API_KEY", "test-value")
    assert pick_provider() == "openai"
    assert get_model_name().startswith("openai/")


def test_gemini_comes_first_when_there_are_many_keys(monkeypatch):
    clear_settings(monkeypatch)
    monkeypatch.setattr(config, "OPENAI_API_KEY", "test-value")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-value")
    assert pick_provider() == "gemini"


def test_explicit_provider_wins(monkeypatch):
    clear_settings(monkeypatch)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-value")
    monkeypatch.setattr(config, "LLM_PROVIDER", "ollama")
    assert pick_provider() == "ollama"


def test_unknown_provider_is_an_error(monkeypatch):
    clear_settings(monkeypatch)
    monkeypatch.setattr(config, "LLM_PROVIDER", "other")
    with pytest.raises(ValueError):
        pick_provider()
