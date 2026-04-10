#!/bin/bash
# Run this in Azure Cloud Shell after uploading artifacts_ui_runs.zip
# Usage: bash setup_cloudshell.sh

set -e
cd ~/playready-qa-automation 2>/dev/null || git clone https://github.com/Sushrut-01/playready-qa-automation.git
cd ~/playready-qa-automation

echo "==> Installing packages..."
pip install --user "ragas==0.4.3" openpyxl rapidfuzz pypdf datasets pandas \
  langchain-openai openai azure-identity tenacity dspy-ai pytest pytest-html python-dotenv --quiet

echo "==> Patching conftest.py..."
python3 - << 'PYEOF'
content = open('conftest.py').read()
old = 'from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright\n\nfrom ui.pages.chatbot_page import ChatbotPage\nfrom ui.utils.artifacts import attach_screenshot_on_failure, attach_trace_on_failure, get_test_artifact_dir'
new = 'try:\n    from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright\n    from ui.pages.chatbot_page import ChatbotPage\n    from ui.utils.artifacts import attach_screenshot_on_failure, attach_trace_on_failure, get_test_artifact_dir\n    _PLAYWRIGHT_AVAILABLE = True\nexcept ModuleNotFoundError:\n    _PLAYWRIGHT_AVAILABLE = False'
open('conftest.py', 'w').write(content.replace(old, new))
print("  conftest.py OK")
PYEOF

echo "==> Patching ragas_runner.py..."
python3 - << 'PYEOF'
import re, os

content = open('ragas_layer/ragas_runner.py').read()

# Fix 1: Replace _build_ragas_metric_catalog
old_func = re.search(r'def _build_ragas_metric_catalog.*?(?=\ndef )', content, re.DOTALL)
if old_func:
    new_func = '''def _build_ragas_metric_catalog(ragas_llm, ragas_embeddings):
    from ragas.metrics._faithfulness import Faithfulness
    from ragas.metrics._answer_relevance import ResponseRelevancy
    from ragas.metrics._factual_correctness import FactualCorrectness
    from ragas.metrics._context_precision import LLMContextPrecisionWithReference, ContextUtilization
    from ragas.metrics._context_recall import LLMContextRecall
    from ragas.metrics._context_entities_recall import ContextEntityRecall
    from ragas.metrics._noise_sensitivity import NoiseSensitivity
    import os
    strictness = int(os.getenv("RAGAS_ANSWER_RELEVANCY_STRICTNESS", "3"))
    return {
        "faithfulness": Faithfulness(llm=ragas_llm) if ragas_llm else None,
        "answer_relevancy": ResponseRelevancy(llm=ragas_llm, embeddings=ragas_embeddings, strictness=strictness) if ragas_llm and ragas_embeddings else None,
        "answer_accuracy": FactualCorrectness(llm=ragas_llm, name="answer_accuracy") if ragas_llm else None,
        "context_precision": LLMContextPrecisionWithReference(llm=ragas_llm, name="context_precision") if ragas_llm else None,
        "context_utilization": ContextUtilization(llm=ragas_llm) if ragas_llm else None,
        "context_recall": LLMContextRecall(llm=ragas_llm) if ragas_llm else None,
        "context_relevance": None,
        "response_groundedness": None,
        "context_entity_recall": ContextEntityRecall(llm=ragas_llm) if ragas_llm else None,
        "noise_sensitivity_relevant": NoiseSensitivity(llm=ragas_llm, name="noise_sensitivity_relevant") if ragas_llm else None,
        "noise_sensitivity_irrelevant": NoiseSensitivity(llm=ragas_llm, name="noise_sensitivity_irrelevant") if ragas_llm else None,
    }

'''
    content = content.replace(old_func.group(), new_func)
    print("  metric catalog OK")

# Fix 2: ModeMetric column remap
old_col = '''                if metric_name not in result_df.columns:
                    payload["skipped_metrics"].append(
                        {"metric": metric_name, "reason": "Metric result column was missing from the RAGAS output."}
                    )
                    return'''
new_col = '''                if metric_name not in result_df.columns:
                    mode_col = next(
                        (c for c in result_df.columns if c.startswith(f"{metric_name}(mode=")),
                        None,
                    )
                    if mode_col:
                        result_df = result_df.rename(columns={mode_col: metric_name})
                    else:
                        payload["skipped_metrics"].append(
                            {"metric": metric_name, "reason": "Metric result column was missing from the RAGAS output."}
                        )
                        return'''
if old_col in content:
    content = content.replace(old_col, new_col)
    print("  ModeMetric column remap OK")

open('ragas_layer/ragas_runner.py', 'w').write(content)
PYEOF

echo "==> Extracting artifacts..."
unzip -o ~/artifacts_ui_runs.zip -d artifacts/ > /dev/null 2>&1 && echo "  artifacts OK" || echo "  WARNING: Upload artifacts_ui_runs.zip first via Cloud Shell upload button"

echo "==> Getting Azure token..."
TOKEN=$(python3 -c "from azure.identity import DefaultAzureCredential; t = DefaultAzureCredential().get_token('https://cognitiveservices.azure.com/.default'); print(t.token)")
echo "  Token length: ${#TOKEN}"

echo "==> Writing .env..."
cat > .env << EOF
LLM_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=$TOKEN
AZURE_OPENAI_BASE_URL=https://dev-playready-fdry-public.openai.azure.com/
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
AZURE_OPENAI_API_VERSION=2024-08-01-preview
RAGAS_METRICS_PROFILE=full
RAGAS_ANSWER_ACCURACY_THRESHOLD=0.70
RAGAS_ANSWER_RELEVANCY_THRESHOLD=0.65
RAGAS_FAITHFULNESS_THRESHOLD=0.70
EOF

echo "==> Running RAGAS tests..."
~/.local/bin/pytest -m ragas --tb=short -q
