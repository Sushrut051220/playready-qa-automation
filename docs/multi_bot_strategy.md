# Multi-Bot QA Strategy: Public / Customer / Private

## Overview

The PlayReady QA automation framework currently tests a single **Public Bot**. The dev team is building two additional bots — **Customer Bot** and **Private Bot** — each with different KB access scopes. This document captures the strategy to extend the framework and dashboard to cover all three.

---

## Bot Types & KB Access

| KB Type        | Public Bot | Customer Bot | Private Bot |
|----------------|-----------|--------------|-------------|
| Public KB      | Yes       | Yes          | Yes         |
| Customer KB    | No        | Yes          | Yes         |

- **Public Bot** — answers from public knowledge base only; MCP tools scoped to public resources
- **Customer Bot** — answers from public KB + customer-specific KB; MCP tools include customer resources
- **Private Bot** — full access: public KB + all customer KB; MCP tools have full resource access

All three bots use MCP (Model Context Protocol) for tool and resource access. MCP scope enforcement per bot is a key test target.

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

---

## DeepEval Gap Analysis — What We Are Missing

This section maps all 54 concrete DeepEval metrics against what the PlayReady QA framework currently covers via RAGAS, Azure Foundry Evaluator, and DSPy. It also covers tracing and synthetic test case generation gaps.

---

### Current Coverage in PlayReady QA

| Layer | Metrics |
|-------|---------|
| RAGAS | AnswerRelevancy, Faithfulness, ContextualPrecision, ContextualRecall, ContextualRelevancy |
| Azure Foundry Quality | Coherence, Fluency, Relevance, Groundedness, Similarity |
| Azure Foundry NLP | F1 Score, ROUGE-1, BLEU, METEOR |
| Azure Foundry Safety | Violence, Sexual, Self-Harm, Hate/Unfairness |
| DSPy Deterministic | Keyword presence, Fallback detection, PDF grounding, Formatting constraints, LLM answer quality |

---

### Complete DeepEval Metrics Cross-Check (54 Metrics)

#### RAG Metrics (9 total)

| Metric | Covered? | How | Gap / Note |
|--------|----------|-----|------------|
| AnswerRelevancyMetric | YES | RAGAS | Duplicate coverage — can consolidate |
| FaithfulnessMetric | YES | RAGAS | Duplicate coverage |
| ContextualPrecisionMetric | YES | RAGAS | Duplicate coverage |
| ContextualRecallMetric | YES | RAGAS | Duplicate coverage |
| ContextualRelevancyMetric | YES | RAGAS | Duplicate coverage |
| RAGASAnswerRelevancyMetric | YES | RAGAS (direct) | Same as above via RAGAS wrapper |
| RAGASFaithfulnessMetric | YES | RAGAS (direct) | Same as above |
| RAGASContextualPrecisionMetric | YES | RAGAS (direct) | Same as above |
| RAGASContextualRecallMetric | YES | RAGAS (direct) | Same as above |
| **RAGASContextualEntitiesRecall** | **NO** | — | **MISSING** — measures entity-level recall, not just passage recall. Important for factual answers citing specific policy entities |

#### Core LLM Judge / Custom Metrics (6 total)

| Metric | Covered? | How | Gap / Note |
|--------|----------|-----|------------|
| **GEval** | **NO** | — | **MISSING** — define PlayReady-specific rubrics in plain English (e.g. "Does response cite the correct policy?", "Does response correctly identify KB source?") |
| **ArenaGEval** | **NO** | — | **MISSING** — compare responses from different bot versions side-by-side |
| **ConversationalGEval** | **NO** | — | **MISSING** — custom evaluation criteria for multi-turn chatbot sessions |
| **DAGMetric** | **NO** | — | **MISSING** — compose multiple checks into a single metric graph (e.g. first check grounding, then check KB scope, then check formatting) |
| **ConversationalDAGMetric** | **NO** | — | **MISSING** — DAG metric for multi-turn flows |
| ExactMatchMetric | Partial | DSPy keyword check | DSPy keyword presence is similar but not identical — ExactMatch is stricter |
| PatternMatchMetric | Partial | DSPy formatting check | DSPy formatting constraints cover this partially |
| JsonCorrectnessMetric | **NO** | — | **MISSING** — if bot returns structured JSON responses, this validates schema correctness |

