# Evaluator Reference — PlayReady QA Automation

Complete picture of every evaluation framework wired into this project: what we run today,
what each metric measures, why it matters for a PlayReady DRM support chatbot, our custom
additions, and what exists upstream (in the `deepeval` source / RAGAS / Foundry ecosystems)
that we do **not** yet use.

Four evaluators are registered (see `FW_META` in the dashboard, `dashboard.html`):

| Evaluator | Color | Code location | Role |
|---|---|---|---|
| RAGAS | `#6366F1` indigo | `ragas_layer/ragas_runner.py` | Primary RAG-quality scorer (LLM + embeddings) |
| Azure Foundry | `#10B981` teal | `foundry_layer/foundry_evaluator.py` | Foundry-hosted quality / NLP-overlap / content-safety scorer |
| DSPy | `#F59E0B` amber | `dspy_layer/ui_to_dspy.py`, `ragas_layer/dspy_to_ragas.py` | Adapter & document-grounding bridge → feeds RAGAS |
| DeepEval | `#A78BFA` purple | `deepeval_layer/deepeval_evaluator.py` | Native DeepEval runner: custom GEval + standard metrics |

---

## 1. RAGAS — 13 metrics (our most comprehensive evaluator)

Source: `ragas_layer/ragas_runner.py`. All 13 are LLM/embedding-driven; thresholds are
env-configurable (e.g. `RAGAS_FAITHFULNESS_THRESHOLD=0.70`).

### Generation-quality metrics
| Metric | Class | What it measures | Why it matters here |
|---|---|---|---|
| `answer_relevancy` | `ResponseRelevancy` | Does the answer actually address the question (vs. going off-topic)? | Catches the bot drifting away from the PlayReady question asked |
| `answer_accuracy` | `FactualCorrectness` | Are the facts in the answer correct vs. ground truth? | Core correctness check for DRM/licensing facts (CDMi, PSSH, license servers, etc.) |
| `faithfulness` | `Faithfulness` | Is every claim in the answer supported by the retrieved context? | Prevents the bot inventing PlayReady behavior not in the docs |
| `response_correctness` | `AnswerCorrectness` | Combined factual + semantic similarity to ground truth | Holistic "is this answer right" score |
| `answer_completeness` | `SimpleCriteriaScore` (custom 1–5 rubric) | Does the answer cover *all* aspects of a multi-part question? | PlayReady questions are often multi-part ("how do I do X and what are the limits of Y") — partial answers are a common failure mode |

### Retrieval-quality metrics
| Metric | Class | What it measures | Why it matters here |
|---|---|---|---|
| `context_precision` | `LLMContextPrecisionWithReference` | Are the retrieved chunks actually relevant (signal-to-noise of retrieval)? | Tells us if the retriever is pulling in irrelevant PDF sections |
| `context_utilization` | `ContextUtilization` | Does the answer actually *use* the retrieved context it was given? | Flags cases where good context was retrieved but ignored |
| `context_recall` | `LLMContextRecall` | Did retrieval surface everything needed to answer fully? | Identifies knowledge-base / chunking gaps |
| `context_relevance` | `ContextRelevance` | Direct relevance score of context to the query | Lighter-weight companion to `context_precision` |
| `context_entity_recall` | `ContextEntityRecall` | Are key named entities (APIs, products, error codes) present in retrieved context? | Crucial for technical DRM terminology — missing entities = missing the point |
| `response_groundedness` | `ResponseGroundedness` | Is the response grounded in the context (answer-side counterpart to context metrics)? | Cross-checks faithfulness from the retrieval side |

### Robustness metrics
| Metric | Class | What it measures | Why it matters here |
|---|---|---|---|
| `noise_sensitivity_relevant` | `NoiseSensitivity(mode="relevant")` | Does the bot stay correct when given relevant-but-imperfect context? | Simulates real retrieval noise from large PDFs |
| `noise_sensitivity_irrelevant` | `NoiseSensitivity(mode="irrelevant")` | Does irrelevant context cause the bot to hallucinate or go off-topic? | Guards against distractor chunks derailing answers |

### Custom audit (not a RAGAS metric — built on top)
- **Document-grounding audit** (`_build_document_grounding_audit`): for test cases flagged
  `strict_grounding`, cross-checks `expected_pdfs` vs `matched_pdfs` and reports
  `wrong_document_cases` (cited the wrong PDF) and `unverifiable_cases` (no traceable source).
  This is **our own addition on top of RAGAS** — RAGAS has no native "did you cite the right
  source document" check, and for a DRM compliance bot, citing the wrong spec/PDF is a
  serious correctness issue RAGAS's generic metrics wouldn't catch.

