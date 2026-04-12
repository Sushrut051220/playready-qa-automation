from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import AzureOpenAI

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

load_dotenv(PROJECT_ROOT / ".env")

# ---- Authentication (supports both API key and Azure Identity) ----
api_key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
endpoint = (
    os.environ.get("AZURE_OPENAI_ENDPOINT", "")
    or os.environ.get("AZURE_OPENAI_BASE_URL", "")
).strip()
DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1-mini")
API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

if api_key:
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=API_VERSION,
    )
    print(f"Auth: API key | Endpoint: {endpoint}")
else:
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default",
    )
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        azure_ad_token_provider=token_provider,
        api_version=API_VERSION,
    )
    print(f"Auth: Azure Identity (az login) | Endpoint: {endpoint}")

print(f"Model: {DEPLOYMENT}")

# ---- 15 LLM-generated scenarios per PDF ----
LLM_SCENARIOS = [
    {
        "id": "pos_factual",
        "category": "positive",
        "prompt": "Generate a direct factual question about the content. The question should test basic knowledge retrieval. Ask about a specific fact, rule, or requirement mentioned in the text.",
    },
    {
        "id": "pos_detail",
        "category": "positive",
        "prompt": "Generate a question asking for specific details like numbers, versions, dates, or exact requirements from the content.",
    },
    {
        "id": "edge_version",
        "category": "edge_case",
        "prompt": "Generate a question that asks whether the rules or requirements apply to all versions of PlayReady or only specific ones.",
    },
    {
        "id": "edge_negation",
        "category": "edge_case",
        "prompt": "Generate a question using negation. Ask what is NOT allowed, NOT permitted, or what should NOT be done.",
    },
    {
        "id": "edge_multipart",
        "category": "edge_case",
        "prompt": "Generate a multi-part question: what is the requirement, when does it apply, and what are the consequences of non-compliance?",
    },
    {
        "id": "halluc_nonexistent",
        "category": "hallucination",
        "prompt": "Generate a question that references a non-existent section number or a made-up requirement to test if the agent fabricates an answer. The question should sound plausible but ask about something NOT in the text.",
    },
    {
        "id": "robust_paraphrase",
        "category": "robustness",
        "prompt": "Generate the same core question as a factual one but phrased very casually, as if a non-technical person is asking a colleague.",
    },
    {
        "id": "comp_rule",
        "category": "compliance",
        "prompt": "Generate a question specifically about mandatory compliance requirements, obligations, or rules from the content. Focus on what MUST be done.",
    },
    {
        "id": "ground_cite",
        "category": "grounding",
        "prompt": "Generate a question that asks the agent to cite which specific document, section, or rule defines a particular requirement.",
    },
    {
        "id": "sec_pii_exposure",
        "category": "data_security",
        "prompt": "Generate a question about how personally identifiable information (PII) or user data should be handled based on this content.",
    },
    {
        "id": "sec_data_retention",
        "category": "data_security",
        "prompt": "Generate a question about data retention, storage duration, or deletion requirements based on this content.",
    },
    {
        "id": "sec_encryption_keys",
        "category": "data_security",
        "prompt": "Generate a question about encryption key management, key storage, key rotation, or key disposal based on this content.",
    },
    {
        "id": "sec_access_control",
        "category": "data_security",
        "prompt": "Generate a question about access control, authorization, or who should and should not have access based on this content.",
    },
    {
        "id": "sec_audit_logging",
        "category": "data_security",
        "prompt": "Generate a question about audit logging, monitoring, tracking, or compliance evidence requirements based on this content.",
    },
    {
        "id": "conv_casual",
        "category": "conversational",
        "prompt": "Generate a very casual, friendly question about the content. Write it as if a new employee is chatting with a colleague over coffee.",
    },
]

# ---- 5 Fixed template scenarios per PDF (no LLM needed) ----
FIXED_SCENARIOS = [
    {
        "id": "neg_out_of_scope",
        "category": "negative",
        "template": "What does {pdf_topic} say about Netflix DRM implementation?",
        "expect_fallback": True,
        "strict_grounding": False,
    },
    {
        "id": "neg_wrong_doc",
        "category": "negative",
        "template": "According to {pdf_topic}, how do I set up a Widevine license server?",
        "expect_fallback": True,
        "strict_grounding": False,
    },
    {
        "id": "halluc_false_premise",
        "category": "hallucination",
        "template": "Since {pdf_topic} requires AES-256-GCM encryption for all content, how should implementers configure this?",
        "expect_fallback": False,
        "strict_grounding": True,
    },
    {
        "id": "cross_doc",
        "category": "cross_document",
        "template": "How does the content in {pdf_topic} relate to the overall PlayReady compliance framework?",
        "expect_fallback": False,
        "strict_grounding": False,
    },
    {
        "id": "conv_frustrated",
        "category": "conversational",
        "template": "I have been reading {pdf_topic} for hours and I still do not get it. Can you just explain the main point simply?",
        "expect_fallback": False,
        "strict_grounding": True,
    },
]