#### Content Quality & Safety Metrics (10 total)

| Metric | Covered? | How | Gap / Note |
|--------|----------|-----|------------|
| **HallucinationMetric** | **NO** | — | **MISSING** — distinct from Faithfulness. Detects fabricated facts not grounded in any context. High priority for policy bot |
| **BiasMetric** | **NO** | — | **MISSING** — Azure Foundry covers hate/unfairness but not subtle bias in framing or wording |
| **ToxicityMetric** | **NO** | — | **MISSING** — Azure Foundry covers violence/sexual/self-harm but not general toxicity of language |
| **SummarizationMetric** | **NO** | — | **MISSING** — if bot summarizes documents, this evaluates coverage and accuracy |
| **PIILeakageMetric** | **NO** | — | **MISSING — CRITICAL** for Customer and Private bots. If customer KB contains personal data, this detects whether bot leaks it in responses |
| **NonAdviceMetric** | **NO** | — | **MISSING** — prevents bot from giving legal, financial, or compliance advice. Essential for a PlayReady policy bot |
| **MisuseMetric** | **NO** | — | **MISSING** — detects if bot is manipulated into acting outside its purpose |
| **RoleViolationMetric** | **NO** | — | **MISSING** — detects when bot breaks its assigned role (e.g. acts as a general assistant instead of PlayReady bot) |
| **RoleAdherenceMetric** | **NO** | — | **MISSING** — verifies bot stays in character across a full session |
| RAGASFaithfulnessMetric | YES | RAGAS | Covered |

#### Task-Specific Metrics (6 total)

| Metric | Covered? | How | Gap / Note |
|--------|----------|-----|------------|
| **ToolCorrectnessMetric** | **NO** | — | **MISSING** — Foundry agent uses internal tools (search, retrieval). We never verify if it called the right tool |
| **ArgumentCorrectnessMetric** | **NO** | — | **MISSING** — even if tool is correct, arguments passed to it may be wrong |
| **TaskCompletionMetric** | **NO** | — | **MISSING** — did the bot actually complete the user's task? Requires trace data |
| **PromptAlignmentMetric** | **NO** | — | **MISSING** — does bot follow its system prompt instructions? |
| **KnowledgeRetentionMetric** | **NO** | — | **MISSING** — in multi-turn sessions, does bot remember facts stated earlier? |
| RagasMetric (wrapper) | YES | RAGAS | Generic wrapper — covered |

#### Agentic Metrics (6 total)

| Metric | Covered? | How | Gap / Note |
|--------|----------|-----|------------|
| **TopicAdherenceMetric** | **NO** | — | **MISSING** — does bot stay on PlayReady-related topics and refuse off-topic requests? |
| **StepEfficiencyMetric** | **NO** | — | **MISSING** — does the Foundry agent complete tasks in a reasonable number of steps? |
| **PlanAdherenceMetric** | **NO** | — | **MISSING** — does agent follow its retrieval-then-answer plan? Requires trace |
| **PlanQualityMetric** | **NO** | — | **MISSING** — is the agent's plan (retrieval strategy) good? |
| **GoalAccuracyMetric** | **NO** | — | **MISSING** — in a conversation, does the bot achieve the user's stated goal? |
| **ToolUseMetric** | **NO** | — | **MISSING** — conversational equivalent of ToolCorrectnessMetric across turns |

#### Conversational Metrics (6 total — none covered)

