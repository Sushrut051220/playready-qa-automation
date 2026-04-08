from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_CONFIG_PATH = PROJECT_ROOT / "data" / "ragas_testset_config.json"
DEFAULT_FALLBACK_PATTERNS = [
    "I don't know",
    "not in my knowledge base",
    "outside my scope",
    "cannot answer",
]
DEFAULT_FORBIDDEN_PATTERNS = [
    "I don't know",
    "cannot help",
    "no information",
]
PDF_ID_PATTERN = re.compile(r"\[PDF_ID:\s*([^\]|]+)", re.IGNORECASE)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def load_config(config_path: Path) -> dict[str, Any]:
    config = _load_json(config_path)
    base_dir = config_path.parent

    def _resolve(value: str, default: str) -> Path:
        raw = value or default
        candidate = Path(raw)
        return candidate if candidate.is_absolute() else (PROJECT_ROOT / candidate).resolve()

    config["pdf_registry_path"] = _resolve(config.get("pdf_registry_path", "data/pdf_registry.json"), "data/pdf_registry.json")
    config["output_path"] = _resolve(config.get("output_path", "data/test_cases.json"), "data/test_cases.json")
    config["archive_dir"] = _resolve(config.get("archive_dir", "artifacts/testsets"), "artifacts/testsets")
    config.setdefault("testset_size", 20)
    config.setdefault(
        "query_type_mix",
        {
            "single_hop_specific": 0.5,
            "multi_hop_specific": 0.3,
            "multi_hop_abstract": 0.2,
        },
    )
    config.setdefault("strict_grounding", True)
    config.setdefault("fallback_patterns", list(DEFAULT_FALLBACK_PATTERNS))
    config.setdefault("forbidden_patterns", list(DEFAULT_FORBIDDEN_PATTERNS))
    config.setdefault(
        "llm_context",
        "Generate realistic enterprise support questions grounded only in the provided PDF context. Do not mention source tags such as PDF_ID or PDF_NAME in the question or reference answer.",
    )
    config.setdefault("max_pages_per_pdf", 25)
    config.setdefault("max_chars_per_page", 4000)
    config.setdefault("seed_from_registry_sample_questions", True)
    return config


def load_pdf_registry(registry_path: Path) -> list[dict[str, Any]]:
    registry = _load_json(registry_path)
    if not isinstance(registry, list):
        raise ValueError(f"Expected a list in {registry_path}")
    return registry


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return cleaned or "item"


def _sanitize_text(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\[PDF_ID:[^\]]+\]\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[PDF_NAME:[^\]]+\]\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[TOPIC:[^\]]+\]\s*", "", text, flags=re.IGNORECASE)
    return text.strip()


def build_seed_test_cases(
    registry: list[dict[str, Any]],
    desired_count: int,
    fallback_patterns: list[str] | None = None,
    forbidden_patterns: list[str] | None = None,
    strict_grounding: bool = True,
) -> list[dict[str, Any]]:
    fallback_patterns = list(fallback_patterns or DEFAULT_FALLBACK_PATTERNS)
    forbidden_patterns = list(forbidden_patterns or DEFAULT_FORBIDDEN_PATTERNS)

    seeded_cases: list[dict[str, Any]] = []
    for entry in registry:
        pdf_id = entry.get("pdf_id") or _slugify(entry.get("pdf_name", "pdf"))
        pdf_name = entry.get("pdf_name") or pdf_id
        topic = entry.get("topic") or pdf_name
        keywords = list(entry.get("expected_keywords") or [])
        sample_questions = list(entry.get("sample_questions") or [])
        for index, question in enumerate(sample_questions, start=1):
            seeded_cases.append(
                {
                    "id": f"seed_{_slugify(pdf_id)}_{index:03d}",
                    "prompt": question,
                    "required_keywords": keywords[:5],
                    "forbidden_patterns": forbidden_patterns,
                    "expect_fallback": False,
                    "fallback_patterns": fallback_patterns,
                    "ground_truth": f"Answer should be grounded in '{pdf_name}' and stay focused on the topic '{topic}'.",
                    "expected_pdfs": [pdf_id],
                    "strict_grounding": strict_grounding,
                    "paraphrase_group": _slugify(topic),
                    "query_type": "seeded_from_registry",
                    "notes": f"Seeded from pdf_registry.json for {pdf_name}.",
                }
            )

    if not seeded_cases:
        return []

    expanded: list[dict[str, Any]] = []
    cursor = 0
    while len(expanded) < desired_count:
        template = dict(seeded_cases[cursor % len(seeded_cases)])
        run_index = len(expanded) + 1
        template["id"] = f"{template['id']}_r{run_index:03d}"
        expanded.append(template)
        cursor += 1

    return expanded[:desired_count]


