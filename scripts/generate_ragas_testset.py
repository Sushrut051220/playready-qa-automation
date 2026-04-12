from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
KB_DIR = DATA_DIR / "kb"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

SCENARIO_TEMPLATES = [
    # ---- POSITIVE (1-2): Reduced from 5 ----
    {
        "id_suffix": "pos_factual",
        "category": "positive",
        "template": "What does {pdf_topic} say about {chunk_topic}?",
        "description": "Direct factual question — tests basic retrieval",
        "expect_fallback": False,
        "strict_grounding": True,
        "bug_it_catches": "Agent cannot answer basic questions from the document",
        "needs_chunk": True,
    },
    {
        "id_suffix": "pos_detail",
        "category": "positive",
        "template": "What are the specific requirements for {chunk_topic} as described in {pdf_topic}?",
        "description": "Specific detail extraction — tests precision",
        "expect_fallback": False,
        "strict_grounding": True,
        "bug_it_catches": "Agent misses specific numbers, dates, or version details",
        "needs_chunk": True,
    },
    # ---- EDGE CASES (3-5): Reduced from 5 ----
    {
        "id_suffix": "edge_version",
        "category": "edge_case",
        "template": "Does {chunk_topic} apply to all versions of PlayReady, or only specific ones as per {pdf_topic}?",
        "description": "Version constraint — tests version-awareness",
        "expect_fallback": False,
        "strict_grounding": True,
        "bug_it_catches": "Agent ignores version boundaries and gives generic answer",
        "needs_chunk": True,
    },
    {
        "id_suffix": "edge_negation",
        "category": "edge_case",
        "template": "What is NOT allowed regarding {chunk_topic} according to {pdf_topic}?",
        "description": "Negation question — tests negation understanding",
        "expect_fallback": False,
        "strict_grounding": True,
        "bug_it_catches": "Agent ignores negation and lists what IS allowed instead",
        "needs_chunk": True,
    },
    {
        "id_suffix": "edge_multipart",
        "category": "edge_case",
        "template": "According to {pdf_topic}, what is {chunk_topic}, when does it apply, and what are the penalties for non-compliance?",
        "description": "Multi-part question — tests completeness",
        "expect_fallback": False,
        "strict_grounding": True,
        "bug_it_catches": "Agent answers only part of the question",
        "needs_chunk": True,
    },
    # ---- NEGATIVE (6-7): Same ----
    {
        "id_suffix": "neg_out_of_scope",
        "category": "negative",
        "template": "What does {pdf_topic} say about Netflix DRM implementation?",
        "description": "Out-of-scope question — tests refusal behavior",
        "expect_fallback": True,
        "strict_grounding": False,
        "bug_it_catches": "Agent hallucinates an answer instead of refusing",
        "needs_chunk": False,
    },
    {
        "id_suffix": "neg_wrong_doc",
        "category": "negative",
        "template": "According to {pdf_topic}, how do I set up a Widevine license server?",
        "description": "Wrong document reference — tests scope boundary",
        "expect_fallback": True,
        "strict_grounding": False,
        "bug_it_catches": "Agent mixes content from unrelated technologies",
        "needs_chunk": False,
    },
    # ---- HALLUCINATION (8-9): Reduced from 3 ----
    {
        "id_suffix": "halluc_false_premise",
        "category": "hallucination",
        "template": "Since {pdf_topic} requires AES-256-GCM encryption for all content, how should implementers configure this?",
        "description": "False premise — tests if agent corrects false claims",
        "expect_fallback": False,
        "strict_grounding": True,
        "bug_it_catches": "Agent agrees with false premise instead of correcting it",
        "needs_chunk": False,
    },
    {
        "id_suffix": "halluc_nonexistent",
        "category": "hallucination",
        "template": "What is the maximum retry count for {chunk_topic} as specified in section 99.9 of {pdf_topic}?",
        "description": "Non-existent section — tests if agent invents data",
        "expect_fallback": False,
        "strict_grounding": True,
        "bug_it_catches": "Agent fabricates data from a non-existent section",
        "needs_chunk": True,
    },
    # ---- ROBUSTNESS (10): Same ----
    {
        "id_suffix": "robust_paraphrase",
        "category": "robustness",
        "template": "Can you explain the rules around {chunk_topic} from the {pdf_topic} document in simple terms?",
        "description": "Paraphrased question — tests consistency",
        "expect_fallback": False,
        "strict_grounding": True,
        "bug_it_catches": "Agent fails on rephrased questions that it answered correctly before",
        "needs_chunk": True,
    },
    # ---- COMPLIANCE (11): Reduced from 2 ----
    {
        "id_suffix": "comp_rule",
        "category": "compliance",
        "template": "What are the mandatory compliance requirements for {chunk_topic} as stated in {pdf_topic}?",
        "description": "Compliance rule verification — tests accuracy of rules",
        "expect_fallback": False,
        "strict_grounding": True,
        "bug_it_catches": "Agent states wrong compliance rules or misses mandatory ones",
        "needs_chunk": True,
    },
    # ---- GROUNDING (12): Same ----
    {
        "id_suffix": "ground_cite",
        "category": "grounding",
        "template": "Which specific document or section defines the requirements for {chunk_topic}? Please cite the source.",
        "description": "Citation verification — tests document grounding",
        "expect_fallback": False,
        "strict_grounding": True,
        "bug_it_catches": "Agent cites wrong document or no document at all",
        "needs_chunk": True,
    },
    # ---- CROSS-DOCUMENT (13): Same ----
    {
        "id_suffix": "cross_doc",
        "category": "cross_document",
        "template": "How does {chunk_topic} from {pdf_topic} relate to the overall PlayReady compliance framework?",
        "description": "Cross-document reasoning — tests multi-doc synthesis",
        "expect_fallback": False,
        "strict_grounding": False,
        "bug_it_catches": "Agent cannot connect information across multiple documents",
        "needs_chunk": True,
    },
    # ================================================================
    # NEW: DATA SECURITY / PII / COMPLIANCE (14-18)
    # Microsoft client strict requirements
    # ================================================================
    {
        "id_suffix": "sec_pii_exposure",
        "category": "data_security",
        "template": "Does {pdf_topic} mention how to handle personally identifiable information (PII) in the context of {chunk_topic}? What data protection measures are required?",
        "description": "PII handling — tests if agent exposes or discusses PII correctly",
        "expect_fallback": False,
        "strict_grounding": True,
        "bug_it_catches": "Agent provides incorrect PII handling guidance or exposes sensitive data patterns",
        "needs_chunk": True,
    },
    {
        "id_suffix": "sec_data_retention",
        "category": "data_security",
        "template": "What are the data retention and deletion policies related to {chunk_topic} as described in {pdf_topic}? How long should license data be stored?",
        "description": "Data retention — tests awareness of data lifecycle requirements",
        "expect_fallback": False,
        "strict_grounding": True,
        "bug_it_catches": "Agent gives incorrect data retention guidance or ignores deletion requirements",
        "needs_chunk": True,
    },
    {
        "id_suffix": "sec_encryption_keys",
        "category": "data_security",
        "template": "How should encryption keys related to {chunk_topic} be stored, rotated, and disposed of according to {pdf_topic}? What happens if a key is compromised?",
        "description": "Key management — tests security-critical key handling knowledge",
        "expect_fallback": False,
        "strict_grounding": True,
        "bug_it_catches": "Agent gives insecure key management advice or exposes key handling internals",
        "needs_chunk": True,
    },
    {
        "id_suffix": "sec_access_control",
        "category": "data_security",
        "template": "What access control and authorization requirements does {pdf_topic} specify for {chunk_topic}? Who should have access and who should not?",
        "description": "Access control — tests RBAC and authorization knowledge",
        "expect_fallback": False,
        "strict_grounding": True,
        "bug_it_catches": "Agent recommends overly permissive access or misses authorization requirements",
        "needs_chunk": True,
    },
    {
        "id_suffix": "sec_audit_logging",
        "category": "data_security",
        "template": "What audit logging and monitoring requirements does {pdf_topic} describe for {chunk_topic}? What events must be logged for compliance?",
        "description": "Audit trail — tests compliance logging awareness",
        "expect_fallback": False,
        "strict_grounding": True,
        "bug_it_catches": "Agent misses mandatory audit logging requirements or gives incomplete compliance guidance",
        "needs_chunk": True,
    },
    # ================================================================
    # NEW: CONVERSATIONAL / TONE (19-20)
    # Natural language, human-like interaction per PDF topic
    # ================================================================
    {
        "id_suffix": "conv_casual",
        "category": "conversational",
        "template": "Hey, I'm new to PlayReady and just started reading {pdf_topic}. Can you give me a quick summary of what {chunk_topic} is about in plain English?",
        "description": "Casual/friendly tone — tests if agent responds naturally to informal questions",
        "expect_fallback": False,
        "strict_grounding": True,
        "bug_it_catches": "Agent gives overly formal or robotic response to casual question, or fails to simplify",
        "needs_chunk": True,
    },
    {
        "id_suffix": "conv_frustrated",
        "category": "conversational",
        "template": "I've been reading {pdf_topic} for hours and I still don't understand {chunk_topic}. This is so confusing! Can you just explain it like I'm five?",
        "description": "Frustrated user tone — tests empathy and simplification ability",
        "expect_fallback": False,
        "strict_grounding": True,
        "bug_it_catches": "Agent ignores user frustration, gives same complex answer, or responds rudely",
        "needs_chunk": True,
    },
]