| Metric | Covered? | Gap / Note |
|--------|----------|------------|
| **TurnRelevancyMetric** | **NO** | Each turn's response relevance to that turn's input — we test single-turn only |
| **TurnFaithfulnessMetric** | **NO** | Per-turn grounding check across a session |
| **TurnContextualPrecisionMetric** | **NO** | Per-turn retrieval precision in multi-turn |
| **TurnContextualRecallMetric** | **NO** | Per-turn retrieval recall in multi-turn |
| **TurnContextualRelevancyMetric** | **NO** | Per-turn context relevance |
| **ConversationCompletenessMetric** | **NO** | Did the full conversation address all user intents? |

#### MCP Metrics (3 total — All Applicable, All Missing)

All three bots (Public, Customer, Private) use MCP (Model Context Protocol) for tool/resource access. These metrics are currently not evaluated at all.

| Metric | Covered? | Gap / Note |
|--------|----------|------------|
| **MCPTaskCompletionMetric** | **NO** | **MISSING** — did the bot complete its task using MCP tools? Each bot has different MCP tool access scope |
| **MCPUseMetric** | **NO** | **MISSING** — validates correct MCP tool/resource/prompt usage. Critical for verifying KB scope enforcement (customer bot should only use customer MCP resources) |
| **MultiTurnMCPUseMetric** | **NO** | **MISSING** — evaluates MCP usage patterns across a full multi-turn session. Important for detecting KB boundary leaks across conversation turns |

#### Multimodal Metrics (5 total — Not Applicable)

| Metric | Status |
|--------|--------|
| TextToImageMetric | N/A — chatbot is text-only |
| ImageEditingMetric | N/A |
| ImageCoherenceMetric | N/A |
| ImageHelpfulnessMetric | N/A |
| ImageReferenceMetric | N/A |

---

### Missing Metrics Summary — Prioritised for PlayReady

| Priority | Metric | Why It Matters for PlayReady |
|----------|--------|------------------------------|
| **P0** | PIILeakageMetric | Customer/Private bot MUST NOT leak personal data from KB |
| **P0** | NonAdviceMetric | Policy bot must not give legal/financial/compliance advice |
| **P1** | HallucinationMetric | Bot fabricating policy details is a critical failure |
| **P1** | TopicAdherenceMetric | Bot must stay on PlayReady topics, refuse off-topic |
| **P1** | GEval | Custom rubrics: KB boundary check, policy citation correctness |
| **P1** | RoleViolationMetric | Bot must stay in its assigned role |
| **P2** | ToolCorrectnessMetric | Foundry agent tool calls are untested today |
| **P2** | ArgumentCorrectnessMetric | Tool arguments may be wrong even if tool is correct |
| **P2** | TaskCompletionMetric | Did the bot actually help the user? |
| **P2** | ConversationCompletenessMetric | Are all user intents addressed in a session? |
| **P2** | KnowledgeRetentionMetric | Multi-turn: does bot remember context? |
| **P2** | PromptAlignmentMetric | Does bot follow its system prompt? |
| **P2** | RAGASContextualEntitiesRecall | Entity-level factual recall — more precise than passage recall |
| **P3** | BiasMetric | Beyond Azure safety — subtle framing bias |
| **P3** | ToxicityMetric | General language toxicity beyond Azure safety categories |
| **P3** | MisuseMetric | Adversarial prompt resistance |
| **P3** | PlanAdherenceMetric | Agent retrieval strategy quality (requires trace) |
| **P3** | StepEfficiencyMetric | Agent efficiency |
| **P3** | ArenaGEval | Compare public vs customer bot responses on same query |
| **P3** | All 5 Turn-level metrics | Full multi-turn evaluation (TurnRelevancy, TurnFaithfulness, etc.) |
| **P1** | MCPUseMetric | All 3 bots use MCP — verify correct MCP resource/tool usage per bot scope |
| **P1** | MCPTaskCompletionMetric | Did the bot complete its task via MCP tools? |
| **P2** | MultiTurnMCPUseMetric | Detect KB boundary leaks via MCP across conversation turns |

---

### Tracing Gaps

#### What PlayReady QA Has Today
- Playwright browser traces (screenshots, DOM snapshots) — UI layer only
- Basic latency via `latency_seconds` in RAGAS eval dataset
- No LLM-level span tracking
- No token usage per query
- No cost tracking per evaluation run
- No retriever span data (what chunks were retrieved, top_k, embedder used)