---

## 2. Azure Foundry — 13 metrics

Source: `foundry_layer/foundry_evaluator.py` (`FOUNDRY_METRIC_METADATA`). This is a **fully
custom bridge** to Azure AI Foundry's evaluation API — there is no equivalent in the
downloaded `deepeval` source (that source only contains generic `azure_model.py` /
`azure_embedding_model.py` LLM-provider wrappers, not a Foundry evaluation harness).

### Quality (LLM-judged, scale 1–5)
| Metric | What it measures | Why it matters here |
|---|---|---|
| `coherence` | Is the response logically structured? | Technical DRM answers need to read as a coherent explanation, not a fact dump |
| `fluency` | Is the response grammatically natural? | Baseline writing-quality check |
| `relevance` | Is the response relevant to the query? | Cross-validates RAGAS's `answer_relevancy` from a different model/provider |
| `groundedness` | Is the response grounded in provided context? | Cross-validates RAGAS's `faithfulness` — a second opinion from a different evaluation engine |
| `similarity` | How similar is the response to ground truth? | Quick correctness proxy independent of RAGAS's correctness metrics |

### NLP overlap (lexical, scale 0.0–1.0, no LLM required)
| Metric | What it measures | Why it matters here |
|---|---|---|
| `f1_score` | Token-level precision+recall vs. ground truth | Cheap, deterministic sanity check that doesn't depend on an LLM judge |
| `rouge_score` | Recall-oriented n-gram overlap | Useful for catching answers that omit key terms even if "relevant" |
| `bleu_score` | Precision-oriented n-gram overlap | Classic MT-style overlap metric, complements ROUGE |
| `meteor_score` | Semantic-aware matching (synonyms, stemming) | Less brittle than exact n-gram overlap for technical paraphrasing |

### Safety (scale 0–7, lower = safer)
| Metric | What it measures | Why it matters here |
|---|---|---|
| `violence` | Violent content in the response | Standard responsible-AI guardrail |
| `sexual` | Sexually explicit content | Standard responsible-AI guardrail |
| `self_harm` | Self-harm-related content | Standard responsible-AI guardrail |
| `hate_unfairness` | Hate speech / unfair content | Standard responsible-AI guardrail |

