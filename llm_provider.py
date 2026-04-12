from __future__ import annotations

import os
from typing import Any
from urllib import error, request


def _is_truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_raw_provider() -> str:
    provider = (os.getenv("LLM_PROVIDER") or os.getenv("EVALUATOR_PROVIDER") or "openai").strip().lower()
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
    """Fetch a short-lived Bearer token via DefaultAzureCredential (Entra ID)."""
    try:
        from azure.identity import DefaultAzureCredential
        credential = DefaultAzureCredential()
        token = credential.get_token("https://cognitiveservices.azure.com/.default")
        return token.token
    except Exception as exc:
        return ""


def _get_openai_api_key() -> str:
    key = (os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not key and _is_azure_openai_mode():
        key = _get_azure_token()
    return key


def _get_openai_base_url() -> str | None:
    base_url = (
        os.getenv("AZURE_OPENAI_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or os.getenv("AZURE_OPENAI_ENDPOINT")
        or ""
    ).strip()
    return base_url or None


def _get_openai_chat_model() -> str:
    return (
        os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
        or os.getenv("OPENAI_MODEL")
        or "gpt-4o-mini"
    ).strip() or "gpt-4o-mini"


def _get_openai_embedding_model() -> str:
    return (
        os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        or os.getenv("OPENAI_EMBEDDING_MODEL")
        or "text-embedding-3-small"
    ).strip() or "text-embedding-3-small"


def get_metrics_profile() -> str:
    profile = os.getenv("RAGAS_METRICS_PROFILE", "full").strip().lower()
    return profile if profile in {"smoke", "fast", "full"} else "fast"


def get_model_label() -> str:
    provider = get_llm_provider()
    if provider == "ollama":
        return f"ollama:{os.getenv('OLLAMA_MODEL', 'phi3:mini').strip() or 'phi3:mini'}"
    if provider == "openai":
        if _is_azure_openai_mode():
            return f"azure-openai:{_get_openai_chat_model()}"
        return f"openai:{_get_openai_chat_model()}"
    if provider == "gemini":
        return f"gemini:{os.getenv('GEMINI_MODEL', 'gemini-2.5-flash').strip() or 'gemini-2.5-flash'}"
    return provider


def _check_ollama_reachable(base_url: str) -> tuple[bool, str | None]:
    normalized = (base_url or "http://localhost:11434").rstrip("/")
    try:
        with request.urlopen(f"{normalized}/api/tags", timeout=3) as response:
            if 200 <= int(getattr(response, "status", 200)) < 300:
                return True, None
            return False, f"Ollama responded with HTTP {getattr(response, 'status', 'unknown')} at {normalized}."
    except error.URLError as exc:
        return False, f"Ollama is not reachable at {normalized}: {exc.reason}."
    except Exception as exc:
        return False, f"Ollama is not reachable at {normalized}: {exc}"


def build_dspy_lm() -> tuple[Any | None, str | None]:
    provider = get_llm_provider()
    temperature = float(os.getenv("LLM_TEMPERATURE", "0") or "0")

    try:
        import dspy
    except Exception as exc:
        return None, f"DSPy is unavailable: {exc}"

    if provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip() or "http://localhost:11434"
        reachable, reason = _check_ollama_reachable(base_url)
        if not reachable:
            return None, reason

        model = os.getenv("OLLAMA_MODEL", "phi3:mini").strip() or "phi3:mini"
        kwargs = {
            "model": f"openai/{model}",
            "api_key": os.getenv("OLLAMA_API_KEY", "ollama"),
            "temperature": temperature,
            "max_tokens": int(os.getenv("DSPY_MAX_TOKENS", "512") or "512"),
        }
        try:
            return dspy.LM(api_base=f"{base_url.rstrip('/')}/v1", **kwargs), None
        except TypeError:
            try:
                return dspy.LM(base_url=f"{base_url.rstrip('/')}/v1", **kwargs), None
            except Exception as exc:
                return None, f"Failed to configure DSPy for Ollama: {exc}"
        except Exception as exc:
            return None, f"Failed to configure DSPy for Ollama: {exc}"

    if provider == "openai":
        api_key = _get_openai_api_key()
        if not api_key:
            return None, "OPENAI_API_KEY / AZURE_OPENAI_API_KEY is missing and DefaultAzureCredential token fetch failed; skipping DSPy LM configuration."

        try:
            os.environ["OPENAI_API_KEY"] = api_key
            return dspy.LM(
                model=f"openai/{_get_openai_chat_model()}",
                api_base=_get_openai_base_url(),
                temperature=temperature,
                max_tokens=int(os.getenv("DSPY_MAX_TOKENS", "512") or "512"),
            ), None
        except Exception as exc:
            return None, f"Failed to configure OpenAI/Azure OpenAI for DSPy: {exc}"

    return None, f"Unsupported LLM_PROVIDER '{provider}'. Use 'openai', 'azure_openai', 'ollama', or 'gemini'."


def configure_dspy_lm() -> str | None:
    lm, issue = build_dspy_lm()
    if lm is None:
        return issue

    try:
        import dspy

        dspy.settings.configure(lm=lm)
        return None
    except Exception as exc:
        return f"Failed to activate DSPy LM: {exc}"


def build_ragas_dependencies() -> tuple[Any | None, Any | None, str | None, dict[str, str]]:
    provider = get_llm_provider()
    skip_if_missing = _is_truthy(os.getenv("RAGAS_SKIP_LLM_METRICS_IF_NO_KEY", "false"), default=False)
    provider_meta = {"provider": provider, "model": get_model_label(), "metrics_profile": get_metrics_profile()}

    try:
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from ragas.llms import LangchainLLMWrapper
    except Exception:
        LangchainEmbeddingsWrapper = None
        LangchainLLMWrapper = None

    if provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip() or "http://localhost:11434"
        reachable, reason = _check_ollama_reachable(base_url)
        if not reachable:
            return None, None, reason, provider_meta

        try:
            from langchain_ollama import ChatOllama, OllamaEmbeddings

            llm = ChatOllama(
                model=os.getenv("OLLAMA_MODEL", "phi3:mini").strip() or "phi3:mini",
                base_url=base_url,
                temperature=0,
            )
            embeddings = OllamaEmbeddings(
                model=os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text").strip() or "nomic-embed-text",
                base_url=base_url,
            )

            if LangchainLLMWrapper and LangchainEmbeddingsWrapper:
                return LangchainLLMWrapper(llm), LangchainEmbeddingsWrapper(embeddings), None, provider_meta
            return llm, embeddings, None, provider_meta
        except Exception as exc:
            return None, None, f"Failed to initialize Ollama evaluator dependencies: {exc}", provider_meta

    if provider == "openai":
        # In Azure OpenAI mode, ONLY check AZURE_OPENAI_API_KEY (not OPENAI_API_KEY) to
        # determine whether to use key auth vs DefaultAzureCredential token auth.
        # DSPy's build_dspy_lm() sets os.environ["OPENAI_API_KEY"] = JWT_token for its
        # own use — we must not treat that JWT as a real Azure API key here.
        if _is_azure_openai_mode():
            raw_api_key = (os.getenv("AZURE_OPENAI_API_KEY") or "").strip()
        else:
            raw_api_key = (os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
        use_token_auth = _is_azure_openai_mode() and not raw_api_key

        if not use_token_auth and not raw_api_key and skip_if_missing:
            return None, None, "OPENAI_API_KEY / AZURE_OPENAI_API_KEY missing; skipping LLM-based RAGAS metrics.", provider_meta
        if not use_token_auth and not raw_api_key:
            return None, None, "OPENAI_API_KEY / AZURE_OPENAI_API_KEY missing.", provider_meta

        try:
            from openai import AzureOpenAI, OpenAI
            from ragas.llms import llm_factory
            from ragas.embeddings import OpenAIEmbeddings as _RagasOpenAIEmbeddings

            class _AzureRagasEmbeddings(_RagasOpenAIEmbeddings):
                """Adds LangChain-style embed_query/embed_documents so RAGAS metrics can call them directly."""

                def embed_query(self, text: str):
                    return self.embed_text(text)

                def embed_documents(self, texts):
                    return self.embed_texts(texts)

            # Dedicated embedding client: prefers a short API key on the cognitiveservices
            # endpoint to avoid "Request Header Fields Too Large" caused by 9KB JWT tokens.
            embed_api_key = (os.getenv("AZURE_OPENAI_EMBEDDING_API_KEY") or "").strip()
            embed_base_url = (os.getenv("AZURE_OPENAI_EMBEDDING_BASE_URL") or "").strip().rstrip("/")

            if _is_azure_openai_mode():
                base_url = (_get_openai_base_url() or "").rstrip("/")
                api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
                if use_token_auth:
                    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
                    credential = DefaultAzureCredential()
                    token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")
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
                    # API-key mode: use a dedicated client on the cognitiveservices endpoint.
                    embed_client = AzureOpenAI(
                        azure_endpoint=embed_base_url,
                        api_version="2023-05-15",
                        api_key=embed_api_key,
                    )
                else:
                    # Token-auth mode: reuse the LLM client (azure_ad_token_provider on
                    # services.ai.azure.com).  Key auth is disabled on this resource, so
                    # the AZURE_OPENAI_EMBEDDING_API_KEY env var is intentionally ignored here.
                    # Authorization: Bearer (not api-key) is required and accepted by that endpoint.
                    embed_client = oai_client
            else:
                oai_client = OpenAI(api_key=raw_api_key)
                embed_client = oai_client

            ragas_llm = llm_factory(
                _get_openai_chat_model(),
                client=oai_client,
                max_tokens=int(os.getenv("RAGAS_LLM_MAX_TOKENS", "16000")),
            )
            ragas_embeddings = _AzureRagasEmbeddings(client=embed_client, model=_get_openai_embedding_model())
            return ragas_llm, ragas_embeddings, None, provider_meta
        except Exception as exc:
            return None, None, f"Failed to initialize OpenAI/Azure OpenAI evaluator dependencies: {exc}", provider_meta

    if provider == "gemini":
        api_key = os.getenv("GOOGLE_API_KEY", "").strip() or os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key and skip_if_missing:
            return None, None, "GOOGLE_API_KEY / GEMINI_API_KEY missing; skipping LLM-based RAGAS metrics.", provider_meta
        if not api_key:
            return None, None, "GOOGLE_API_KEY / GEMINI_API_KEY missing.", provider_meta

        try:
            from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

            os.environ.setdefault("GOOGLE_API_KEY", api_key)
            llm = ChatGoogleGenerativeAI(
                model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                temperature=0,
            )
            embeddings = GoogleGenerativeAIEmbeddings(
                model=os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001"),
            )

            if LangchainLLMWrapper and LangchainEmbeddingsWrapper:
                return LangchainLLMWrapper(llm), LangchainEmbeddingsWrapper(embeddings), None, provider_meta
            return llm, embeddings, None, provider_meta
        except Exception as exc:
            return None, None, f"Failed to initialize Gemini evaluator dependencies: {exc}", provider_meta

    return None, None, f"Unsupported LLM_PROVIDER '{provider}'. Use 'openai', 'azure_openai', 'ollama', or 'gemini'.", provider_meta