#### What DeepEval Tracing Provides (Not Wired In)

| Feature | DeepEval Capability | PlayReady Gap |
|---------|--------------------|--------------| 
| `@observe` decorator | Auto-instruments any function into a named span | Not applied to any PlayReady code |
| LLM spans | Captures model, provider, input/output tokens, cost per token | No token or cost tracking today |
| Retriever spans | Captures embedder, top_k, chunk_size, retrieved chunks | No retrieval tracing |
| Tool spans | Captures tool name, args, result per Foundry tool call | No tool-level tracing |
| Agent spans | Captures agent handoffs, available tools, decision steps | No agent-level tracing |
| OpenAI auto-patch | `patch_openai_client()` auto-captures all LLM calls | Not applied |
| OpenTelemetry export | OTLP-compatible trace export | Not configured |
| Trace → Test case link | Traces auto-associate with test cases for per-query drill-down | Not connected |
| Offline eval on trace | Run metrics on stored traces without re-querying the bot | Not available |
| `evaluate_trace()` | Evaluate stored traces against any metric | Not used |
| Cost per run tracking | Total token cost per evaluation run | Not tracked |
| Sampling rate | Control what % of production calls are traced | Not configured |

**Impact:** Without tracing, the dashboard's bug detector cannot fire LATENCY, COST, TOOL, AGENT, or CHUNKING bug categories for PlayReady runs. Those 5 of 12 bug categories are completely blind.

---

### Synthetic Test Case Generation Gaps

#### What PlayReady QA Has Today
- `scripts/generate_ragas_testset.py` — generates test cases via RAGAS testset generator
- `scripts/generate_conversational_testcases.py` — basic multi-turn generation
- `scripts/generate_negative_testcases.py` — negative scenario generation
- `scripts/generate_smart_testcases.py` — smart case generation
- All generators write to `data/test_cases_*.json`

#### What DeepEval Synthesizer Provides (Not Used)

