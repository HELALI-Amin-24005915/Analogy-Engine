"""Unit tests for core.config module."""

import pytest

from core.config import build_llm_config_from_input


def test_build_llm_config_from_input_returns_dict_with_config_list() -> None:
    cfg = build_llm_config_from_input("test-key", "https://test.openai.azure.com/")
    assert isinstance(cfg, dict)
    assert "config_list" in cfg
    assert len(cfg["config_list"]) == 1


def test_build_llm_config_from_input_entry_has_required_keys() -> None:
    cfg = build_llm_config_from_input("key", "https://x.openai.azure.com/")
    entry = cfg["config_list"][0]
    assert entry["model"] == "gpt-4o"
    assert entry["api_type"] == "azure"
    assert entry["api_key"] == "key"
    assert "base_url" in entry
    assert entry["base_url"].endswith("/")
    assert "api_version" in entry


def test_build_llm_config_from_input_custom_deployment() -> None:
    cfg = build_llm_config_from_input("k", "https://x.openai.azure.com/", deployment="gpt-4")
    assert cfg["config_list"][0]["model"] == "gpt-4"


def test_build_llm_config_from_input_strips_whitespace() -> None:
    cfg = build_llm_config_from_input("  key  ", "  https://x.openai.azure.com/  ")
    assert cfg["config_list"][0]["api_key"] == "key"
    assert "https://x.openai.azure.com/" in cfg["config_list"][0]["base_url"]


def test_build_llm_config_from_input_empty_key_raises() -> None:
    with pytest.raises(ValueError, match="API key and endpoint"):
        build_llm_config_from_input("", "https://x.openai.azure.com/")


def test_build_llm_config_from_input_empty_endpoint_raises() -> None:
    with pytest.raises(ValueError, match="API key and endpoint"):
        build_llm_config_from_input("key", "")


def test_build_llm_config_from_input_whitespace_only_raises() -> None:
    with pytest.raises(ValueError):
        build_llm_config_from_input("   ", "https://x.openai.azure.com/")
    with pytest.raises(ValueError):
        build_llm_config_from_input("key", "   ")
