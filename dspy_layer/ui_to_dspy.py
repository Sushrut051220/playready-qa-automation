from __future__ import annotations

import json
import os
import re
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from statistics import mean
from typing import Any

import dspy

from llm_provider import get_llm_provider, get_model_label


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF_REGISTRY_PATH = PROJECT_ROOT / "data" / "pdf_registry.json"

DEFAULT_FALLBACK_PATTERNS = [
    "i don't know",
    "outside my scope",
    "not in my knowledge base",
    "cannot answer",
    "please contact support",
    "not available",
]

# Generic tokens appear in many answers and should not alone determine source grounding.
GENERIC_GROUNDING_TOKENS = {
    "playready",
    "license",
    "licenses",
    "rules",
    "rule",
    "compliance",
    "documentation",
    "document",
    "pdf",
    "api",
    "client",
    "server",
    "microsoft",
}


class NormalizeChatbotOutput(dspy.Signature):
    """Simple deterministic adapter that normalizes UI-captured chatbot answers."""

    question: str = dspy.InputField()
    answer: str = dspy.InputField()
    contexts: list[str] = dspy.InputField(desc="Optional citations or retrieved chunks.")

    normalized_answer: str = dspy.OutputField()
    detected_fallback: bool = dspy.OutputField()
    context_count: int = dspy.OutputField()
    matched_pdfs: list[str] = dspy.OutputField()


def _normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()


def load_pdf_registry(pdf_registry_path: str | Path | None = None) -> list[dict[str, Any]]:
    path = Path(pdf_registry_path or os.getenv("PDF_REGISTRY_PATH", DEFAULT_PDF_REGISTRY_PATH))
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def match_pdfs_from_texts(texts: list[str], pdf_registry: list[dict[str, Any]]) -> list[str]:
    combined_text = " || ".join(_normalize_text(text) for text in texts if str(text).strip())
    if not combined_text:
        return []

    matches: list[str] = []
    for record in pdf_registry:
        strong_tokens = [
            record.get("pdf_id", ""),
            record.get("pdf_name", ""),
            record.get("topic", ""),
        ]
        expected_keywords = [_normalize_text(keyword) for keyword in (record.get("expected_keywords", []) or [])]

        # Strong evidence: explicit id/name/topic mentions in response or captured contexts.
        has_strong_match = any(_normalize_text(token) and _normalize_text(token) in combined_text for token in strong_tokens)

        # Keyword evidence: require at least two non-generic keyword hits to avoid false positives.
        keyword_hits = {
            keyword
            for keyword in expected_keywords
            if keyword and keyword not in GENERIC_GROUNDING_TOKENS and keyword in combined_text
        }

        if has_strong_match or len(keyword_hits) >= 2:
            matches.append(str(record.get("pdf_id", "")))

    return list(dict.fromkeys(match for match in matches if match))


class UIArtifactAdapter(dspy.Module):
    """DSPy adapter program that standardizes the raw UI artifact payload."""

    def __init__(self, pdf_registry: list[dict[str, Any]] | None = None) -> None:
        super().__init__()
        self.pdf_registry = pdf_registry or load_pdf_registry()

    def forward(self, question: str, answer: str, contexts: list[str] | None = None):
        normalized_answer = re.sub(r"\s+", " ", answer or "").strip()
        normalized_contexts = [re.sub(r"\s+", " ", ctx).strip() for ctx in (contexts or []) if str(ctx).strip()]
        answer_lower = normalized_answer.lower()
        detected_fallback = any(pattern in answer_lower for pattern in DEFAULT_FALLBACK_PATTERNS)
        matched_pdfs = match_pdfs_from_texts(normalized_contexts + [normalized_answer], self.pdf_registry)

        return dspy.Prediction(
            normalized_answer=normalized_answer,
            normalized_contexts=normalized_contexts,
            detected_fallback=detected_fallback,
            context_count=len(normalized_contexts),
            matched_pdfs=matched_pdfs,
        )


def _load_artifact_files(artifacts_path: str | Path) -> list[Path]:
    root = Path(artifacts_path)
    if root.is_file():
        return [root]
    if not root.exists():
        return []
    return sorted(path for path in root.glob("*.json") if path.is_file())