def _extract_text_from_pdf(pdf_path: Path, max_pages_per_pdf: int, max_chars_per_page: int) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    parts: list[str] = []
    for page_index, page in enumerate(reader.pages[:max_pages_per_pdf], start=1):
        page_text = (page.extract_text() or "").strip()
        if not page_text:
            continue
        parts.append(f"[PAGE {page_index}] {page_text[:max_chars_per_page]}")
    return "\n\n".join(parts).strip()


def build_langchain_documents(
    registry: list[dict[str, Any]],
    max_pages_per_pdf: int,
    max_chars_per_page: int,
) -> tuple[list[Any], list[str]]:
    from langchain_core.documents import Document

    documents: list[Any] = []
    warnings: list[str] = []

    for entry in registry:
        pdf_id = entry.get("pdf_id") or _slugify(entry.get("pdf_name", "pdf"))
        pdf_name = entry.get("pdf_name") or pdf_id
        topic = entry.get("topic") or "general"
        file_path = Path(entry.get("file_path") or "")
        if file_path and not file_path.is_absolute():
            file_path = (PROJECT_ROOT / file_path).resolve()

        if not file_path or not file_path.exists():
            warnings.append(f"Missing PDF file for {pdf_id}: {file_path}")
            continue

        try:
            text = _extract_text_from_pdf(file_path, max_pages_per_pdf=max_pages_per_pdf, max_chars_per_page=max_chars_per_page)
        except Exception as exc:
            warnings.append(f"Failed to read {pdf_name}: {exc}")
            continue

        if not text:
            warnings.append(f"No extractable text found in {pdf_name}.")
            continue

        tagged_text = f"[PDF_ID: {pdf_id}] [PDF_NAME: {pdf_name}] [TOPIC: {topic}]\n{text}"
        documents.append(
            Document(
                page_content=tagged_text,
                metadata={
                    "pdf_id": pdf_id,
                    "pdf_name": pdf_name,
                    "topic": topic,
                    "source": str(file_path),
                },
            )
        )

    return documents, warnings


def _normalize_query_type_mix(query_type_mix: dict[str, Any]) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for name, weight in (query_type_mix or {}).items():
        try:
            numeric = float(weight)
        except (TypeError, ValueError):
            continue
        if numeric > 0:
            normalized[str(name).strip().lower()] = numeric
    total = sum(normalized.values())
    if total <= 0:
        return {}
    return {name: value / total for name, value in normalized.items()}


def _canonical_synth_name(name: str) -> str:
    cleaned = str(name or "").strip().lower()
    for prefix in (
        "single_hop_specific",
        "multi_hop_specific",
        "multi_hop_abstract",
    ):
        if cleaned.startswith(prefix):
            return prefix
    return cleaned or "ragas_generated"


def _build_query_distribution(ragas_llm: Any, query_type_mix: dict[str, Any], llm_context: str):
    from ragas.testset.synthesizers import default_query_distribution

    normalized_mix = _normalize_query_type_mix(query_type_mix)
    distribution = default_query_distribution(ragas_llm, llm_context=llm_context)
    if not normalized_mix:
        return distribution

    selected: list[tuple[Any, float]] = []
    for synthesizer, default_weight in distribution:
        canonical = _canonical_synth_name(getattr(synthesizer, "name", ""))
        weight = normalized_mix.get(canonical)
        if weight is not None and weight > 0:
            selected.append((synthesizer, weight))

    return selected or distribution


