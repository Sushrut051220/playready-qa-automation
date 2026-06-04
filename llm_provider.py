from __future__ import annotations

import os
from typing import Any


def _is_truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_raw_provider() -> str:
    provider = (
        os.getenv("LLM_PROVIDER")
        or os.getenv("EVALUATOR_PROVIDER")
        or "openai"
    ).strip().lower()
    return provider or "openai"


def get_llm_provider() -> str:
    provider = _get_raw_provider()
    if provider in {"azure", "azure_openai", "azure-openai", "azureopenai"}:
        return "openai"
    return provider


def _is_azure_openai_mode() -> bool:
    provider = _get_raw_provider()
    return provider in {"azure", "azure_openai", "azure-openai", "azureopenai"} or bool(
        (os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT") or "").strip()
        or (os.getenv("AZURE_OPENAI_BASE_URL") or "").strip()
        or (os.getenv("AZURE_OPENAI_ENDPOINT") or "").strip()
    )


def _get_azure_token() -> str:
    try:
        from azure.identity import DefaultAzureCredential

        credential = DefaultAzureCredential()
        token = credential.get_token("https://cognitiveservices.azure.com/.default")
        return token.token
    except Exception:
        return ""


def _get_openai_api_key() -> str:
    key = (os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not key and _is_azure_openai_mode():
        key = _get_azure_token()
    return key


def _get_openai_chat_model() -> str:
    return (
        os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
        or os.getenv("OPENAI_MODEL")
        or "gpt-4.1-mini"
    )


def _get_openai_embedding_model() -> str:
    return (
        os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        or os.getenv("OPENAI_EMBEDDING_MODEL")
        or "text-embedding-ada-002"
    )


def get_metrics_profile() -> str:
    return os.getenv("RAGAS_METRICS_PROFILE", "full").strip().lower()


def build_ragas_dependencies():

    provider = get_llm_provider()

    raw_api_key = (
        os.getenv("AZURE_OPENAI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    ).strip()

    # ✅ ALWAYS force token auth in Azure mode
    use_token_auth = _is_azure_openai_mode()
    raw_api_key = None

    provider_meta = {
        "provider": provider,
        "model": _get_openai_chat_model(),
    }
    try:
        from openai import AzureOpenAI, OpenAI
        from ragas.llms import llm_factory
        from ragas.embeddings import OpenAIEmbeddings as _RagasOpenAIEmbeddings

        # =============================
        # ✅ EMBEDDING WRAPPER (FIX async/sync issue)
        # =============================
        class _AzureRagasEmbeddings(_RagasOpenAIEmbeddings):

            def embed_query(self, text: str):
                return self.embed_text(text)

            def embed_documents(self, texts):
                return self.embed_texts(texts)

            async def aembed_text(self, text: str):
                return self.embed_text(text)

            async def aembed_query(self, text: str):
                return self.embed_text(text)

            async def aembed_documents(self, texts):
                return self.embed_documents(texts)

        embed_api_key = (os.getenv("AZURE_OPENAI_EMBEDDING_API_KEY") or "").strip()
        embed_base_url = (os.getenv("AZURE_OPENAI_EMBEDDING_BASE_URL") or "").strip().rstrip("/")

        if _is_azure_openai_mode():

            # ✅ FIX: correct VNet-safe endpoint
            base_url = (
                os.getenv("AZURE_OPENAI_ENDPOINT_COGNITIVE")
                or os.getenv("AZURE_OPENAI_BASE_URL")
                or os.getenv("AZURE_OPENAI_ENDPOINT")
                or ""
            ).rstrip("/")

            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

            if use_token_auth:
                from azure.identity import DefaultAzureCredential, get_bearer_token_provider

                credential = DefaultAzureCredential()
                token_provider = get_bearer_token_provider(
                    credential,
                    "https://cognitiveservices.azure.com/.default",
                )

                oai_client = AzureOpenAI(
                    azure_endpoint=base_url,
                    api_version=api_version,
                    azure_ad_token_provider=token_provider,
                )

            else:
                oai_client = AzureOpenAI(
                    azure_endpoint=base_url,
                    api_version=api_version,
                    api_key=raw_api_key,
                )

            if not use_token_auth and embed_api_key and embed_base_url:
                embed_client = AzureOpenAI(
                    azure_endpoint=embed_base_url,
                    api_version="2023-05-15",
                    api_key=embed_api_key,
                )
            else:
                embed_client = oai_client

        else:
            oai_client = OpenAI(api_key=raw_api_key)
            embed_client = oai_client

        ragas_llm = llm_factory(
            _get_openai_chat_model(),
            client=oai_client,
            max_tokens=int(os.getenv("RAGAS_LLM_MAX_TOKENS", "16000")),
        )

        ragas_embeddings = _AzureRagasEmbeddings(
            client=embed_client,
            model=_get_openai_embedding_model(),
        )

        return ragas_llm, ragas_embeddings, None, provider_meta

    except Exception as exc:
        return None, None, f"Failed to initialize OpenAI/Azure OpenAI evaluator dependencies: {exc}", provider_meta