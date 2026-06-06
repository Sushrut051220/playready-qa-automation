# Multi-Bot QA Strategy: Public / Customer / Private

## Overview

The PlayReady QA automation framework currently tests a single **Public Bot**. The dev team is building two additional bots — **Customer Bot** and **Private Bot** — each with different KB access scopes. This document captures the strategy to extend the framework and dashboard to cover all three.

---

## Bot Types & KB Access

| KB Type        | Public Bot | Customer Bot | Private Bot |
|----------------|-----------|--------------|-------------|
| Public KB      | Yes       | Yes          | Yes         |
| Customer KB    | No        | Yes          | Yes         |

- **Public Bot** — answers from public knowledge base only
- **Customer Bot** — answers from public KB + customer-specific KB
- **Private Bot** — full access: public KB + all customer KB

---

## What Needs to Change

### 1. Test Case Schema — Add `bot_type` + `kb_scope`

Current schema in `data/test_cases.json` has no bot type field. Extend it:

```json
{
  "id": "cust001_q01_pos_factual",
  "bot_type": "customer",
  "kb_scope": ["public", "customer"],
  "prompt": "What is my account limit?",
  "ground_truth": "...",
  "expected_pdfs": ["Customer_KB_Policy.pdf"],
  "strict_grounding": true,
  "expect_fallback": false,
  "query_type": "positive",
  "source_category": "customer_specific"
}
```

**Split into 3 files:**
```
data/
  test_cases_public.json     # existing cases, add bot_type: "public"
  test_cases_customer.json   # customer-specific + shared public cases
  test_cases_private.json    # all KB cases + private-only cases
```

**Key test scenarios to cover per bot:**

| Scenario | Public Bot | Customer Bot | Private Bot |
|---------|-----------|--------------|-------------|
| Public KB question answered | PASS | PASS | PASS |
| Customer KB question answered | FAIL (expect fallback) | PASS | PASS |
| Private-only question answered | FAIL | FAIL | PASS |
| Cross-KB grounding check | N/A | Verify source is correct KB | Verify source is correct KB |
| KB boundary NOT violated | N/A | Customer cannot access private data | N/A |

---

### 2. Environment Config — Per-Bot Variables

Each bot type has its own **Foundry project endpoint**, **OpenAI endpoint**, and **agent**. These are completely separate Azure deployments.

Add to `.env`:

```bash
# UI endpoints (chatbot frontend)
PUBLIC_BASE_URL=https://public-bot.example.com
CUSTOMER_BASE_URL=https://customer-bot.example.com
PRIVATE_BASE_URL=https://private-bot.example.com

# Azure AI Foundry project endpoint — one per bot (different Azure projects)
PUBLIC_FOUNDRY_PROJECT_ENDPOINT=https://public-foundry.api.azureml.ms/...
CUSTOMER_FOUNDRY_PROJECT_ENDPOINT=https://customer-foundry.api.azureml.ms/...
PRIVATE_FOUNDRY_PROJECT_ENDPOINT=https://private-foundry.api.azureml.ms/...

# Foundry agent name + version per bot
PUBLIC_FOUNDRY_AGENT_NAME=PublicAgent
CUSTOMER_FOUNDRY_AGENT_NAME=CustomerAgent
PRIVATE_FOUNDRY_AGENT_NAME=PrivateAgent

PUBLIC_FOUNDRY_AGENT_VERSION=8
CUSTOMER_FOUNDRY_AGENT_VERSION=1
PRIVATE_FOUNDRY_AGENT_VERSION=1

# Azure OpenAI endpoint — one per bot (different Azure OpenAI deployments)
PUBLIC_AZURE_OPENAI_BASE_URL=https://public-openai.openai.azure.com/
CUSTOMER_AZURE_OPENAI_BASE_URL=https://customer-openai.openai.azure.com/
PRIVATE_AZURE_OPENAI_BASE_URL=https://private-openai.openai.azure.com/

# Azure OpenAI API keys per bot
PUBLIC_AZURE_OPENAI_API_KEY=<public-key>
CUSTOMER_AZURE_OPENAI_API_KEY=<customer-key>
PRIVATE_AZURE_OPENAI_API_KEY=<private-key>

# Azure OpenAI deployment names per bot (may differ per project)
PUBLIC_AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o
CUSTOMER_AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o
PRIVATE_AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o

PUBLIC_AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
CUSTOMER_AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
PRIVATE_AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small

# Active bot type for the current run
BOT_TYPE=public   # override per run: public | customer | private
```

