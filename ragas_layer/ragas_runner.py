from __future__ import annotations

import os
import concurrent.futures
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.run_config import RunConfig

from audit.reporting import create_enterprise_reporting_assets
from llm_provider import build_ragas_dependencies, get_llm_provider, get_metrics_profile

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# =============================
# Helpers
# =============================
def _to_builtin(value):
    """Recursively convert numpy/pandas objects to plain Python types for JSON serialization."""
    if value is None:
        return None

    if isinstance(value, dict):
        return {str(k): _to_builtin(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_to_builtin(v) for v in value]

    if hasattr(value, "tolist") and callable(value.tolist):
        try:
            return _to_builtin(value.tolist())
        except Exception:
            pass

    if hasattr(value, "item") and callable(value.item):
        try:
            return value.item()
        except Exception:
            pass

    return value


def _rows_from_dataset(dataset: Dataset) -> list[dict[str, Any]]:
    return [dataset[index] for index in range(dataset.num_rows)]


def _filter_rows(
    rows: list[dict[str, Any]],
    *,
    require_contexts: bool = False,
    require_ground_truth: bool = False,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for row in rows:
        contexts = row.get("contexts") or row.get("retrieved_contexts") or []
        ground_truth = row.get("ground_truth") or row.get("reference") or row.get("ground_truths") or []

        if require_contexts and not contexts:
            continue
        if require_ground_truth and not ground_truth:
            continue

        filtered.append(row)

    return filtered


def _build_document_grounding_audit(dataset: Dataset) -> dict[str, Any]:
    checked_rows = 0
    wrong_document_cases: list[dict[str, Any]] = []
    unverifiable_cases: list[dict[str, Any]] = []

    for row in _rows_from_dataset(dataset):
        strict_grounding = bool(row.get("strict_grounding", False))
        expected_pdfs = set(row.get("expected_pdfs") or [])
        matched_pdfs = set(row.get("matched_pdfs") or [])

        if not strict_grounding or not expected_pdfs:
            continue

        checked_rows += 1

        if matched_pdfs and expected_pdfs.isdisjoint(matched_pdfs):
            wrong_document_cases.append(
                {
                    "id": row.get("id"),
                    "question": row.get("question"),
                    "expected_pdfs": sorted(expected_pdfs),
                    "matched_pdfs": sorted(matched_pdfs),
                    "reason": "Answer/citation evidence points to an unexpected PDF.",
                }
            )
        elif not matched_pdfs:
            unverifiable_cases.append(
                {
                    "id": row.get("id"),
                    "question": row.get("question"),
                    "expected_pdfs": sorted(expected_pdfs),
                    "reason": "No citation or context exposed a PDF identifier for this strict-grounding case.",
                }
            )

    return {
        "checked_rows": checked_rows,
        "wrong_document_count": len(wrong_document_cases),
        "wrong_document_cases": wrong_document_cases,
        "unverifiable_count": len(unverifiable_cases),
        "unverifiable_cases": unverifiable_cases,
    }


# =============================
# Metric Catalog (ALL 13 included)
# =============================
def _build_ragas_metric_catalog(ragas_llm: Any | None, ragas_embeddings: Any | None) -> dict[str, Any]:
    """
    Include all 13 metrics.
    Metrics that are unavailable in the installed ragas version are returned as None
    and will be marked as skipped later.
    """
    # Core metrics that are usually present in your ragas stack
    from ragas.metrics._faithfulness import Faithfulness
    from ragas.metrics._answer_relevance import ResponseRelevancy
    from ragas.metrics._factual_correctness import FactualCorrectness
    from ragas.metrics._context_precision import LLMContextPrecisionWithReference, ContextUtilization
    from ragas.metrics._context_recall import LLMContextRecall
    from ragas.metrics._context_entities_recall import ContextEntityRecall
    from ragas.metrics._answer_correctness import AnswerCorrectness

    # Optional / version-dependent metrics
    try:
        from ragas.metrics._noise_sensitivity import NoiseSensitivity
    except Exception:
        NoiseSensitivity = None

    try:
        from ragas.metrics._nv_metrics import ContextRelevance, ResponseGroundedness
    except Exception:
        ContextRelevance = None
        ResponseGroundedness = None

    try:
        from ragas.metrics._simple_criteria import SimpleCriteriaScore
    except Exception:
        SimpleCriteriaScore = None

    answer_relevancy_strictness = int(os.getenv("RAGAS_ANSWER_RELEVANCY_STRICTNESS", "1"))

    return {
        "answer_relevancy": ResponseRelevancy(
            llm=ragas_llm,
            embeddings=ragas_embeddings,
            strictness=answer_relevancy_strictness,
        ) if ragas_llm and ragas_embeddings else None,

        "answer_accuracy": FactualCorrectness(
            llm=ragas_llm,
            name="answer_accuracy",
        ) if ragas_llm else None,

        "faithfulness": Faithfulness(llm=ragas_llm) if ragas_llm else None,

        "context_precision": LLMContextPrecisionWithReference(
            llm=ragas_llm,
            name="context_precision",
        ) if ragas_llm else None,

        "context_utilization": ContextUtilization(llm=ragas_llm) if ragas_llm else None,

        "context_recall": LLMContextRecall(llm=ragas_llm) if ragas_llm else None,

        "context_relevance": ContextRelevance(llm=ragas_llm) if (ragas_llm and ContextRelevance) else None,

        "response_groundedness": ResponseGroundedness(llm=ragas_llm) if (ragas_llm and ResponseGroundedness) else None,

        "context_entity_recall": ContextEntityRecall(llm=ragas_llm) if ragas_llm else None,

        "noise_sensitivity_relevant": NoiseSensitivity(
            llm=ragas_llm,
            mode="relevant",
            name="noise_sensitivity_relevant",
        ) if (ragas_llm and NoiseSensitivity) else None,

        "noise_sensitivity_irrelevant": NoiseSensitivity(
            llm=ragas_llm,
            mode="irrelevant",
            name="noise_sensitivity_irrelevant",
        ) if (ragas_llm and NoiseSensitivity) else None,

        "response_correctness": AnswerCorrectness(
            llm=ragas_llm,
            embeddings=ragas_embeddings,
        ) if ragas_llm and ragas_embeddings else None,

        "answer_completeness": SimpleCriteriaScore(
            name="answer_completeness",
            definition=(
                "Rate how completely the response addresses all aspects of the user question. "
                "1 = severely incomplete, misses major parts; "
                "3 = partially complete, covers main point but omits details; "
                "5 = fully complete, covers all relevant aspects of the question."
            ),
            llm=ragas_llm,
        ) if (ragas_llm and SimpleCriteriaScore) else None,
    }


# =============================
# Safe metric execution
# =============================
def _execute_metric(
    *,
    metric_name: str,
    eligible_rows: list[dict[str, Any]],
    reason_if_empty: str,
    metric_object: Any,
    ragas_llm: Any,
    ragas_embeddings: Any,
    payload: dict[str, Any],
) -> None:
    payload["metric_row_counts"][metric_name] = len(eligible_rows)

    if not eligible_rows:
        payload["skipped_metrics"].append({"metric": metric_name, "reason": reason_if_empty})
        payload["summary"][metric_name] = None
        payload["metric_details"][metric_name] = []
        return

    if metric_object is None:
        payload["skipped_metrics"].append({"metric": metric_name, "reason": "Unsupported metric"})
        payload["summary"][metric_name] = None
        payload["metric_details"][metric_name] = []
        return

    try:
        eligible_dataset = Dataset.from_list(_to_builtin(eligible_rows))

        # Normalize column names for ragas 0.4.x expectations
        col_map = {}
        if "question" in eligible_dataset.column_names and "user_input" not in eligible_dataset.column_names:
            col_map["question"] = "user_input"
        if "answer" in eligible_dataset.column_names and "response" not in eligible_dataset.column_names:
            col_map["answer"] = "response"
        if "ground_truth" in eligible_dataset.column_names and "reference" not in eligible_dataset.column_names:
            col_map["ground_truth"] = "reference"
        if "contexts" in eligible_dataset.column_names and "retrieved_contexts" not in eligible_dataset.column_names:
            col_map["contexts"] = "retrieved_contexts"

        if col_map:
            eligible_dataset = eligible_dataset.rename_columns(col_map)

        provider = get_llm_provider()
        run_config = RunConfig(
            max_workers=1 if provider in {"ollama"} else 2,
        )

        eval_kwargs = dict(
            dataset=eligible_dataset,
            metrics=[metric_object],
            llm=ragas_llm,
            embeddings=ragas_embeddings,
            run_config=run_config,
            raise_exceptions=True,
            show_progress=False,
        )

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            evaluation_result = pool.submit(evaluate, **eval_kwargs).result()

        df = evaluation_result.to_pandas()

        # Column normalization
        actual_col = metric_name
        if metric_name not in df.columns:
            # Some metrics return custom names, try to detect / normalize
            mode_match = next((c for c in df.columns if c.startswith(f"{metric_name}(mode=")), None)
            metric_natural_name = getattr(metric_object, "name", None)

            if mode_match:
                df = df.rename(columns={mode_match: metric_name})
                actual_col = metric_name
            elif metric_natural_name and metric_natural_name != metric_name and metric_natural_name in df.columns:
                df = df.rename(columns={metric_natural_name: metric_name})
                actual_col = metric_name
            else:
                raise RuntimeError(
                    f"Metric '{metric_name}' result column was missing from RAGAS output. "
                    f"Available columns: {list(df.columns)}"
                )

        valid_scores = df[actual_col].dropna()
        if valid_scores.empty:
            raise RuntimeError(
                f"Metric '{metric_name}' returned no valid scores."
            )

        payload["executed_metrics"].append(metric_name)
        payload["metric_details"][metric_name] = _to_builtin(df.to_dict(orient="records"))
        payload["summary"][metric_name] = round(float(valid_scores.mean()), 4)

    except Exception as exc:
        payload["skipped_metrics"].append({"metric": metric_name, "reason": str(exc)})
        payload["summary"][metric_name] = None
        payload["metric_details"][metric_name] = []


# =============================
# Main runner
# =============================
def run_ragas_evaluation(
    dataset: Dataset,
    metrics_config: dict[str, Any] | None = None,
    output_dir: str | Path = "artifacts/ragas",
) -> dict[str, Any]:
    metrics_config = metrics_config or {}
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Thresholds
    answer_relevancy_threshold = float(metrics_config.get("answer_relevancy_threshold", os.getenv("RAGAS_ANSWER_RELEVANCY_THRESHOLD", "0.65")))
    faithfulness_threshold = float(metrics_config.get("faithfulness_threshold", os.getenv("RAGAS_FAITHFULNESS_THRESHOLD", "0.70")))
    answer_accuracy_threshold = float(metrics_config.get("answer_accuracy_threshold", os.getenv("RAGAS_ANSWER_ACCURACY_THRESHOLD", "0.70")))
    context_precision_threshold = float(metrics_config.get("context_precision_threshold", os.getenv("RAGAS_CONTEXT_PRECISION_THRESHOLD", "0.70")))
    context_utilization_threshold = float(metrics_config.get("context_utilization_threshold", os.getenv("RAGAS_CONTEXT_UTILIZATION_THRESHOLD", "0.70")))
    context_recall_threshold = float(metrics_config.get("context_recall_threshold", os.getenv("RAGAS_CONTEXT_RECALL_THRESHOLD", "0.70")))
    context_relevance_threshold = float(metrics_config.get("context_relevance_threshold", os.getenv("RAGAS_CONTEXT_RELEVANCE_THRESHOLD", "0.70")))
    response_groundedness_threshold = float(metrics_config.get("response_groundedness_threshold", os.getenv("RAGAS_RESPONSE_GROUNDEDNESS_THRESHOLD", "0.70")))
    context_entity_recall_threshold = float(metrics_config.get("context_entity_recall_threshold", os.getenv("RAGAS_CONTEXT_ENTITY_RECALL_THRESHOLD", "0.70")))
    noise_sensitivity_relevant_threshold = float(metrics_config.get("noise_sensitivity_relevant_threshold", os.getenv("RAGAS_NOISE_SENSITIVITY_RELEVANT_THRESHOLD", "0.30")))
    noise_sensitivity_irrelevant_threshold = float(metrics_config.get("noise_sensitivity_irrelevant_threshold", os.getenv("RAGAS_NOISE_SENSITIVITY_IRRELEVANT_THRESHOLD", "0.30")))
    response_correctness_threshold = float(metrics_config.get("response_correctness_threshold", os.getenv("RAGAS_RESPONSE_CORRECTNESS_THRESHOLD", "0.70")))
    answer_completeness_threshold = float(metrics_config.get("answer_completeness_threshold", os.getenv("RAGAS_ANSWER_COMPLETENESS_THRESHOLD", "3.0")))

    metrics_profile = get_metrics_profile()

    ragas_llm, ragas_embeddings, llm_issue, provider_meta = build_ragas_dependencies()
    if llm_issue:
        raise RuntimeError(f"LLM/embedding provider is not ready: {llm_issue}")

    metric_catalog = _build_ragas_metric_catalog(ragas_llm, ragas_embeddings)

    rows = _rows_from_dataset(dataset)
    rows_for_answer_relevancy = [row for row in rows if not bool(row.get("expect_fallback", False))]
    rows_with_ground_truth = _filter_rows(rows, require_ground_truth=True)
    rows_with_contexts = _filter_rows(rows, require_contexts=True)
    rows_with_contexts_and_ground_truth = _filter_rows(rows, require_contexts=True, require_ground_truth=True)

    payload: dict[str, Any] = {
        "dataset_size": dataset.num_rows,
        "thresholds": {
            "answer_relevancy": answer_relevancy_threshold,
            "faithfulness": faithfulness_threshold,
            "answer_accuracy": answer_accuracy_threshold,
            "context_precision": context_precision_threshold,
            "context_utilization": context_utilization_threshold,
            "context_recall": context_recall_threshold,
            "context_relevance": context_relevance_threshold,
            "response_groundedness": response_groundedness_threshold,
            "context_entity_recall": context_entity_recall_threshold,
            "noise_sensitivity_relevant": noise_sensitivity_relevant_threshold,
            "noise_sensitivity_irrelevant": noise_sensitivity_irrelevant_threshold,
            "response_correctness": response_correctness_threshold,
            "answer_completeness": answer_completeness_threshold,
        },
        "provider": provider_meta,
        "metrics_profile": metrics_profile,
        "answer_relevancy_scope": "non_fallback_only",
        "executed_metrics": [],
        "skipped_metrics": [],
        "summary": {},
        "metric_row_counts": {},
        "metric_details": {},
        "rows": [],
        "document_grounding_audit": _build_document_grounding_audit(dataset),
    }

    # Execute all 13 metrics (or gracefully skip)
    _execute_metric(
        metric_name="answer_relevancy",
        eligible_rows=rows_for_answer_relevancy,
        reason_if_empty="No in-scope rows were available for answer relevancy evaluation.",
        metric_object=metric_catalog.get("answer_relevancy"),
        ragas_llm=ragas_llm,
        ragas_embeddings=ragas_embeddings,
        payload=payload,
    )

    _execute_metric(
        metric_name="answer_accuracy",
        eligible_rows=rows_with_ground_truth,
        reason_if_empty="Answer accuracy requires a reference/ground-truth answer.",
        metric_object=metric_catalog.get("answer_accuracy"),
        ragas_llm=ragas_llm,
        ragas_embeddings=ragas_embeddings,
        payload=payload,
    )

    _execute_metric(
        metric_name="faithfulness",
        eligible_rows=rows_with_contexts,
        reason_if_empty="No contexts/citations were captured from UI or network.",
        metric_object=metric_catalog.get("faithfulness"),
        ragas_llm=ragas_llm,
        ragas_embeddings=ragas_embeddings,
        payload=payload,
    )

    _execute_metric(
        metric_name="context_precision",
        eligible_rows=rows_with_contexts_and_ground_truth,
        reason_if_empty="Context precision requires both retrieved contexts and a reference/ground-truth answer.",
        metric_object=metric_catalog.get("context_precision"),
        ragas_llm=ragas_llm,
        ragas_embeddings=ragas_embeddings,
        payload=payload,
    )

    _execute_metric(
        metric_name="context_utilization",
        eligible_rows=rows_with_contexts,
        reason_if_empty="Context utilization requires retrieved contexts plus the generated response.",
        metric_object=metric_catalog.get("context_utilization"),
        ragas_llm=ragas_llm,
        ragas_embeddings=ragas_embeddings,
        payload=payload,
    )

    _execute_metric(
        metric_name="context_recall",
        eligible_rows=rows_with_contexts_and_ground_truth,
        reason_if_empty="Context recall requires both retrieved contexts and a reference/ground-truth answer.",
        metric_object=metric_catalog.get("context_recall"),
        ragas_llm=ragas_llm,
        ragas_embeddings=ragas_embeddings,
        payload=payload,
    )

    _execute_metric(
        metric_name="context_relevance",
        eligible_rows=rows_with_contexts,
        reason_if_empty="Context relevance requires retrieved contexts plus the user input.",
        metric_object=metric_catalog.get("context_relevance"),
        ragas_llm=ragas_llm,
        ragas_embeddings=ragas_embeddings,
        payload=payload,
    )

    _execute_metric(
        metric_name="response_groundedness",
        eligible_rows=rows_with_contexts,
        reason_if_empty="Response groundedness requires a response and retrieved contexts.",
        metric_object=metric_catalog.get("response_groundedness"),
        ragas_llm=ragas_llm,
        ragas_embeddings=ragas_embeddings,
        payload=payload,
    )

    _execute_metric(
        metric_name="context_entity_recall",
        eligible_rows=rows_with_contexts_and_ground_truth,
        reason_if_empty="Context entity recall requires retrieved contexts and a reference/ground-truth answer.",
        metric_object=metric_catalog.get("context_entity_recall"),
        ragas_llm=ragas_llm,
        ragas_embeddings=ragas_embeddings,
        payload=payload,
    )

    _execute_metric(
        metric_name="noise_sensitivity_relevant",
        eligible_rows=rows_with_contexts_and_ground_truth,
        reason_if_empty="Noise sensitivity requires user_input, response, reference, and retrieved contexts.",
        metric_object=metric_catalog.get("noise_sensitivity_relevant"),
        ragas_llm=ragas_llm,
        ragas_embeddings=ragas_embeddings,
        payload=payload,
    )

    _execute_metric(
        metric_name="noise_sensitivity_irrelevant",
        eligible_rows=rows_with_contexts_and_ground_truth,
        reason_if_empty="Noise sensitivity requires user_input, response, reference, and retrieved contexts.",
        metric_object=metric_catalog.get("noise_sensitivity_irrelevant"),
        ragas_llm=ragas_llm,
        ragas_embeddings=ragas_embeddings,
        payload=payload,
    )

    _execute_metric(
        metric_name="response_correctness",
        eligible_rows=rows_with_ground_truth,
        reason_if_empty="Response correctness requires a reference/ground-truth answer.",
        metric_object=metric_catalog.get("response_correctness"),
        ragas_llm=ragas_llm,
        ragas_embeddings=ragas_embeddings,
        payload=payload,
    )

    _execute_metric(
        metric_name="answer_completeness",
        eligible_rows=rows_for_answer_relevancy,
        reason_if_empty="No in-scope rows were available for answer completeness evaluation.",
        metric_object=metric_catalog.get("answer_completeness"),
        ragas_llm=ragas_llm,
        ragas_embeddings=ragas_embeddings,
        payload=payload,
    )

    # =============================
    # Build bridge-compatible rows
    # =============================
    final_rows: list[dict[str, Any]] = []

    for base_row in rows:
        row_id = base_row.get("id")

        new_row: dict[str, Any] = {
            "id": base_row.get("id"),
            "question": base_row.get("question"),
            "response": base_row.get("response") or base_row.get("answer"),
            "ground_truth": base_row.get("ground_truth"),
            "retrieved_chunks": _to_builtin(base_row.get("contexts") or base_row.get("retrieved_contexts") or []),
            "citations": _to_builtin(base_row.get("agent_citations") or []),
            "citation_quotes": _to_builtin(base_row.get("agent_citation_quotes") or []),
            "latency_seconds": _to_builtin(base_row.get("latency_seconds")),
        }

        token_usage = base_row.get("token_usage") or {}
        new_row["total_tokens"] = _to_builtin(token_usage.get("total_tokens"))
        new_row["prompt_tokens"] = _to_builtin(token_usage.get("prompt_tokens"))
        new_row["completion_tokens"] = _to_builtin(token_usage.get("completion_tokens"))

        for metric_name, threshold in payload["thresholds"].items():
            match = next(
                (
                    r for r in payload["metric_details"].get(metric_name, [])
                    if r.get("id") == row_id or r.get("question") == base_row.get("question")
                ),
                None,
            )

            score = _to_builtin(match.get(metric_name)) if match else None
            new_row[metric_name] = score

            if score is None:
                new_row[f"{metric_name}_result"] = "SKIPPED"
            elif metric_name.startswith("noise_sensitivity"):
                new_row[f"{metric_name}_result"] = "PASS" if score <= threshold else "FAIL"
            else:
                new_row[f"{metric_name}_result"] = "PASS" if score >= threshold else "FAIL"

        new_row["has_contexts"] = bool(base_row.get("contexts") or base_row.get("retrieved_contexts"))
        new_row["has_ground_truth"] = bool(base_row.get("ground_truth") or base_row.get("reference"))

        if not (base_row.get("contexts") or base_row.get("retrieved_contexts")):
            new_row["skipped_metrics_notes"] = "No retrieved contexts available."
        elif not (base_row.get("ground_truth") or base_row.get("reference")):
            new_row["skipped_metrics_notes"] = "No ground truth available."
        else:
            new_row["skipped_metrics_notes"] = "All applicable metrics executed."

        new_row["run_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        final_rows.append(_to_builtin(new_row))

    payload["rows"] = final_rows

    # Save CSV + JSON
    results_df = pd.DataFrame(final_rows)
    results_df.to_csv(output_path / "ragas_results.csv", index=False)

    with open(output_path / "ragas_results.json", "w", encoding="utf-8") as f:
        json.dump(_to_builtin(payload), f, indent=2, ensure_ascii=False)

    # Generate bridge report in the existing bridge flow
    try:
        payload["enterprise_reporting"] = create_enterprise_reporting_assets(
            PROJECT_ROOT,
            ragas_results=_to_builtin(payload),
            report_mode="bridge",
        )
    except Exception as exc:
        print(f"⚠️ Report generation failed: {exc}")

    return payload