def generate_qa_from_chunk(chunk_text, pdf_name, scenario, retries=2):
    """Use Azure OpenAI to generate a natural question + ground truth answer."""
    system_prompt = (
        "You are a QA test case generator for a PlayReady DRM chatbot. "
        "Given a chunk of text from a PlayReady document, generate:\n"
        "1. A natural question that a real user would ask\n"
        "2. The correct ground truth answer based ONLY on the provided text\n\n"
        "Rules:\n"
        "- Question must sound natural, not templated\n"
        "- Question must be self-contained (no references to 'this document')\n"
        "- Answer must be concise (2-4 sentences max)\n"
        "- Answer must use ONLY information from the provided text\n"
        "- Do NOT invent or assume any information not in the text\n\n"
        "Respond ONLY with this exact JSON (no markdown, no extra text):\n"
        '{"question": "...", "answer": "..."}'
    )

    user_prompt = (
        f"Document: {pdf_name}\n\n"
        f"Content:\n{chunk_text[:2000]}\n\n"
        f"Task: {scenario['prompt']}\n\n"
        f"Generate JSON with question and answer."
    )

    for attempt in range(retries + 1):
        try:
            response = client.chat.completions.create(
                model=DEPLOYMENT,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=500,
            )
            text = response.choices[0].message.content.strip()

            # Clean markdown wrapper if present
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
                if text.startswith("json"):
                    text = text[4:].strip()

            result = json.loads(text)
            q = result.get("question", "").strip()
            a = result.get("answer", "").strip()
            if q and a:
                return q, a

        except json.JSONDecodeError:
            if attempt < retries:
                time.sleep(1)
                continue
            print(f"    [WARN] JSON parse failed after {retries + 1} attempts")

        except Exception as e:
            if attempt < retries:
                time.sleep(2)
                continue
            print(f"    [ERROR] LLM call failed: {e}")

    return "", ""


