# RAG Chatbot UI + DSPy + RAGAS Automation Framework

## Repo role and provider strategy

This current repository is now positioned as **Repo 1: Local / QA Evaluation** for PlayReady.

Recommended usage:
- use `openai` as the primary provider for evaluation runs
- keep the same chat model and embedding model names that will be used in the enterprise repo
- keep `ollama` only as an optional fallback for cheap local smoke tests

Helpful references:
- `config/env/.env.openai.example` — preferred OpenAI / Azure OpenAI-compatible profile
- `config/env/.env.ollama.example` — optional local fallback profile
- `docs/repo_split_strategy.md` — simple guide for the two-repo setup
- `enterprise/README.md` — scaffold for Repo 2 (Azure Search / Foundry / Entra ID)

## Recommended folder structure

```text
.
├── .env.example
├── .github/workflows/ci.yml
├── audit/
│   └── compliance_validator.py
├── conftest.py
├── data/
│   ├── pdf_registry.json
│   └── test_cases.json
├── dspy_layer/
│   └── ui_to_dspy.py
├── ragas_layer/
│   ├── dspy_to_ragas.py
│   └── ragas_runner.py
├── requirements.txt
├── tests/
│   ├── test_compliance_audit.py
│   ├── test_dspy_eval.py
│   ├── test_ragas_eval.py
│   └── test_ui_capture.py
└── ui/
    ├── pages/chatbot_page.py
    └── utils/
        ├── artifacts.py
        └── waits.py
```

## Quick start

1. Create a virtual environment and install dependencies:
   ```bash
   pip install -r requirements.txt
   python -m playwright install chromium
   ```
   > For the smoothest `dspy` + `ragas` installs, prefer **Python 3.11 or 3.12**.
2. Copy `.env.example` to `.env` and update `BASE_URL`, chatbot selectors, and your OpenAI/Azure OpenAI endpoint settings.
   > If you want a ready profile, start from `config/env/.env.openai.example`.
3. Run the suite in the same staged order used by CI:
   ```bash
   pytest -m compliance
   pytest -m ui
   pytest -m dspy
   pytest -m ragas
   ```

## If you are new: how to use this repo day-to-day

### 1) Choose one environment profile

Use the helper script to switch profiles:

```powershell
.\scripts\use_env_profile.ps1 -Profile openai -DryRun
.\scripts\use_env_profile.ps1 -Profile openai
```

Other options:

```powershell
.\scripts\use_env_profile.ps1 -Profile ollama
.\scripts\use_env_profile.ps1 -Profile enterprise -DryRun
```

### 2) Update only the `.env` file

For normal switching, you usually change **only one file**:
- `.env`

You do **not** need to edit Python code every time.

### 3) Only update data files when the KB or test questions change

- `data/pdf_registry.json` → update when your local PDF list changes
- `data/test_cases.json` → update when your test questions change
- `data/ragas_testset_config.json` → update only if you want a different test generation mix or size

### 4) Simple switching rule

| What you want to switch | Files you usually update |
|---|---|
| OpenAI ↔ Ollama in this repo | `.env` only |
| Change local PDFs | `.env` + `data/pdf_registry.json` |
| Regenerate local questions | maybe `data/ragas_testset_config.json`, then regenerate `data/test_cases.json` |
| Move to the future enterprise repo | use that repo's own `.env` only; keep the code mostly the same |

> For most day-to-day runs, the answer is: **update only `.env`**.

## Repo 2 enterprise scaffold

A starter layout for the enterprise repo is already added under:

- `enterprise/README.md`
- `enterprise/config/.env.enterprise.example`
- `enterprise/config/settings.enterprise.example.json`
- `enterprise/providers/README.md`
- `enterprise/tests/README.md`

Use that scaffold later when you create the separate Microsoft project repo.

## How to adapt to your chatbot UI

- Update selectors in `.env`:
  - `CHAT_WIDGET_BUTTON_SELECTOR`
  - `CHAT_INPUT_SELECTOR`
  - `CHAT_SEND_BUTTON_SELECTOR`
  - `BOT_MESSAGE_SELECTOR`
  - `CHAT_STREAMING_INDICATOR_SELECTOR`
  - `CHAT_CITATION_SELECTOR`
- If your widget is already expanded, `open_chat_widget()` safely exits when the input is visible.

## How to capture contexts

1. **Preferred:** expose citations/sources in the UI and set `CHAT_CITATION_SELECTOR`.
2. **Optional:** if your backend response returns retrieved chunks, enable `CAPTURE_NETWORK_CONTEXTS=true` and set `NETWORK_CONTEXT_URL_KEYWORD` to the chat API path (for example `/api/chat`).
3. If no contexts are available, the framework still evaluates deterministic checks and only runs RAGAS metrics that remain valid.

## How to model ~80 PDFs

- Keep one row per document in `data/pdf_registry.json`.
- For each PDF define:
  - `pdf_id`
  - `pdf_name`
  - `topic`
  - `expected_keywords`
  - `sample_questions`
