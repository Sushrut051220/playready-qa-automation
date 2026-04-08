# Two-Repo Strategy for PlayReady QA Automation

## Repo 1 — current repository (`RAGAS_5_April_Automation`)
Purpose:
- local / QA evaluation baseline
- Playwright UI automation
- DSPy + RAGAS scoring
- report generation
- testset generation from `pdf_registry.json`

Recommended provider strategy:
- use `openai` as the primary provider
- keep the chat model and embedding model names aligned with the enterprise repo
- keep `ollama` only as a fallback for cheap local smoke runs

Suggested profile:
- `LLM_PROVIDER=openai`
- `OPENAI_MODEL=gpt-4o-mini`
- `OPENAI_EMBEDDING_MODEL=text-embedding-3-small`

## Repo 2 — future enterprise repo
Purpose:
- same QA workflow and report format
- Azure AI Search retrieval
- Foundry orchestration / tracing
- Entra ID authentication
- production-like validation on the Microsoft project laptop

Suggested profile:
- same chat model family as Repo 1
- same embedding model family as Repo 1
- retrieval comes from Azure AI Search instead of local PDFs
- secrets come from enterprise identity / secret management, not local files

## Debugging rule of thumb
- if both repos fail → likely shared test logic / evaluation / report issue
- if only enterprise fails → likely Azure Search / Foundry / Entra ID / environment issue
- if only local fails → likely local PDF setup or local configuration issue