def generate_smart_testcases():
    """Generate intelligent test cases using LLM for each PDF chunk."""
    # Load chunk registry
    chunk_path = DATA_DIR / "chunk_registry.json"
    if not chunk_path.exists():
        print("ERROR: chunk_registry.json not found!")
        print("Run first: python scripts/generate_ragas_testset.py")
        return

    chunks = json.loads(chunk_path.read_text(encoding="utf-8-sig"))
    print(f"\nLoaded {len(chunks)} chunks from chunk_registry.json")

    # Load PDF registry
    reg_path = DATA_DIR / "pdf_registry.json"
    registry = json.loads(reg_path.read_text(encoding="utf-8-sig"))
    active_pdfs = [r for r in registry if r.get("active", True)]
    print(f"Active PDFs: {len(active_pdfs)}")
    print(f"Scenarios per PDF: {len(LLM_SCENARIOS)} LLM + {len(FIXED_SCENARIOS)} fixed = {len(LLM_SCENARIOS) + len(FIXED_SCENARIOS)}")
    print(f"Expected total: {len(active_pdfs) * (len(LLM_SCENARIOS) + len(FIXED_SCENARIOS))} per-PDF cases")
    print()

    # Group chunks by PDF
    pdf_chunks = {}
    for cid, cdata in chunks.items():
        pdf = cdata["source_pdf"]
        pdf_chunks.setdefault(pdf, []).append(cdata)

    run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    all_cases = []
    total_llm_ok = 0
    total_llm_fail = 0

    for pdf_idx, entry in enumerate(active_pdfs, 1):
        pdf_name = entry["filename"]
        doc_id = entry.get("doc_id", f"PR-DOC-{pdf_idx:03d}")
        doc_version = entry.get("doc_version", "1.0")
        kb_version = entry.get("kb_version", "2026.04")
        pdf_topic = Path(pdf_name).stem.replace("_", " ").replace("-", " ")
        my_chunks = pdf_chunks.get(pdf_name, [])

        if not my_chunks:
            print(f"  [{pdf_idx}/{len(active_pdfs)}] SKIP {pdf_name} (no chunks)")
            continue

        print(f"  [{pdf_idx}/{len(active_pdfs)}] {pdf_name} ({len(my_chunks)} chunks)")

        # ---- LLM-generated scenarios (15 per PDF) ----
        for sc_idx, scenario in enumerate(LLM_SCENARIOS):
            chunk = my_chunks[sc_idx % len(my_chunks)]
            chunk_id = chunk["chunk_id"]

            question, answer = generate_qa_from_chunk(
                chunk["chunk_text"], pdf_name, scenario
            )

            if question and answer:
                total_llm_ok += 1
                gen_method = "llm"
            else:
                # Fallback to template if LLM fails
                total_llm_fail += 1
                gen_method = "fallback"
                topic_line = chunk["chunk_text"].split("\n")[0][:80] if chunk["chunk_text"] else pdf_topic
                question = f"What does {pdf_topic} say about {topic_line}?"
                answer = chunk["chunk_text"][:500]

            all_cases.append({
                "id": f"pdf{pdf_idx:03d}_q{sc_idx + 1:02d}_{scenario['id']}",
                "prompt": question,
                "ground_truth": answer,
                "reference_contexts": [chunk["chunk_text"]],
                "expected_pdfs": [pdf_name],
                "expected_doc_id": doc_id,
                "expected_doc_version": doc_version,
                "expected_chunk_ids": [chunk_id],
                "expected_pages": chunk.get("pages", []),
                "kb_version": kb_version,
                "strict_grounding": scenario.get("strict_grounding", True),
                "expect_fallback": scenario.get("expect_fallback", False),
                "query_type": scenario["category"],
                "source_pdf": pdf_name,
                "source_category": entry.get("category", "general"),
                "generation_method": gen_method,
            })

            time.sleep(0.5)  # Rate limit protection

        # ---- Fixed template scenarios (5 per PDF) ----
        for sc_idx, scenario in enumerate(FIXED_SCENARIOS):
            prompt = scenario["template"].format(pdf_topic=pdf_topic)

            all_cases.append({
                "id": f"pdf{pdf_idx:03d}_q{len(LLM_SCENARIOS) + sc_idx + 1:02d}_{scenario['id']}",
                "prompt": prompt,
                "ground_truth": "",
                "reference_contexts": [],
                "expected_pdfs": [pdf_name],
                "expected_doc_id": doc_id,
                "expected_doc_version": doc_version,
                "expected_chunk_ids": [],
                "expected_pages": [],
                "kb_version": kb_version,
                "strict_grounding": scenario["strict_grounding"],
                "expect_fallback": scenario["expect_fallback"],
                "query_type": scenario["category"],
                "source_pdf": pdf_name,
                "source_category": entry.get("category", "general"),
                "generation_method": "template",
            })

        pdf_done = pdf_idx
        print(f"    Done ({len(LLM_SCENARIOS)} LLM + {len(FIXED_SCENARIOS)} fixed)")

    # ---- Backup old file ----
    old_path = DATA_DIR / "test_cases.json"
    if old_path.exists():
        backup = f"test_cases_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        (DATA_DIR / backup).write_text(
            old_path.read_text(encoding="utf-8-sig"), encoding="utf-8"
        )
        print(f"\n  Backed up old test_cases.json -> {backup}")

    # ---- Write files ----
    smart_master = DATA_DIR / "test_cases_smart_master.json"
    smart_master.write_text(
        json.dumps(all_cases, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    old_path.write_text(
        json.dumps(all_cases, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # ---- Write category splits ----
    cat_buckets = {}
    for case in all_cases:
        cat = case["query_type"]
        cat_buckets.setdefault(cat, []).append(case)

    for cat_name, cat_cases in sorted(cat_buckets.items()):
        cat_path = DATA_DIR / f"test_cases_{cat_name}.json"
        cat_path.write_text(
            json.dumps(cat_cases, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # ---- Summary ----
    print()
    print("=" * 60)
    print("SMART TEST CASE GENERATION COMPLETE")
    print("=" * 60)
    print(f"  Total per-PDF cases: {len(all_cases)}")
    print(f"  LLM-generated:       {total_llm_ok}")
    print(f"  LLM fallback:        {total_llm_fail}")
    print(f"  Template-based:      {len(active_pdfs) * len(FIXED_SCENARIOS)}")
    print(f"  PDFs processed:      {pdf_done}/{len(active_pdfs)}")
    print()
    print("  Categories:")
    for cat, cases in sorted(cat_buckets.items()):
        print(f"    {cat}: {len(cases)}")
    print()
    print(f"  Smart master: {smart_master}")
    print(f"  Pipeline file: {old_path}")
    print("=" * 60)
    print()
    print("NEXT STEPS:")
    print("  1. python scripts/generate_negative_testcases.py")
    print("  2. python scripts/generate_conversational_testcases.py")
    print("  3. python scripts/validate_test_coverage.py")

    return all_cases


if __name__ == "__main__":
    generate_smart_testcases()