def convert_ui_artifacts_to_dspy_examples(artifacts_path: str | Path) -> list[dspy.Example]:
    """Convert saved UI artifacts into DSPy examples."""
    examples: list[dspy.Example] = []

    for artifact_file in _load_artifact_files(artifacts_path):
        payload = json.loads(artifact_file.read_text(encoding="utf-8"))
        ground_truth_value = payload.get("ground_truth")
        ground_truths = []
        if isinstance(ground_truth_value, list):
            ground_truths = ground_truth_value
        elif ground_truth_value:
            ground_truths = [str(ground_truth_value)]

        evaluation_question = payload.get("base_prompt") or payload.get("prompt", "")

        example = dspy.Example(
            id=payload.get("id", artifact_file.stem),
            question=evaluation_question,
            answer=payload.get("answer", ""),
            contexts=payload.get("contexts") or payload.get("citations") or [],
            required_keywords=payload.get("required_keywords", []),
            forbidden_patterns=payload.get("forbidden_patterns", []),
            expect_fallback=payload.get("expect_fallback", False),
            fallback_patterns=payload.get("fallback_patterns", []),
            ground_truths=ground_truths,
            expected_pdfs=payload.get("expected_pdfs", []),
            strict_grounding=payload.get("strict_grounding", False),
            paraphrase_group=payload.get("paraphrase_group"),
            notes=payload.get("notes", ""),
        ).with_inputs("question", "answer", "contexts")
        examples.append(example)

    return examples


def keyword_presence_metric(example: dspy.Example, prediction: dspy.Prediction) -> dict[str, Any]:
    required_keywords = [str(item).lower() for item in (getattr(example, "required_keywords", []) or [])]
    if not required_keywords:
        return {"score": 1.0, "issues": []}

    answer_lower = prediction.normalized_answer.lower()
    matched = [keyword for keyword in required_keywords if keyword in answer_lower]
    missing = [keyword for keyword in required_keywords if keyword not in answer_lower]

    score = len(matched) / len(required_keywords)
    issues = [f"Missing required keyword: {keyword}" for keyword in missing]
    return {"score": round(score, 4), "issues": issues}


def fallback_detection_metric(example: dspy.Example, prediction: dspy.Prediction) -> dict[str, Any]:
    expected = bool(getattr(example, "expect_fallback", False))
    patterns = [str(item).lower() for item in (getattr(example, "fallback_patterns", []) or [])]
    answer_lower = prediction.normalized_answer.lower()

    detected_by_patterns = any(pattern in answer_lower for pattern in patterns)
    actual = bool(prediction.detected_fallback or detected_by_patterns)

    score = 1.0 if actual == expected else 0.0
    if score == 1.0:
        return {"score": score, "issues": []}

    return {
        "score": score,
        "issues": [f"Fallback expectation mismatch: expected={expected}, actual={actual}"],
    }


def formatting_constraints_metric(example: dspy.Example, prediction: dspy.Prediction) -> dict[str, Any]:
    issues: list[str] = []
    forbidden_patterns = [str(item).lower() for item in (getattr(example, "forbidden_patterns", []) or [])]
    answer_text = prediction.normalized_answer
    answer_lower = answer_text.lower()

    if not answer_text.strip():
        issues.append("Answer is empty.")

    for pattern in forbidden_patterns:
        if pattern and pattern in answer_lower:
            issues.append(f"Forbidden pattern found: {pattern}")

    if len(answer_text) < 3:
        issues.append("Answer is too short to be meaningful.")

    score = 1.0 if not issues else 0.0
    return {"score": score, "issues": issues}


def pdf_grounding_metric(example: dspy.Example, prediction: dspy.Prediction) -> dict[str, Any]:
    expected_pdfs = set(getattr(example, "expected_pdfs", []) or [])
    strict_grounding = bool(getattr(example, "strict_grounding", False))
    matched_pdfs = set(getattr(prediction, "matched_pdfs", []) or [])

    if not strict_grounding or not expected_pdfs:
        return {"score": 1.0, "issues": []}

    if expected_pdfs.intersection(matched_pdfs):
        return {"score": 1.0, "issues": []}

    if matched_pdfs:
        return {
            "score": 0.0,
            "issues": [
                f"Expected grounding in {sorted(expected_pdfs)}, but evidence matched {sorted(matched_pdfs)}."
            ],
        }

    return {
        "score": 0.5,
        "issues": [
            "Strict grounding requested but the UI/network did not expose enough PDF evidence to verify the source."
        ],
    }