**Why we run Foundry *and* RAGAS in parallel:** they overlap deliberately on
relevance/groundedness/correctness — running two independently-implemented evaluation
engines against the same answer acts as a cross-check (if RAGAS says "faithful" but Foundry's
`groundedness` disagrees, that's a signal worth investigating). Foundry uniquely adds the
**lexical-overlap** metrics (cheap, no-LLM sanity checks) and the **content-safety** suite,
neither of which RAGAS provides.

---

## 3. DSPy — adapter & grounding bridge (not an independent scorer)

Source: `dspy_layer/ui_to_dspy.py` (+ `ragas_layer/dspy_to_ragas.py`). DSPy here is **not**
producing pass/fail scores of its own — it's a normalization and verification layer that
sits *before* RAGAS in the pipeline.

| Component | What it does | Why it matters here |
|---|---|---|
| `UIArtifactAdapter` (`dspy.Module`) | Normalizes raw UI-captured chatbot artifacts (whitespace, casing) into a consistent schema | Raw UI exports are messy; RAGAS/DeepEval need clean, consistent fields |
| `detected_fallback` | Flags canned non-answers ("I don't know", "outside my scope", "please contact support", etc.) | Lets us exclude fallback responses from `answer_relevancy` scoring (a fallback isn't "irrelevant", it's a different failure mode — see `answer_relevancy_scope: non_fallback_only` in the RAGAS thresholds config) |
| `matched_pdfs` (via `match_pdfs_from_texts`) | Matches the answer + retrieved context against `data/pdf_registry.json` using strong-token (id/name/topic) or ≥2-keyword-hit evidence, filtering out generic terms (`playready`, `license`, `compliance`, …) | This is the data feed for the document-grounding audit described above — without DSPy's matching step, RAGAS would have no way to know *which* source PDF an answer is supposedly grounded in |
| `convert_dspy_predictions_to_ragas_dataset` | Converts adapted predictions into a RAGAS-ready `Dataset`, carrying `expect_fallback` / `strict_grounding` flags through | The actual hand-off point into the RAGAS pipeline |

**Custom for our project:** the entire `matched_pdfs` / PDF-registry-matching system is
project-specific — it only makes sense because our knowledge base is a fixed set of
PlayReady spec PDFs and we need to verify citation accuracy, not just generic faithfulness.

---

## 4. DeepEval — 6 metrics active (3 custom + 3 standard)

Source: `deepeval_layer/deepeval_evaluator.py`.

### Custom GEval rubrics (LLM-graded against PlayReady-specific criteria) — **our own metrics**
| Metric | Threshold / weight | Criteria summary | Why it matters here |
|---|---|---|---|
| `PlayReadyRelevance` | 0.7 / 1.0 | Does the answer directly address the PlayReady question without drifting into unrelated DRM/media topics? | Generic "relevance" metrics don't know that "PlayReady" ≠ "Widevine" ≠ "FairPlay" — this rubric is written specifically to penalize cross-DRM topic drift |
| `PlayReadyFaithfulness` | 0.7 / 1.0 | Score = faithful_claims / total_claims, every factual claim checked against retrieval context | A PlayReady-flavored faithfulness check that mirrors RAGAS's but with criteria worded for our domain and graded by a different LLM judge — another cross-check layer |
| `PlayReadyClarity` | 0.6 / 0.8 | Is the answer clearly structured and does it use correct terminology (license acquisition, CDMi, PSSH) for a developer/architect audience? | None of RAGAS/Foundry/DSPy check *terminology correctness for our specific domain* — this is the only metric that explicitly rewards correct use of PlayReady jargon |

### Standard DeepEval metrics
| Metric | Threshold | What it measures | Why it matters here |
|---|---|---|---|
| `AnswerRelevancyMetric` | 0.7 | Generic answer-to-question relevance | Third independent relevance signal (alongside RAGAS and Foundry) |
| `FaithfulnessMetric` | 0.7 | Generic claim-vs-context faithfulness | Third independent faithfulness signal |
| `HallucinationMetric` | 0.5 (inverted — lower is better) | Does the answer introduce facts not present anywhere in context? | Complements faithfulness — faithfulness asks "is each claim supported", hallucination asks "did you invent something new" — subtly different failure modes |

Falls back to deterministic scoring if no OpenAI/Azure-OpenAI LLM is configured.

---

## 5. What exists upstream that we DON'T use yet

The folder `C:\Users\SushrutNistane\Downloads\Deepeval-playready-foundry` is the **upstream
open-source `confident-ai/deepeval` package source** (not a custom PlayReady project — no
PlayReady-specific code lives there). It ships ~47 metric classes; we actively use 4
(`AnswerRelevancyMetric`, `FaithfulnessMetric`, `HallucinationMetric`, `GEval`).

### 5a. Imported but dormant (1)
- **`ContextualRelevancyMetric`** — imported at `deepeval_evaluator.py:143` but never
  instantiated (the dispatch loop only handles `AnswerRelevancy`/`Faithfulness`/`Hallucination`
  types). One line of wiring away from being live. Would check whether *retrieved context*
  (not the answer) is relevant to the question — a useful complement to RAGAS's
  `context_relevance`.

### 5b. Available upstream, never integrated (~41)

**Safety / Compliance** — `BiasMetric`, `ToxicityMetric`, `PIILeakageMetric`,
`NonAdviceMetric`, `MisuseMetric`, `RoleViolationMetric`
> *Relevance:* Foundry already covers violence/sexual/self-harm/hate. Bias, PII leakage, and
> "misuse" detection would be the most plausible additions if compliance scope grows — a DRM
> support bot shouldn't leak licensing keys/credentials or give bypass instructions, which
> `MisuseMetric`/`PIILeakageMetric` are designed to catch.

**Retrieval / RAG** — `ContextualRecallMetric`, `ContextualPrecisionMetric`
> *Relevance:* Would round out the contextual-relevancy metric we already have pending,
> giving DeepEval its own full RAG triad — though RAGAS already covers this ground (and more)
> with `context_precision`/`context_recall`/`context_relevance`/`context_entity_recall`.

**Structural / exact-match** — `ExactMatchMetric`, `PatternMatchMetric`,
`JsonCorrectnessMetric`, `DAGMetric`
> *Relevance:* Useful only if the bot ever needs to produce structured output (JSON configs,
> exact error codes) — not applicable to today's free-text Q&A use case.

**Conversational / multi-turn** — `KnowledgeRetentionMetric`, `RoleAdherenceMetric`,
`ConversationCompletenessMetric`, `ConversationalGEval`, `ConversationalDAGMetric`,
`TurnRelevancyMetric`, `TurnFaithfulnessMetric`, `TurnContextualPrecisionMetric`,
`TurnContextualRecallMetric`, `TurnContextualRelevancyMetric`
> **Correction (was previously marked "not applicable"):** our *evaluation pipeline* currently
> only scores single-turn Q&A artifacts, but the live bots are conversational and — per
> `docs/multi_bot_strategy.md` — span Public/Customer/Private personas with different
> session lengths and KB-boundary risks across turns. `KnowledgeRetentionMetric`,
> `RoleAdherenceMetric`, and `ConversationCompletenessMetric` are flagged there as **P2
> gaps** (does the bot remember context, stay in role, and resolve the user's full intent
> across a session?). The `Turn*` metrics remain **P3** ("full multi-turn evaluation") —
> lower priority but not "not applicable". See the prioritised gap table in
> `multi_bot_strategy.md` for the full reasoning.

**Agentic / tool-use** — `TaskCompletionMetric`, `ToolCorrectnessMetric`, `ToolUseMetric`,
`TopicAdherenceMetric`, `StepEfficiencyMetric`, `PlanAdherenceMetric`, `PlanQualityMetric`,
`GoalAccuracyMetric`, `ArgumentCorrectnessMetric`, `PromptAlignmentMetric`
> **Correction (was previously marked "not applicable"):** the Foundry-hosted bots *are*
> agentic — they call internal retrieval/search tools — and `multi_bot_strategy.md` lists
> `ToolCorrectnessMetric` and `ArgumentCorrectnessMetric` as **P2 gaps** ("Foundry agent
> tool calls are untested today" / "tool arguments may be wrong even if tool is correct").
> `TopicAdherenceMetric` is rated **P1** (must stay on PlayReady topics, refuse off-topic —
> directly relevant to a policy bot guarding against misuse). `TaskCompletionMetric`,
> `PromptAlignmentMetric`, `GoalAccuracyMetric`, `PlanAdherenceMetric`/`PlanQualityMetric`,
> `StepEfficiencyMetric`, and `ToolUseMetric` round out **P2/P3** gaps once trace data is
> available. None of these are "not applicable" — they were simply not yet prioritised.

**MCP-specific** — `MCPTaskCompletionMetric`, `MultiTurnMCPUseMetric`, `MCPUseMetric`
> **Correction (was incorrectly marked "not applicable" — flagged by the user):** all three
> bots (Public, Customer, Private) **do** use MCP (Model Context Protocol) for tool/resource
> access, scoped per persona via a hierarchical storage path (folder → sub-folder → PDF).
> The Public Bot's MCP tools are scoped to public resources only; the Customer Bot adds
> customer-specific KB resources; the Private Bot has full public + all-customer access.
> `multi_bot_strategy.md` rates this exact gap **"3 total — All Applicable, All Missing"**:
> | Metric | Priority | Why it matters for our 3-persona architecture |
> |---|---|---|
> | `MCPUseMetric` | **P1** | Verifies the bot only invokes MCP tools/resources within its tier's scope — e.g. catches a Public Bot wrongly calling a Customer-KB MCP resource (a KB-boundary leak) |
> | `MCPTaskCompletionMetric` | **P1** | Confirms the bot completed the user's task using the *correct* MCP tools for its access tier |
> | `MultiTurnMCPUseMetric` | **P2** | Detects KB-boundary leaks that only emerge across a multi-turn session (e.g. a customer escalates a question and the bot drifts into private-tier MCP resources by turn 3) |
>
> This is one of the most consequential gaps in the whole 73-metric landscape — MCP scope
> enforcement is the mechanism that keeps customer data out of the public bot and keeps
> client A's data out of client B's session. None of RAGAS/Foundry/DeepEval's currently-active
> 32 metrics check *which* MCP resource was called — only whether the resulting answer
> "sounds" relevant/faithful/grounded. A bot could score perfectly on all 32 active metrics
> while silently leaking cross-tenant data through a wrongly-scoped MCP call, and we would
> never know. **`MCPUseMetric` + `MCPTaskCompletionMetric` should be treated as P1 additions.**

**Summarization** — `SummarizationMetric`
> *Relevance:* Genuinely low — the bots answer scoped questions from retrieved chunks, they
> don't produce whole-document summaries. `multi_bot_strategy.md` still lists it as a
> technical "MISSING" entry (for completeness) but assigns it no priority tier.

**Arena / comparative** — `ArenaGEval`
> *Relevance:* Could be interesting later for "which bot/model answers better" head-to-head
> comparisons (we already compare runs in the dashboard's "Compare Runs" page, but via
> separately-run scores, not a head-to-head judge).

**Multimodal / image** — `TextToImageMetric`, `ImageEditingMetric`, `ImageCoherenceMetric`,
`ImageHelpfulnessMetric`, `ImageReferenceMetric`
> *Relevance:* Not applicable — text-only chatbot, no image generation/editing.

### 5c. RAGAS wrapper in upstream DeepEval — overlap, not a gap
`deepeval/metrics/ragas.py` provides thin wrapper classes (e.g.
`RAGASContextualPrecisionMetric`) that run individual RAGAS metrics one-at-a-time through
DeepEval's `BaseMetric` interface. **We bypass this entirely** and run RAGAS natively via
`ragas_layer/ragas_runner.py` with all 13 metrics in one batched `evaluate()` call — broader
coverage and better performance than the wrapper would give us. Nothing pending here; our
approach supersedes the upstream bridge.

### 5d. Integrations in upstream DeepEval — not adopted
`agentcore`, `crewai`, `google_adk`, `hugging_face`, `langchain`, `llama_index`,
`openinference`, `pydantic_ai`, `strands` tracing/framework integrations ship with the
upstream package. We use **none of them** — the project has its own custom
`local_trace_exporter` tracer (visible as the `__FULL_DEEP_TRACER_INJECTED__` block at the
top of every `*_layer` evaluator file) and custom dashboard bridges
(`*_to_dashboard.py` files) instead.

---

## 6. Summary — at a glance

| | RAGAS | Foundry | DSPy | DeepEval |
|---|---|---|---|---|
| Active metrics | 13 | 13 | 0 (adapter role) | 6 (3 custom + 3 standard) |
| Custom additions | Document-grounding audit | — (fully custom evaluator itself) | PDF-registry matching, fallback detection | 3 PlayReady-specific GEval rubrics |
| Unique strength | Broadest RAG-quality coverage (retrieval + generation + robustness) | Lexical-overlap + content-safety, independent scoring engine | Pre-processing & citation-accuracy verification | Domain-tuned LLM-judged rubrics with PlayReady terminology awareness |
| Overlap w/ others | relevancy/faithfulness cross-checked by Foundry & DeepEval | relevance/groundedness/similarity cross-check RAGAS | feeds normalized data to RAGAS | relevancy/faithfulness/hallucination triangulate against RAGAS & Foundry |

**Total active evaluation signals across the suite: ~32 metrics** (13 RAGAS + 13 Foundry + 6
DeepEval) **+ 1 dormant** (`ContextualRelevancyMetric`) **+ ~41 unused-but-available** upstream,
of which only a handful (Bias, PII Leakage, Misuse, Contextual Recall/Precision) are realistically
relevant to this project's single-turn RAG/DRM-support use case.

**Custom metrics built specifically for this project** (none of which exist in any upstream
source — these are PlayReady QA-automation originals):
1. RAGAS document-grounding audit (`wrong_document_cases` / `unverifiable_cases`)
2. DSPy PDF-registry citation matcher (`matched_pdfs`, strong-token + keyword-hit logic)
3. DSPy fallback-response detector (`detected_fallback`)
4. DeepEval `PlayReadyRelevance` GEval rubric (cross-DRM topic-drift detection)
5. DeepEval `PlayReadyFaithfulness` GEval rubric (PlayReady-worded claim verification)
6. DeepEval `PlayReadyClarity` GEval rubric (PlayReady terminology correctness: CDMi, PSSH, license acquisition)
7. The entire Azure Foundry evaluator bridge (`foundry_layer/foundry_evaluator.py`) — a
   from-scratch integration with no upstream equivalent in the deepeval source

---

## 7. Master tally — every metric across all three ecosystems (73 total)

Counting every distinct metric definition across RAGAS + Azure Foundry + DeepEval (DSPy
contributes no scoring metrics of its own — it's an adapter/bridge role) gives a precise
grand total of **73**.

| Ecosystem | Total defined | ✅ Used | ⏳ Pending | ❌ Not used |
|---|---|---|---|---|
| RAGAS | 13 | 13 | 0 | 0 |
| Azure Foundry | 13 | 13 | 0 | 0 |
| DeepEval (upstream classes) | 47 | 4 classes → 6 active instances | 1 | 42 |
| **TOTAL** | **73** | **32 active instances (30 unique definitions)** | **1** | **42** |

### 7a. ✅ Used — 32 active metrics

**RAGAS (13/13 used):** answer_relevancy, answer_accuracy, faithfulness, response_correctness,
answer_completeness, context_precision, context_utilization, context_recall, context_relevance,
context_entity_recall, response_groundedness, noise_sensitivity_relevant, noise_sensitivity_irrelevant

**Azure Foundry (13/13 used):** coherence, fluency, relevance, groundedness, similarity,
f1_score, rouge_score, bleu_score, meteor_score, violence, sexual, self_harm, hate_unfairness

**DeepEval (6 active instances, from 4 classes):**
- `GEval` ×3 custom rubrics → `PlayReadyRelevance`, `PlayReadyFaithfulness`, `PlayReadyClarity`
- `AnswerRelevancyMetric`
- `FaithfulnessMetric`
- `HallucinationMetric`

### 7b. ⏳ Pending — 1 metric
- `ContextualRelevancyMetric` (DeepEval) — imported at `deepeval_evaluator.py:143`, never instantiated

### 7c. ❌ Not used — 42 metrics, re-graded by actual relevance to our 3-persona MCP architecture

> **Revision note:** an earlier pass through this list judged the Conversational, Agentic,
> and MCP groups (29 of the 42) as "not applicable" on the assumption that the bots are
> simple single-turn, tool-free Q&A bots. That assumption was **wrong** — per
> `docs/multi_bot_strategy.md`, all three bot personas (Public / Customer / Private) are
> conversational, are Foundry *agents* that call internal retrieval tools, and — critically —
> all use **MCP (Model Context Protocol)** to access hierarchically-scoped KB resources
> (public-only for the Public bot, public+own-customer for the Customer bot, public+all-clients
> for the Private bot). The table below replaces the old blanket "not applicable" framing with
> the priority grades (P0–P3) already established in `multi_bot_strategy.md`'s gap analysis.

Rather than group these 42 by metric *category* (which obscures urgency), they're sorted
below into **action tiers** — what to add now, soon, later, or not at all — based on the
P0–P3 priorities in `multi_bot_strategy.md`, reconciled against what's verifiably already
active in `deepeval_evaluator.py` (a few entries in that doc's prioritised list —
`HallucinationMetric`, `GEval`, RAGAS `context_entity_recall` — turned out to be stale;
they're already covered and excluded from the tiers below).

#### 🔴 Tier 1 — ADD NOW: 6 metrics (P0 + P1)
The single biggest blind spot across all 32 active metrics: **none of them check whether a
bot stayed inside its MCP/KB access scope.** A bot can score perfectly on
faithfulness/relevance/groundedness while silently leaking Customer-A's data into
Customer-B's session, or exposing Private-tier KB through the Public bot — and today,
nothing would catch it.

| Metric | Priority | Why it's urgent |
|---|---|---|
| `PIILeakageMetric` | P0 | Customer/Private bots hold personal data — must verify it never leaks into a response |
| `NonAdviceMetric` | P0 | Policy bot must not give unauthorized legal/financial/compliance advice |
| `MCPUseMetric` | P1 | The *only* metric that can catch a Public bot calling a Customer-tier MCP resource (cross-tenant leak) |
| `MCPTaskCompletionMetric` | P1 | Confirms the bot used the *correct* MCP tools for its access tier to complete the task |
| `TopicAdherenceMetric` | P1 | Bot must stay on PlayReady topics and refuse off-topic / adversarial prompts |
| `RoleViolationMetric` | P1 | Detects the bot breaking its assigned persona (e.g. Public bot behaving like Private bot) |

#### 🟡 Tier 2 — ADD SOON: 7 metrics (P2)
Next wave, once Tier 1 is wired in and trace data is flowing through the tracer.

| Metric | Why |
|---|---|
| `MultiTurnMCPUseMetric` | Catches MCP scope leaks that only emerge across a multi-turn session |
| `ToolCorrectnessMetric` | Foundry agent's internal tool calls are currently untested |
| `ArgumentCorrectnessMetric` | The tool may be right but its arguments may still be wrong |
| `TaskCompletionMetric` | Did the bot actually resolve the user's request? |
| `ConversationCompletenessMetric` | Were all of the user's intents addressed across the session? |
| `KnowledgeRetentionMetric` | Does the bot remember facts stated earlier in the same session? |
| `PromptAlignmentMetric` | Does the bot follow its system-prompt instructions? |

#### 🟢 Tier 3 — DEFER: 11 metrics (P3)
Real value, lower urgency — revisit after Tiers 1–2 land and conversational/agentic trace
data is mature.

`BiasMetric`, `ToxicityMetric`, `MisuseMetric`, `PlanAdherenceMetric`, `StepEfficiencyMetric`,
`ArenaGEval` (great for Public vs. Customer vs. Private side-by-side response comparison),
and the five turn-level metrics — `TurnRelevancyMetric`, `TurnFaithfulnessMetric`,
`TurnContextualPrecisionMetric`, `TurnContextualRecallMetric`, `TurnContextualRelevancyMetric`.

#### ⚪ Tier 4 — SKIP: 18 metrics
Either redundant with metrics you already run, or genuinely not applicable to a text-only
RAG chatbot suite.

| Reason to skip | Metrics |
|---|---|
| Redundant — RAGAS already covers this natively | `ContextualRecallMetric`, `ContextualPrecisionMetric` |
| Low value for free-text Q&A (no structured/JSON output) | `ExactMatchMetric`, `PatternMatchMetric`, `JsonCorrectnessMetric`, `DAGMetric` |
| Composite wrappers — add the underlying metrics individually first | `ConversationalGEval`, `ConversationalDAGMetric` |
| Lower-value agentic extras, not in the prioritised gap list | `RoleAdherenceMetric`, `GoalAccuracyMetric`, `ToolUseMetric`, `PlanQualityMetric` |
| Bots answer scoped questions, they don't summarize whole documents | `SummarizationMetric` |
| Text-only chatbot — no image generation/editing | `TextToImageMetric`, `ImageEditingMetric`, `ImageCoherenceMetric`, `ImageHelpfulnessMetric`, `ImageReferenceMetric` |

---

### How many do we need to add now?

**6 metrics — Tier 1 (P0 + P1):** `PIILeakageMetric`, `NonAdviceMetric`, `MCPUseMetric`,
`MCPTaskCompletionMetric`, `TopicAdherenceMetric`, `RoleViolationMetric`.

Looking two waves out: **6 now + 7 soon = 13 metrics** closes every P0/P1/P2 gap identified
for the multi-tenant, MCP-scoped, multi-persona architecture. The remaining 11 (Tier 3) and
18 (Tier 4) can stay parked — adding them wouldn't move the needle on the architecture's
actual risk surface (cross-tenant data leakage via MCP, PII exposure, role/topic drift).

**Bottom line:** 32 used + 1 pending + 42 unused = **73**. Of the 42 unused, **6 should be
added immediately**, **7 soon after**, **11 deferred**, and **18 skipped** as redundant or
not applicable.

---

## 8. Combined DeepEval roster after expansion (6 → 19 metrics)

All 13 Tier-1 + Tier-2 recommended additions are **DeepEval-native classes** — RAGAS and
Foundry don't ship MCP-, role-, PII-, or conversational-aware metrics, so this expansion
lands entirely in `deepeval_layer/deepeval_evaluator.py`. The table below shows the existing
6 active metrics alongside the 13 recommended additions as one combined roster.

| # | Metric | Status | Type | What it adds to the suite |
|---|---|---|---|---|
| 1 | `PlayReadyRelevance` (GEval) | ✅ existing | Custom rubric | On-topic check for PlayReady questions |
| 2 | `PlayReadyFaithfulness` (GEval) | ✅ existing | Custom rubric | PlayReady-worded claim-vs-context check |
| 3 | `PlayReadyClarity` (GEval) | ✅ existing | Custom rubric | PlayReady terminology/structure check |
| 4 | `AnswerRelevancyMetric` | ✅ existing | Standard | Generic relevance (cross-checks RAGAS/Foundry) |
| 5 | `FaithfulnessMetric` | ✅ existing | Standard | Generic faithfulness (cross-checks RAGAS/Foundry) |
| 6 | `HallucinationMetric` | ✅ existing | Standard | Fabricated-fact detection |
| 7 | `PIILeakageMetric` | 🆕 Tier 1 (P0) | Standard | Personal-data leak detection — Customer/Private bots |
| 8 | `NonAdviceMetric` | 🆕 Tier 1 (P0) | Standard | Blocks unauthorized legal/financial/compliance advice |
| 9 | `MCPUseMetric` | 🆕 Tier 1 (P1) | Standard | MCP resource/tool scope verification per persona tier |
| 10 | `MCPTaskCompletionMetric` | 🆕 Tier 1 (P1) | Standard | Confirms task completed via correctly-scoped MCP tools |
| 11 | `TopicAdherenceMetric` | 🆕 Tier 1 (P1) | Standard | Stays on PlayReady topic, refuses off-topic/adversarial prompts |
| 12 | `RoleViolationMetric` | 🆕 Tier 1 (P1) | Standard | Detects persona break (e.g. Public bot acting like Private bot) |
| 13 | `MultiTurnMCPUseMetric` | 🆕 Tier 2 (P2) | Conversational | MCP-scope leak detection across multi-turn sessions |
| 14 | `ToolCorrectnessMetric` | 🆕 Tier 2 (P2) | Standard | Foundry agent's internal tool-call correctness |
| 15 | `ArgumentCorrectnessMetric` | 🆕 Tier 2 (P2) | Standard | Validates tool-call arguments, not just tool choice |
| 16 | `TaskCompletionMetric` | 🆕 Tier 2 (P2) | Standard | Did the bot resolve the user's actual request? |
| 17 | `ConversationCompletenessMetric` | 🆕 Tier 2 (P2) | Conversational | Were all user intents addressed across the session? |
| 18 | `KnowledgeRetentionMetric` | 🆕 Tier 2 (P2) | Conversational | Does the bot remember earlier-session facts? |
| 19 | `PromptAlignmentMetric` | 🆕 Tier 2 (P2) | Standard | Adherence to system-prompt instructions |

**Net effect:** DeepEval's footprint in this project would roughly **triple** (6 → 19 active
metrics), making it the layer specifically responsible for guarding **persona-scope
integrity** (MCP, role, topic, PII, advice-boundaries) — a job neither RAGAS's nor Foundry's
26 currently-active metrics are equipped to do, since neither framework ships MCP- or
role-aware metrics.

### 8a. Development plan — what changes in `deepeval_evaluator.py` to support this

The 19-metric roster splits into three implementation tracks by the kind of test-case data
each group needs:

**Track 1 — Drop-in additions to `STANDARD_METRICS` (10 metrics, no architecture change)**
`PIILeakageMetric`, `NonAdviceMetric`, `MCPUseMetric`, `MCPTaskCompletionMetric`,
`TopicAdherenceMetric`, `RoleViolationMetric`, `ToolCorrectnessMetric`,
`ArgumentCorrectnessMetric`, `TaskCompletionMetric`, `PromptAlignmentMetric`
> These all run on a single-turn `LLMTestCase`, exactly like the existing
> `AnswerRelevancyMetric`/`FaithfulnessMetric`/`HallucinationMetric`. Adding them is
> mechanically identical to the existing pattern: extend the `STANDARD_METRICS` list (growing
> it from **3 → 13 entries**) and add one `elif sm["type"] == "..."` branch per metric in the
> dispatch loop at lines 175–185. **No new GEval rubrics needed** — these are DeepEval's
> built-in classes, not custom-authored criteria. `GEVAL_DEFINITIONS` stays at 3.

**Track 2 — Conversational test cases (3 metrics, new code path)**
`MultiTurnMCPUseMetric`, `ConversationCompletenessMetric`, `KnowledgeRetentionMetric`
> These require `ConversationalTestCase` (a sequence of turns), not the single-turn
> `LLMTestCase` the evaluator currently builds from `_load_dataset`. This means: (a) a new
> dataset loader that groups artifact rows into sessions/turns instead of treating each row
> as an independent case, and (b) a parallel `run_conversational_evaluation()` path alongside
> the existing `run_deepeval_evaluation()`. This is the same multi-turn-readiness gap noted
> for the RAGAS/Foundry "Conversational" metric groups — solving it once here would unlock
> those too.

**Track 3 — Requires MCP trace instrumentation (3 metrics, depends on tracer upgrade)**
`MCPUseMetric`, `MCPTaskCompletionMetric`, `MultiTurnMCPUseMetric`
> These need to know **which MCP tool/resource was actually invoked** and **what scope that
> bot persona is allowed**. That data has to come from the `local_trace_exporter` tracer
> (the `__FULL_DEEP_TRACER_INJECTED__` block already present in every `*_layer` file) —
> specifically, it needs to capture MCP tool-call spans (tool name, resource path, persona
> tier) the way it already captures evaluator spans. Until the tracer emits that data, these
> three metrics can be *wired in* but won't have meaningful inputs to score. **Recommended
> sequencing:** instrument MCP trace capture first, then land `MCPUseMetric` /
> `MCPTaskCompletionMetric` (Track 1, single-turn) before attempting `MultiTurnMCPUseMetric`
> (Track 2, needs both conversational cases *and* trace data).

### 8b. Suggested rollout order
1. **Now:** Track 1 minus the two MCP metrics (8 metrics) — pure `STANDARD_METRICS` additions, zero new infrastructure
2. **Next:** Instrument MCP tool-call spans in `local_trace_exporter` (infrastructure work, unlocks 3 metrics)
3. **Then:** `MCPUseMetric` + `MCPTaskCompletionMetric` (Track 1, now unblocked by step 2)
4. **Then:** Build the conversational/session test-case path (infrastructure work, unlocks Track 2)
5. **Finally:** `MultiTurnMCPUseMetric`, `ConversationCompletenessMetric`, `KnowledgeRetentionMetric`

This sequencing front-loads the 8 zero-infrastructure wins, then tackles the two
infrastructure investments (MCP tracing, conversational test cases) each exactly once —
each investment unlocks multiple metrics rather than being built per-metric.