def _extract_text_from_pdf(pdf_path):
    try:
        import fitz
    except ImportError:
        print(f"  [WARN] PyMuPDF not installed. Run: pip install PyMuPDF")
        return ""

    text_parts = []
    try:
        doc = fitz.open(str(pdf_path))
        for page_num, page in enumerate(doc, 1):
            page_text = page.get_text("text")
            if page_text.strip():
                text_parts.append({"page": page_num, "text": page_text.strip()})
        doc.close()
    except Exception as e:
        print(f"  [ERROR] Could not read {pdf_path.name}: {e}")
        return ""

    return text_parts


def _create_chunks(page_texts, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
    full_text = ""
    page_map = []

    for pt in page_texts:
        start = len(full_text)
        full_text += pt["text"] + "\n\n"
        end = len(full_text)
        page_map.append({"start": start, "end": end, "page": pt["page"]})

    chunks = []
    pos = 0
    chunk_idx = 0
    while pos < len(full_text):
        end = min(pos + chunk_size, len(full_text))
        chunk_text = full_text[pos:end].strip()

        if len(chunk_text) < 50:
            break

        pages = set()
        for pm in page_map:
            if pm["start"] < end and pm["end"] > pos:
                pages.add(pm["page"])

        chunks.append({
            "chunk_index": chunk_idx,
            "chunk_text": chunk_text,
            "char_start": pos,
            "char_end": end,
            "pages": sorted(pages),
        })

        chunk_idx += 1
        pos += chunk_size - chunk_overlap

    return chunks


def _generate_chunk_id(doc_id, doc_version, chunk_index):
    return f"{doc_id}_v{doc_version}_chunk_{chunk_index:03d}"


def _generate_chunk_hash(chunk_text):
    return hashlib.md5(chunk_text.encode("utf-8")).hexdigest()[:12]


def _extract_topic_from_chunk(chunk_text):
    lines = [l.strip() for l in chunk_text.split("\n") if len(l.strip()) > 20]
    if not lines:
        return "the documented requirements"
    first_line = lines[0]
    if len(first_line) > 80:
        first_line = first_line[:77] + "..."
    return first_line


def _load_pdf_registry():
    registry_path = DATA_DIR / "pdf_registry.json"
    if registry_path.exists():
        registry = json.loads(registry_path.read_text(encoding="utf-8-sig"))
        active = [r for r in registry if r.get("active", True)]
        if active:
            return active

    pdf_files = sorted(KB_DIR.glob("*.pdf"))
    return [
        {
            "filename": p.name,
            "doc_id": f"PR-DOC-{i:03d}",
            "doc_version": "1.0",
            "kb_version": "2026.04",
            "category": "general",
            "active": True,
        }
        for i, p in enumerate(pdf_files, 1)
    ]


def generate_test_cases_for_pdf(pdf_entry, pdf_idx, chunk_registry):
    pdf_file = pdf_entry["filename"]
    pdf_path = KB_DIR / pdf_file
    doc_id = pdf_entry.get("doc_id", f"PR-DOC-{pdf_idx:03d}")
    doc_version = pdf_entry.get("doc_version", "1.0")
    kb_version = pdf_entry.get("kb_version", "2026.04")
    pdf_category = pdf_entry.get("category", "general")

    page_texts = _extract_text_from_pdf(pdf_path)
    if not page_texts:
        print(f"    [WARN] No text extracted from {pdf_file}")
        chunks = []
    else:
        chunks = _create_chunks(page_texts)
        print(f"    Extracted {len(chunks)} chunks from {pdf_file}")

    for chunk in chunks:
        chunk_id = _generate_chunk_id(doc_id, doc_version, chunk["chunk_index"])
        chunk_hash = _generate_chunk_hash(chunk["chunk_text"])
        chunk_registry[chunk_id] = {
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "doc_version": doc_version,
            "kb_version": kb_version,
            "source_pdf": pdf_file,
            "chunk_index": chunk["chunk_index"],
            "pages": chunk["pages"],
            "char_start": chunk["char_start"],
            "char_end": chunk["char_end"],
            "chunk_hash": chunk_hash,
            "chunk_text_preview": chunk["chunk_text"][:200],
            "chunk_text": chunk["chunk_text"],
        }

    pdf_topic = pdf_path.stem.replace("_", " ").replace("-", " ").strip()

    cases = []
    for scenario_idx, scenario in enumerate(SCENARIO_TEMPLATES):
        case_num = scenario_idx + 1
        case_id = f"pdf{pdf_idx:03d}_q{case_num:02d}_{scenario['id_suffix']}"

        if scenario["needs_chunk"] and chunks:
            chunk = chunks[scenario_idx % len(chunks)]
            chunk_id = _generate_chunk_id(doc_id, doc_version, chunk["chunk_index"])
            chunk_topic = _extract_topic_from_chunk(chunk["chunk_text"])
            ground_truth_source = chunk["chunk_text"][:500]
            reference_contexts = [chunk["chunk_text"]]
            expected_chunk_ids = [chunk_id]
            expected_pages = chunk["pages"]
        else:
            chunk_id = None
            chunk_topic = pdf_topic
            ground_truth_source = ""
            reference_contexts = []
            expected_chunk_ids = []
            expected_pages = []

        if chunks and len(chunks) > 1:
            alt_chunk = chunks[(scenario_idx + 5) % len(chunks)]
            secondary_topic = _extract_topic_from_chunk(alt_chunk["chunk_text"])
        else:
            secondary_topic = "related requirements"

        prompt = scenario["template"].format(
            pdf_topic=pdf_topic,
            chunk_topic=chunk_topic,
            secondary_topic=secondary_topic,
        )

        cases.append({
            "id": case_id,
            "prompt": prompt,
            "ground_truth": ground_truth_source,
            "reference_contexts": reference_contexts,
            "expected_pdfs": [pdf_file],
            "expected_doc_id": doc_id,
            "expected_doc_version": doc_version,
            "expected_chunk_ids": expected_chunk_ids,
            "expected_pages": expected_pages,
            "kb_version": kb_version,
            "strict_grounding": scenario["strict_grounding"],
            "expect_fallback": scenario["expect_fallback"],
            "query_type": scenario["category"],
            "scenario_description": scenario["description"],
            "bug_it_catches": scenario["bug_it_catches"],
            "source_pdf": pdf_file,
            "source_category": pdf_category,
        })

    return cases


def generate_all_test_cases():
    pdf_entries = _load_pdf_registry()
    print(f"Found {len(pdf_entries)} active PDFs in registry\n")

    all_cases = []
    category_buckets = {}
    chunk_registry = {}

    for idx, entry in enumerate(pdf_entries, 1):
        print(f"  [{idx}/{len(pdf_entries)}] Processing: {entry['filename']}")
        cases = generate_test_cases_for_pdf(entry, idx, chunk_registry)
        all_cases.extend(cases)

        for case in cases:
            cat = case["query_type"]
            category_buckets.setdefault(cat, []).append(case)

    old_path = DATA_DIR / "test_cases.json"
    if old_path.exists():
        backup_name = f"test_cases_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = DATA_DIR / backup_name
        backup_path.write_text(old_path.read_text(encoding="utf-8-sig"), encoding="utf-8")
        print(f"\n  Backed up old test_cases.json -> {backup_name}")

    chunk_registry_path = DATA_DIR / "chunk_registry.json"
    chunk_registry_path.write_text(
        json.dumps(chunk_registry, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n  Chunk registry: {chunk_registry_path} ({len(chunk_registry)} chunks)")

    master_path = DATA_DIR / "test_cases_master.json"
    master_path.write_text(json.dumps(all_cases, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Master file: {master_path} ({len(all_cases)} test cases)")

    for cat_name, cat_cases in sorted(category_buckets.items()):
        cat_path = DATA_DIR / f"test_cases_{cat_name}.json"
        cat_path.write_text(json.dumps(cat_cases, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  Category '{cat_name}': {cat_path} ({len(cat_cases)} cases)")

    default_path = DATA_DIR / "test_cases.json"
    default_path.write_text(json.dumps(all_cases, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Pipeline file: {default_path} ({len(all_cases)} cases)")

    summary = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_pdfs": len(pdf_entries),
        "total_test_cases": len(all_cases),
        "total_chunks": len(chunk_registry),
        "cases_per_pdf": len(SCENARIO_TEMPLATES),
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "categories": {cat: len(cases) for cat, cases in sorted(category_buckets.items())},
        "scenario_types": [s["id_suffix"] for s in SCENARIO_TEMPLATES],
        "pdfs_processed": [
            {"filename": e["filename"], "doc_id": e.get("doc_id"), "doc_version": e.get("doc_version")}
            for e in pdf_entries
        ],
    }
    summary_path = DATA_DIR / "testcase_generation_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Summary: {summary_path}")

    print(f"\n✅ Done! {len(all_cases)} test cases from {len(pdf_entries)} PDFs ({len(chunk_registry)} chunks)")
    return all_cases


if __name__ == "__main__":
    generate_all_test_cases()