def llm_answer_quality_metric(example: dspy.Example, prediction: dspy.Prediction) -> dict[str, Any]:
    """Use LLM to evaluate answer quality and relevance to the question."""
    question = getattr(example, "question", "")
    answer = prediction.normalized_answer

    if not question or not answer:
        return {"score": 0.0, "issues": ["Question or answer is empty."]}

    try:
        import dspy
        llm_provider = get_llm_provider()
        if not llm_provider or llm_provider == "offline":
            return {"score": 0.5, "issues": ["LLM provider not configured; quality assessment skipped."]}

        class QualityRating(dspy.Signature):
            question: str = dspy.InputField()
            answer: str = dspy.InputField()
            quality_score: int = dspy.OutputField(desc="Rate the answer quality and relevance on a scale 0-5.")
            reasoning: str = dspy.OutputField(desc="Brief explanation of the score.")

        rater = dspy.ChainOfThought(QualityRating)
        try:
            result = rater(question=question, answer=answer)
            score_raw = int(str(result.quality_score).strip().split()[0])
            score = max(0.0, min(1.0, score_raw / 5.0))
            return {"score": round(score, 4), "issues": []}
        except Exception as inner_exc:
            return {"score": 0.5, "issues": [f"LLM scoring failed: {str(inner_exc)[:100]}"]}
    except Exception as exc:
        return {"score": 0.5, "issues": [f"LLM quality metric error: {str(exc)[:100]}"]}


def build_metric_breakdown(example: dspy.Example, prediction: dspy.Prediction) -> dict[str, dict[str, Any]]:
    metrics = {
        "keyword_presence": keyword_presence_metric(example, prediction),
        "fallback_detection": fallback_detection_metric(example, prediction),
        "formatting_constraints": formatting_constraints_metric(example, prediction),
        "pdf_grounding": pdf_grounding_metric(example, prediction),
        "llm_answer_quality": llm_answer_quality_metric(example, prediction),
    }
    return metrics


def composite_deterministic_metric(example: dspy.Example, prediction: dspy.Prediction, trace=None) -> float:
    del trace
    breakdown = build_metric_breakdown(example, prediction)
    return round(mean(item["score"] for item in breakdown.values()), 4)


def _compute_paraphrase_consistency(results: list[dict[str, Any]]) -> dict[str, float]:
    grouped: dict[str, list[str]] = {}
    for result in results:
        group = result.get("paraphrase_group")
        if group:
            grouped.setdefault(group, []).append(result.get("normalized_answer", ""))

    consistency: dict[str, float] = {}
    for group, answers in grouped.items():
        if len(answers) < 2:
            continue
        pair_scores: list[float] = []
        for index in range(len(answers) - 1):
            for next_index in range(index + 1, len(answers)):
                pair_scores.append(SequenceMatcher(None, answers[index], answers[next_index]).ratio())
        if pair_scores:
            consistency[group] = round(mean(pair_scores), 4)
    return consistency


def _resolve_source_match_status(expected_pdfs: list[str], matched_pdfs: list[str], strict_grounding: bool) -> str:
    expected_set = set(expected_pdfs or [])
    matched_set = set(matched_pdfs or [])

    if not strict_grounding or not expected_set:
        return "not_applicable"
    if expected_set.intersection(matched_set):
        return "matched_expected_pdf"
    if matched_set:
        return "matched_unexpected_pdf"
    return "no_grounding_evidence"


