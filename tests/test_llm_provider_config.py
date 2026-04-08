from __future__ import annotations

import llm_provider


def test_get_llm_provider_supports_azure_alias(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "azure_openai")

    assert llm_provider.get_llm_provider() == "openai"


def test_get_model_label_prefers_azure_chat_deployment(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "azure_openai")
    monkeypatch.setenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-enterprise")

    assert llm_provider.get_model_label() == "azure-openai:gpt-4o-enterprise"