def _extract_expected_pdfs(contexts: list[str]) -> list[str]:
    found: list[str] = []
    for context in contexts:
        for match in PDF_ID_PATTERN.findall(str(context or "")):
            pdf_id = match.strip()
            if pdf_id and pdf_id not in found:
                found.append(pdf_id)
    return found


def _keywords_for_pdfs(expected_pdfs: list[str], registry_by_id: dict[str, dict[str, Any]]) -> list[str]:
    keywords: list[str] = []
    for pdf_id in expected_pdfs:
        for keyword in registry_by_id.get(pdf_id, {}).get("expected_keywords", []) or []:
            if keyword not in keywords:
                keywords.append(keyword)
    return keywords[:6]


def convert_ragas_samples_to_test_cases(
    samples: list[dict[str, Any]],
    registry_by_id: dict[str, dict[str, Any]],
    fallback_patterns: list[str],
    forbidden_patterns: list[str],
    strict_grounding: bool,
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    for index, sample in enumerate(samples, start=1):
        prompt = _sanitize_text(sample.get("user_input") or sample.get("query") or "")
        if not prompt:
            continue

        contexts = sample.get("reference_contexts") or sample.get("retrieved_contexts") or []
        if isinstance(contexts, str):
            contexts = [contexts]
        contexts = [_sanitize_text(item) for item in contexts if str(item or "").strip()]

        expected_pdfs = _extract_expected_pdfs(sample.get("reference_contexts") or sample.get("retrieved_contexts") or [])
        reference = _sanitize_text(sample.get("reference") or sample.get("response") or "")
        synth_name = sample.get("synthesizer_name") or "ragas_generated"
        query_type = _canonical_synth_name(synth_name)

        cases.append(
            {
                "id": f"generated_{query_type}_{index:03d}",
                "prompt": prompt,
                "required_keywords": _keywords_for_pdfs(expected_pdfs, registry_by_id),
                "forbidden_patterns": list(forbidden_patterns),
                "expect_fallback": False,
                "fallback_patterns": list(fallback_patterns),
                "ground_truth": reference or "Reference answer generated by RAGAS.",
                "expected_pdfs": expected_pdfs,
                "strict_grounding": strict_grounding,
                "paraphrase_group": query_type,
                "query_type": query_type,
                "reference_contexts": contexts,
                "notes": f"Generated by RAGAS using {synth_name}.",
            }
        )

    return cases


def merge_cases(primary_cases: list[dict[str, Any]], fallback_cases: list[dict[str, Any]], desired_count: int) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen_prompts: set[str] = set()

    for item in primary_cases + fallback_cases:
        prompt_key = str(item.get("prompt", "")).strip().lower()
        if not prompt_key or prompt_key in seen_prompts:
            continue
        merged.append(item)
        seen_prompts.add(prompt_key)
        if len(merged) >= desired_count:
            break

    return merged


def write_output_file(payload: list[dict[str, Any]], output_path: Path, archive_dir: Path) -> None:
    archive_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    if output_path.exists():
        backup_path = archive_dir / f"test_cases_previous_{timestamp}.json"
        shutil.copy2(output_path, backup_path)

    _write_json(output_path, payload)
    archive_copy = archive_dir / f"test_cases_generated_{timestamp}.json"
    shutil.copy2(output_path, archive_copy)


def generate_with_ragas(documents: list[Any], config: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    from llm_provider import build_ragas_dependencies
    from ragas.testset import TestsetGenerator

    ragas_llm, ragas_embeddings, issue, provider_meta = build_ragas_dependencies()
    if ragas_llm is None or ragas_embeddings is None:
        return [], issue or "RAGAS dependencies are not available."

    generator = TestsetGenerator(
        llm=ragas_llm,
        embedding_model=ragas_embeddings,
        llm_context=config.get("llm_context"),
    )
    query_distribution = _build_query_distribution(
        ragas_llm=ragas_llm,
        query_type_mix=config.get("query_type_mix", {}),
        llm_context=config.get("llm_context", ""),
    )

    try:
        testset = generator.generate_with_langchain_docs(
            documents=documents,
            testset_size=int(config.get("testset_size", 20)),
            query_distribution=query_distribution,
            with_debugging_logs=bool(config.get("with_debugging_logs", False)),
            raise_exceptions=False,
        )
        to_list = getattr(testset, "to_list", None)
        if callable(to_list):
            generated_rows = cast(list[dict[str, Any]], to_list())
            return list(generated_rows), None
        return [], "RAGAS returned an executor instead of a materialized testset."
    except Exception as exc:
        return [], f"RAGAS generation failed: {exc}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate RAGAS-based chatbot test cases from the PDF registry.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="Path to the JSON config file.")
    parser.add_argument("--testset-size", type=int, default=None, help="Override the configured number of generated questions.")
    parser.add_argument("--output", type=Path, default=None, help="Override the configured output path.")
    parser.add_argument("--seed-only", action="store_true", help="Skip RAGAS generation and only seed cases from pdf_registry sample_questions.")
    parser.add_argument("--dry-run", action="store_true", help="Print a summary without writing to disk.")
    return parser.parse_args()


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    args = parse_args()
    config = load_config(args.config)

    if args.testset_size is not None:
        config["testset_size"] = args.testset_size
    if args.output is not None:
        config["output_path"] = args.output if args.output.is_absolute() else (PROJECT_ROOT / args.output).resolve()

    registry = load_pdf_registry(config["pdf_registry_path"])
    registry_by_id = {item.get("pdf_id") or _slugify(item.get("pdf_name", "pdf")): item for item in registry}

    seed_cases = build_seed_test_cases(
        registry=registry,
        desired_count=int(config["testset_size"]),
        fallback_patterns=list(config.get("fallback_patterns", DEFAULT_FALLBACK_PATTERNS)),
        forbidden_patterns=list(config.get("forbidden_patterns", DEFAULT_FORBIDDEN_PATTERNS)),
        strict_grounding=bool(config.get("strict_grounding", True)),
    )

    ragas_cases: list[dict[str, Any]] = []
    issue: str | None = None
    warnings: list[str] = []

    if not args.seed_only:
        documents, warnings = build_langchain_documents(
            registry=registry,
            max_pages_per_pdf=int(config.get("max_pages_per_pdf", 25)),
            max_chars_per_page=int(config.get("max_chars_per_page", 4000)),
        )
        if documents:
            samples, issue = generate_with_ragas(documents, config)
            ragas_cases = convert_ragas_samples_to_test_cases(
                samples=samples,
                registry_by_id=registry_by_id,
                fallback_patterns=list(config.get("fallback_patterns", DEFAULT_FALLBACK_PATTERNS)),
                forbidden_patterns=list(config.get("forbidden_patterns", DEFAULT_FORBIDDEN_PATTERNS)),
                strict_grounding=bool(config.get("strict_grounding", True)),
            )
        else:
            issue = "No readable PDF documents were found; falling back to sample_questions from the registry."

    merged_cases = merge_cases(ragas_cases, seed_cases, int(config["testset_size"]))

    summary = {
        "config": str(args.config),
        "output_path": str(config["output_path"]),
        "requested_questions": int(config["testset_size"]),
        "generated_with_ragas": len(ragas_cases),
        "seeded_from_registry": len(seed_cases),
        "final_export_count": len(merged_cases),
        "warnings": warnings,
        "issue": issue,
    }

    print(json.dumps(summary, indent=2))

    if not merged_cases:
        print("No test cases were produced. Add sample_questions or valid PDF file paths to data/pdf_registry.json.")
        return 1

    if args.dry_run:
        return 0

    write_output_file(
        payload=merged_cases,
        output_path=Path(config["output_path"]),
        archive_dir=Path(config["archive_dir"]),
    )
    print(f"Saved {len(merged_cases)} generated test cases to {config['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