- In `data/test_cases.json`, map each question to the expected supporting PDFs using:
  - `expected_pdfs`
  - `strict_grounding`

This scales cleanly to 80+ PDFs because the runtime logic matches citations/context text against the registry rather than hard-coding individual tests in Python.

## How to add new tests

- Add another object to `data/test_cases.json`.
- Keep the schema:
  - `id`
  - `prompt`
  - `required_keywords`
  - `forbidden_patterns`
  - `expect_fallback`
  - `fallback_patterns`
  - `ground_truth`
  - `expected_pdfs`
  - `strict_grounding`
  - `paraphrase_group`
  - `notes`

## Generate tests automatically with RAGAS

When you move from one PDF to a larger KB (for example 44 PDFs), you can generate a fresh `data/test_cases.json` automatically:

```bash
python scripts/generate_ragas_testset.py --config data/ragas_testset_config.json
```

What this does:

- reads the document list from `data/pdf_registry.json`
- loads readable PDFs and uses RAGAS testset generation when an evaluator LLM is available
- falls back to `sample_questions` from the registry if PDFs are missing or the LLM is unavailable
- overwrites `data/test_cases.json` and keeps timestamped backups in `artifacts/testsets/`

Helpful options:

```bash
python scripts/generate_ragas_testset.py --dry-run
python scripts/generate_ragas_testset.py --seed-only
python scripts/generate_ragas_testset.py --testset-size 50
```

Tune the mix of query types, number of questions, and export path in `data/ragas_testset_config.json`.

## How we know the bot answers ONLY from PDFs

The framework uses four layers of evidence:

1. **Expected source mapping**  
   Each test case declares the PDF(s) that are allowed to support the answer via `expected_pdfs`.

2. **Observed source evidence**  
   The UI layer captures visible citations and can also inspect network responses for retrieved chunks.

3. **DSPy deterministic validation**  
   The DSPy layer checks fallback behavior, required keywords, forbidden patterns, formatting, and whether the observed evidence matches the expected PDF registry.

4. **RAGAS grounding validation**  
   - `faithfulness` checks whether the answer is supported by retrieved PDF content.
   - `context_precision` / `context_recall` help expose the wrong-document problem when the retriever surfaces irrelevant PDF chunks.
   - If no contexts are exposed, the report clearly records the skipped metrics rather than pretending the answer is grounded.

> In strict-grounding cases, a mismatch between captured evidence and `expected_pdfs` is flagged in both the DSPy results and the compliance/RAGAS audit report.

## How to tune thresholds

Use `.env`:
- `DSPY_MIN_SCORE`
- `RAGAS_ANSWER_RELEVANCY_THRESHOLD`
- `RAGAS_FAITHFULNESS_THRESHOLD`

> If `OPENAI_API_KEY` is missing, LLM-based RAGAS metrics are skipped and the report records the reason.

## Enterprise Reporting Model

The framework now separates **immutable raw evidence** from the **human-friendly executive workbook**.

### What is preserved forever

Every completed evaluation run creates a timestamped archive folder under:

```text
artifacts/reports/<YYYY-MM-DD_HH-MM-SS>/
```

That folder preserves the latest raw evidence for that run without deleting historical runs:

- `ui_runs/` — raw chatbot evidence JSON, screenshots, and traces
- `dspy/` — raw DSPy CSV/JSON outputs
- `ragas/` — raw RAGAS CSV/JSON outputs and cache
- `system/` — supporting run-level files such as `pytest_report.html`

> Historical evidence is never removed by the reporting pipeline, so audit trails remain intact.

### What is overwritten safely

A single Excel workbook is regenerated on each run for non-technical stakeholders:

```text
reports/Latest_Report.xlsx
```

This file is intentionally overwritten and is built only from the **latest archived run data**. It is meant for:

- QA leads
- delivery managers
- audit reviewers
- business stakeholders who do not need to inspect JSON or code

### Where the real chatbot response lives

The real bot response is captured in:

```text
artifacts/ui_runs/<test_id>.json
```

and preserved for the current archived run in:

```text
artifacts/reports/<timestamp>/ui_runs/<test_id>.json
```

The `answer_text` shown in `reports/Latest_Report.xlsx` is copied directly from that artifact JSON so every Excel row remains traceable back to the original captured response.

### How QA and managers should read the Excel workbook

`reports/Latest_Report.xlsx` contains four sheets:

1. **Test Results** — one row per test with `PASS`/`FAIL`, full prompt, full real answer, and expected/matched PDFs
2. **PDF Coverage** — shows whether each registered PDF is covered by at least one test
3. **Failures Only** — a quick triage sheet for issues that need attention
4. **Summary Dashboard** — run totals and execution timestamp for audit summaries

Color coding is applied for quick review:

- `PASS` / `YES` = green
- `FAIL` = red
- `NO` = yellow

