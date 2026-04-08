# Enterprise provider integration placeholders

When you split to the real enterprise repo, this folder is where the Azure-specific integration code should live.

Recommended files later:
- `auth.py` — Entra ID / DefaultAzureCredential / service principal setup
- `azure_search_client.py` — Azure AI Search retrieval helpers
- `foundry_client.py` — Foundry / Azure OpenAI project orchestration calls
- `trace_adapter.py` — trace IDs, eval scores, and backend metadata capture

Keep these integrations **out of the current local QA repo** as much as possible.