> **Why separate endpoints?** Each bot type is a different Azure AI Foundry **project** with its own KB index, agent, and OpenAI deployment. They are not just different agents within the same project — the entire Azure backend is separate per bot.

---

### 3. `scripts/query_new_agent.py` — Add `--bot-type` Argument

Current: single agent name + single Foundry endpoint from env vars.
Change: pass `--bot-type` to select the right Foundry project endpoint, agent, and dataset.

```python
parser.add_argument("--bot-type", choices=["public", "customer", "private"], default="public")
args = parser.parse_args()
prefix = args.bot_type.upper()

# All three change per bot type
foundry_endpoint = os.getenv(f"{prefix}_FOUNDRY_PROJECT_ENDPOINT")
agent_name       = os.getenv(f"{prefix}_FOUNDRY_AGENT_NAME", "PublicAgent")
agent_version    = os.getenv(f"{prefix}_FOUNDRY_AGENT_VERSION", "8")
test_cases_file  = f"data/test_cases_{args.bot_type}.json"
output_file      = f"data/ragas_eval_dataset_{args.bot_type}.json"
```

Run per bot:
```bash
python scripts/query_new_agent.py --bot-type public
python scripts/query_new_agent.py --bot-type customer
python scripts/query_new_agent.py --bot-type private
```

---

### 4. `conftest.py` — Add `--bot-type` pytest Option

```python
def pytest_addoption(parser):
    parser.addoption("--bot-type", default="public", choices=["public", "customer", "private"])

@pytest.fixture(scope="session")
def bot_type(request):
    return request.config.getoption("--bot-type")

@pytest.fixture(scope="session")
def settings(bot_type):
    prefix = bot_type.upper()
    return {
        "base_url":                os.getenv(f"{prefix}_BASE_URL", os.getenv("BASE_URL", "")).strip(),
        "bot_type":                bot_type,
        "foundry_project_endpoint": os.getenv(f"{prefix}_FOUNDRY_PROJECT_ENDPOINT"),
        "azure_openai_base_url":   os.getenv(f"{prefix}_AZURE_OPENAI_BASE_URL"),
        "azure_openai_api_key":    os.getenv(f"{prefix}_AZURE_OPENAI_API_KEY"),
        "azure_openai_deployment": os.getenv(f"{prefix}_AZURE_OPENAI_CHAT_DEPLOYMENT"),
        ...
    }
```

These settings flow into `foundry_evaluator.py` and `query_new_agent.py` so every layer uses the correct Azure endpoints for the selected bot.

Run tests per bot:
```bash
pytest -m ui --bot-type=public
pytest -m ui --bot-type=customer
pytest -m ui --bot-type=private
```

---

### 5. `ragas_layer/dashboard_bridge.py` — Tag Results with `bot_type`

Currently sets `project: "playready-foundry"` for all runs.
Change to use bot_type as both a project tag and a hyperparameter:

```python
hyperparameters = {
    "project": f"playready-{bot_type}",        # e.g. "playready-customer"
    "bot_type": bot_type,                       # NEW — for dashboard filtering
    "kb_scope": ",".join(kb_scope),             # NEW — e.g. "public,customer"
    "framework": "ragas",
    "model": provider.model,
    "provider": provider.provider,
    "environment": os.getenv("ENVIRONMENT", "development"),
    "version": os.getenv("APP_VERSION", ""),
}
```

---

## Dashboard Integration (DeepEval Dashboard)

The dashboard at `http://localhost:5000` supports the following which maps directly to our multi-bot needs:

### How Bot Types Will Appear in the Dashboard

**Project Filter** (auto-detected from `hyperparameters.project`):
```
Projects dropdown:
  [playready-public]
  [playready-customer]
  [playready-private]
```

Each bot gets its own project in the dashboard — separate pass rates, metric averages, SLOs, and run history.

**Per-Test-Case Tags** (`testCases[].tags`):
Add tags on each test case for granular filtering:
```python
tags = [bot_type, f"kb_{kb_scope}", query_type, source_category]
# e.g. ["customer", "kb_public_customer", "positive", "customer_specific"]
```

**Hyperparameters** visible in run detail view:
```json
{
  "project": "playready-customer",
  "bot_type": "customer",
  "kb_scope": "public,customer",
  "environment": "development",
  "version": "1.0"
}
```

### Dashboard Views to Use Per Bot

