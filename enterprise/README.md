# Repo 2 Scaffold — Enterprise PlayReady QA Automation

This folder is a **starter scaffold** for the future enterprise repo that will run against the Microsoft project environment.

## Purpose
Use the enterprise repo for:
- validating the real PlayReady chatbot UI in the Microsoft environment
- Azure AI Search-backed retrieval
- Azure OpenAI / Foundry-backed generation
- Entra ID authentication
- enterprise-safe reporting and audit evidence

## Recommended folder structure

```text
enterprise/
├── README.md
├── config/
│   ├── .env.enterprise.example
│   └── settings.enterprise.example.json
├── providers/
│   └── README.md
└── tests/
    └── README.md
```

## What changes vs the current repo

Current repo (`RAGAS_5_April_Automation`):
- local / QA evaluation baseline
- OpenAI or Azure OpenAI-compatible endpoint testing
- optional local PDF registry and testset generation

Future enterprise repo:
- same UI testing style
- same reporting style
- same chat model family and embedding model family where possible
- Azure AI Search for retrieval
- Foundry / Azure orchestration and traceability
- Entra ID for auth instead of local secrets

## What you normally update in the enterprise repo
Usually only **one file**:
- `.env`

Sometimes also:
- `config/settings.enterprise.json` if the Azure Search index name or deployment names change

You should **not** need to edit Python code for normal environment switching.

## Runtime flow

```text
PlayReady PDFs in enterprise storage
  -> ingestion/indexing pipeline
  -> Azure AI Search index + vectors
  -> chatbot backend / Foundry
  -> chatbot UI
  -> Playwright automation
  -> DSPy / RAGAS / Excel report
```