| Feature | DeepEval Synthesizer | PlayReady Gap |
|---------|---------------------|---------------|
| `generate_goldens_from_docs()` | Feed PDFs from `data/kb/` directly — auto-chunks, embeds, generates Q&A pairs | Current generators don't read PDFs directly |
| 7 evolution strategies | REASONING, MULTICONTEXT, CONCRETIZING, CONSTRAINED, COMPARATIVE, HYPOTHETICAL, IN_BREADTH | Current generators have no evolution strategies |
| Quality filtering | `FiltrationConfig` with LLM-judged quality threshold per generated case | No quality scoring on generated cases today |
| Context deduplication | `context_similarity_threshold` removes near-duplicate test cases | No deduplication today |
| `generate_conversational_goldens_from_docs()` | Generates full multi-turn scenarios directly from KB PDFs | Current conversational generator is manual/template-based |
| `ConversationalGolden` output | Produces structured multi-turn test cases with scenario + expected_outcome + turns | No structured conversational goldens today |
| `generate_goldens_from_scratch()` | Generates test cases with no source document (tests bot's general knowledge boundary) | Not done — important for testing fallback behaviour |
| `EvolutionConfig` weights | Control probability of each evolution type per run | No evolution control today |
| `StylingConfig` | Control format, tone, complexity of generated inputs | No style control today |
| Ground truth via LLM judge | Expected output generated and scored by a critic LLM | Current ground truth is manually written |
| Export to CSV/JSON/JSONL | `synthesizer.save_as()` | Current output is always JSON |
| `generate_goldens_from_goldens()` | Evolve existing test cases into harder variants | Not done — useful for red teaming |

**Most valuable for PlayReady:** `generate_goldens_from_docs(data/kb/*.pdf)` with MULTICONTEXT evolution would auto-generate cross-document test cases that test KB boundary enforcement — exactly what the multi-bot scenario needs.

---

---

## Load Testing — Dashboard Integration

### Current State

The PlayReady QA project has `scripts/run_agent_load_test.py` which runs concurrent load tests against the Azure Foundry agent endpoint. It produces:

| Output File | Contents |
|-------------|----------|
| `agent_load_summary_TIMESTAMP.json` | Overall stats — P50/P95/P99, throughput, SLA evaluation, RCA, recommendations |
| `agent_load_details_TIMESTAMP.json` | Per-request records — `latency_seconds`, `token_usage`, `run_status`, `error_type` |
| `agent_load_details_TIMESTAMP.csv` | Flattened CSV version |
| `agent_load_bridge_TIMESTAMP.xlsx` | Excel report with latency percentiles, SLA, errors |

**Problem:** These results are not appearing on the dashboard Latency page.

---

### Why It Does Not Show on the Dashboard

The dashboard Latency page reads latency exclusively from **span timestamps** nested inside `trace.llmSpans[].startTime` and `endTime` (ISO8601). The load test outputs a flat `latency_seconds` number in files with the wrong name.

| Issue | Load Test Output | Dashboard Expects |
|-------|-----------------|-------------------|
| File name | `agent_load_details_*.json` | `test_run_*.json` |
| Latency format | `"latency_seconds": 5.2` (flat float) | `startTime` + `endTime` ISO8601 on each span |
| Structure | Flat request list | `testCases[].trace.llmSpans[]` |
| Span types | None | `llm`, `retriever`, `tool`, `agent`, `base` |

The dashboard's aggregator (`aggregator.py`) computes latency as:
```
duration_ms = (datetime.fromisoformat(endTime) - datetime.fromisoformat(startTime)) * 1000
```
It only reads files named `test_run_*.json` from `eval_history/`. Load test files never reach it.

---

### Integration Approach — Non-Disruptive Bridge

The fix is a **bridge script** that converts what the load test already produces into what the dashboard expects. Zero changes to `run_agent_load_test.py` or the existing RAGAS/Foundry eval pipeline.

```
run_agent_load_test.py              (unchanged)
        |
        v
agent_load_details_TIMESTAMP.json   (unchanged output)
        |
        v
scripts/load_test_to_dashboard.py   ← NEW bridge script
        |
        v
eval_history/test_run_loadtest_TIMESTAMP.json
        |
        v
Dashboard Latency Page              (now shows load test data)
```

**What the bridge does:**
- Reads `agent_load_details_*.json`
- For each request record, reconstructs span timestamps:
  - `startTime = recorded request_time` (ISO8601)
  - `endTime = startTime + latency_seconds`
- Wraps each request as a test case with one `llmSpan` of type `"llm"`
- Writes to `eval_history/test_run_loadtest_TIMESTAMP.json`
- Sets `project: "playready-loadtest"` in hyperparameters — load test runs appear as a **separate project** in the dashboard, completely isolated from regular eval runs

**Bot type support:** Pass `--bot-type` to the bridge so load test runs for each bot appear under their own project:
```
playready-loadtest-public
playready-loadtest-customer
playready-loadtest-private
```

---

### What Shows on Dashboard After Integration

| Dashboard Section | What Appears |
|------------------|--------------|
| Latency page | P50, P95, P99 per span type from load test runs |
| Projects filter | `playready-loadtest-*` isolated from regular eval projects |
| SLOs | Set `latency_p95 ≤ 5000ms` for load test project independently |
| Bug detector | LATENCY bug category fires if P95 exceeds 2× SLO threshold |
| Regular eval runs | Completely unaffected — different file prefix, different project |

---

### File Changes for Load Test Integration

| File | Change |
|------|--------|
| `scripts/load_test_to_dashboard.py` | NEW — bridge that converts load test JSON → `test_run_loadtest_*.json` |
| `scripts/run_agent_load_test.py` | No change — output format stays as-is |
| `eval_history/` | Receives new `test_run_loadtest_*.json` files from bridge |
| `.env` | No change needed |

---

*Last updated: 2026-06-06*