| Dashboard Section | What to Check |
|------------------|---------------|
| Projects > playready-public | Pass rate, metric averages for public bot |
| Projects > playready-customer | Customer bot metrics, KB boundary checks |
| Projects > playready-private | Private bot full-access metrics |
| SLA/SLOs | Set thresholds per project (e.g. faithfulness >= 0.85 for customer bot) |
| Bugs | KB boundary violations flagged as bugs |
| Tags filter | Filter by "kb_violation" tag to find boundary leaks |

### KB Boundary Violation as a New Metric

Add a custom metric in `metricsData` per test case:

```json
{
  "name": "KBBoundaryViolation",
  "score": 0.0,
  "success": true,
  "threshold": 0.0,
  "reason": "Response only cites customer KB sources, no private data exposed"
}
```

If the bot returns content from a KB it shouldn't access, this metric fails (score > 0) and appears as a red metric in the dashboard.

### SLO Configuration Per Bot (via Dashboard API)

```bash
# Create SLO for customer bot faithfulness
POST /api/sla/slos
{
  "name": "Customer Bot Faithfulness",
  "project": "playready-customer",
  "metric_type": "metric_avg_score",
  "metric_name": "Faithfulness",
  "threshold": 0.85,
  "operator": ">=",
  "window_size": 10
}
```

---

## Data Flow (End to End)

```
Dev Team deploys Customer Bot (separate Azure Foundry project + OpenAI instance)
         |
         v
scripts/query_new_agent.py --bot-type=customer
  - Reads CUSTOMER_FOUNDRY_PROJECT_ENDPOINT   ← customer Azure Foundry project
  - Reads CUSTOMER_FOUNDRY_AGENT_NAME/VERSION ← customer agent
  - Reads data/test_cases_customer.json
  - Queries CustomerAgent and writes data/ragas_eval_dataset_customer.json
         |
         v
pytest -m ragas --bot-type=customer
  - conftest loads CUSTOMER_AZURE_OPENAI_BASE_URL + CUSTOMER_AZURE_OPENAI_API_KEY
  - test_ragas_eval.py runs RAGAS metrics (using customer OpenAI endpoint)
  - test_foundry_eval.py runs quality/safety/NLP (using customer OpenAI endpoint)
  - dspy_layer evaluates deterministic metrics
         |
         v
ragas_layer/dashboard_bridge.py
  - Tags run: bot_type="customer", project="playready-customer"
  - Records foundry_endpoint and openai_endpoint in hyperparameters for traceability
  - Writes eval_history/test_run_<timestamp>.json
         |
         v
DeepEval Dashboard (localhost:5000)
  - Auto-detects new file in eval_history/
  - Shows under Projects > playready-customer
  - Metrics, SLOs, bugs visible and isolated per bot
```

---

## File Changes Summary

| File | Change |
|------|--------|
| `data/test_cases.json` | Add `bot_type`, `kb_scope` fields; split into 3 files |
| `scripts/query_new_agent.py` | Add `--bot-type` CLI arg; per-bot Foundry endpoint + agent name/version/dataset |
| `conftest.py` | Add `--bot-type` pytest option; per-bot BASE_URL, Foundry endpoint, OpenAI endpoint fixture |
| `ragas_layer/dashboard_bridge.py` | Tag hyperparameters with `bot_type`, `kb_scope`; per-bot project name |
| `.env` / `.env.example` | Add per-bot BASE_URL, Foundry project endpoint, OpenAI endpoint + key + deployment |
| `foundry_layer/foundry_evaluator.py` | Accept per-bot OpenAI endpoint/key instead of global env vars; add `KBBoundaryViolation` metric |
| `pytest.ini` | Add `bot_type` marker or session variable |

---

## Implementation Order

1. Add `bot_type` + `kb_scope` to test case schema and split data files
2. Update `query_new_agent.py` with `--bot-type` arg
3. Update `conftest.py` with `--bot-type` pytest option + per-bot URL fixture
4. Update `dashboard_bridge.py` to tag with `bot_type` and use per-bot project name
5. Add `KBBoundaryViolation` metric in `foundry_evaluator.py`
6. Configure SLOs per bot in dashboard
7. Run full test suite for all 3 bots and verify dashboard shows 3 separate projects

---

## Dashboard Project Configuration (One-Time Setup)

After first run of each bot, configure display in dashboard:

```bash
POST /api/projects/configure
{ "project_id": "playready-public",   "display_name": "Public Bot",   "color": "#2196F3" }
POST /api/projects/configure
{ "project_id": "playready-customer", "display_name": "Customer Bot", "color": "#4CAF50" }
POST /api/projects/configure
{ "project_id": "playready-private",  "display_name": "Private Bot",  "color": "#FF9800" }
```

---

*Last updated: 2026-06-06*