def run_dspy_evaluation(
    examples: list[dspy.Example],
    output_path: str | Path = "artifacts/dspy",
    pdf_registry_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run a deterministic DSPy evaluation loop over UI artifacts using `dspy.Evaluate`."""
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_registry = load_pdf_registry(pdf_registry_path)
    adapter = UIArtifactAdapter(pdf_registry=pdf_registry)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    raw_csv_path = output_dir / f"dspy_evaluate_raw_{timestamp}.csv"
    raw_json_path = output_dir / f"dspy_evaluate_raw_{timestamp}.json"
    evaluator = dspy.Evaluate(
        devset=examples,
        metric=composite_deterministic_metric,
        display_progress=False,
        display_table=False,
        save_as_csv=str(raw_csv_path),
        save_as_json=str(raw_json_path),
    )
    try:
        evaluation_result = evaluator(adapter)
    except PermissionError:
        fallback_evaluator = dspy.Evaluate(
            devset=examples,
            metric=composite_deterministic_metric,
            display_progress=False,
            display_table=False,
            save_as_csv=None,
            save_as_json=None,
        )
        evaluation_result = fallback_evaluator(adapter)

    evaluation_rows = getattr(evaluation_result, "results", []) or []
    if not evaluation_rows:
        evaluation_rows = []
        for example in examples:
            prediction = adapter(**example.inputs().toDict())
            evaluation_rows.append((example, prediction, composite_deterministic_metric(example, prediction)))

    results: list[dict[str, Any]] = []
    total_scores: list[float] = []

    for example, prediction, row_score in evaluation_rows:
        breakdown = build_metric_breakdown(example, prediction)
        composite_score = float(row_score)
        total_scores.append(composite_score)

        expected_pdfs = getattr(example, "expected_pdfs", []) or []
        matched_pdfs = getattr(prediction, "matched_pdfs", []) or []
        strict_grounding = bool(getattr(example, "strict_grounding", False))
        source_match_status = _resolve_source_match_status(expected_pdfs, matched_pdfs, strict_grounding)

        result_row = {
            "id": example.id,
            "question": example.question,
            "answer": example.answer,
            "normalized_answer": prediction.normalized_answer,
            "contexts": getattr(prediction, "normalized_contexts", []),
            "ground_truths": getattr(example, "ground_truths", []),
            "required_keywords": getattr(example, "required_keywords", []),
            "forbidden_patterns": getattr(example, "forbidden_patterns", []),
            "expect_fallback": getattr(example, "expect_fallback", False),
            "fallback_patterns": getattr(example, "fallback_patterns", []),
            "expected_pdfs": expected_pdfs,
            "strict_grounding": strict_grounding,
            "matched_pdfs": matched_pdfs,
            "source_match_status": source_match_status,
            "paraphrase_group": getattr(example, "paraphrase_group", None),
            "detected_fallback": bool(prediction.detected_fallback),
            "context_count": int(prediction.context_count),
            "deterministic_scores": {
                key: value["score"] for key, value in breakdown.items()
            } | {"total": round(composite_score, 4)},
            "issues": [issue for item in breakdown.values() for issue in item["issues"]],
        }
        results.append(result_row)

    paraphrase_consistency = _compute_paraphrase_consistency(results)
    summary = {
        "example_count": len(results),
        "average_score": round(mean(total_scores), 4) if total_scores else 0.0,
        "pass_rate": round(sum(1 for score in total_scores if score >= 0.75) / len(total_scores), 4) if total_scores else 0.0,
        "failures": sum(1 for row in results if row["issues"]),
        "strict_grounding_failures": sum(1 for row in results if row["source_match_status"] == "matched_unexpected_pdf"),
        "unverified_grounding_cases": sum(1 for row in results if row["source_match_status"] == "no_grounding_evidence"),
        "paraphrase_consistency": paraphrase_consistency,
        "dspy_evaluate_score_percent": round(float(getattr(evaluation_result, "score", 0.0)), 4),
        "llm_provider": get_model_label(),
    }

    # Capture evaluation metadata for authentication
    metadata = {
        "evaluation_timestamp": datetime.now().isoformat(),
        "llm_provider": get_model_label(),
        "dspy_version": getattr(dspy, "__version__", "unknown"),
        "min_score_threshold": os.getenv("DSPY_MIN_SCORE", "0.70"),
        "ragas_profile": os.getenv("RAGAS_METRICS_PROFILE", "full"),
        "artifacts_path": str(output_dir),
        "dspy_results_file": "dspy_results.json",
        "dspy_raw_files": f"dspy_evaluate_raw_{timestamp}.csv/json (if disk permissions allow)",
    }

    payload = {"summary": summary, "results": results, "metadata": metadata}
    results_json = json.dumps(payload, indent=2, ensure_ascii=False)
    summary_json = json.dumps(summary, indent=2, ensure_ascii=False)
    (output_dir / "dspy_results.json").write_text(results_json, encoding="utf-8")
    (output_dir / f"dspy_results_{timestamp}.json").write_text(results_json, encoding="utf-8")
    (output_dir / "dspy_score_summary.json").write_text(summary_json, encoding="utf-8")
    (output_dir / f"dspy_score_summary_{timestamp}.json").write_text(summary_json, encoding="utf-8")
    return payload
