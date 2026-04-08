from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from audit.reporting import create_enterprise_reporting_assets
from llm_provider import build_ragas_dependencies, get_llm_provider, get_metrics_profile, get_model_label

import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.run_config import RunConfig


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _build_ragas_metric_catalog(ragas_llm: Any | None, ragas_embeddings: Any | None) -> dict[str, Any]:
    try:
        from ragas.metrics.collections import (
            AnswerAccuracy,
            AnswerRelevancy,
            ContextEntityRecall,
            ContextPrecision,
            ContextRecall,
            ContextRelevance,
            ContextUtilization,
            Faithfulness,
            NoiseSensitivity,
            ResponseGroundedness,
        )

        context_precision_metric = None
        if ragas_llm:
            try:
                context_precision_metric = ContextPrecision(llm=ragas_llm)
            except Exception:
                from ragas.metrics.collections.context_precision import ContextPrecisionWithReference

                context_precision_metric = ContextPrecisionWithReference(llm=ragas_llm)

        answer_relevancy_strictness = int(os.getenv("RAGAS_ANSWER_RELEVANCY_STRICTNESS", "3"))

        return {
            "faithfulness": Faithfulness(llm=ragas_llm) if ragas_llm else None,
            "answer_relevancy": AnswerRelevancy(
                llm=ragas_llm,
                embeddings=ragas_embeddings,
                strictness=answer_relevancy_strictness,
            )
            if ragas_llm and ragas_embeddings
            else None,
            "answer_accuracy": AnswerAccuracy(llm=ragas_llm) if ragas_llm else None,
            "context_precision": context_precision_metric,
            "context_utilization": ContextUtilization(llm=ragas_llm) if ragas_llm else None,
            "context_recall": ContextRecall(llm=ragas_llm) if ragas_llm else None,
            "context_relevance": ContextRelevance(llm=ragas_llm) if ragas_llm else None,
            "response_groundedness": ResponseGroundedness(llm=ragas_llm) if ragas_llm else None,
            "context_entity_recall": ContextEntityRecall(llm=ragas_llm) if ragas_llm else None,
            "noise_sensitivity_relevant": NoiseSensitivity(
                llm=ragas_llm,
                mode="relevant",
                name="noise_sensitivity_relevant",
            ) if ragas_llm else None,
            "noise_sensitivity_irrelevant": NoiseSensitivity(
                llm=ragas_llm,
                mode="irrelevant",
                name="noise_sensitivity_irrelevant",
            ) if ragas_llm else None,
        }
    except Exception:
        import ragas.metrics as ragas_metrics

        candidates = {
            "faithfulness": ["faithfulness", "Faithfulness"],
            "answer_relevancy": ["answer_relevancy", "answer_relevance", "ResponseRelevancy"],
            "answer_accuracy": ["answer_accuracy", "AnswerAccuracy"],
            "context_precision": ["context_precision", "ContextPrecision", "LLMContextPrecisionWithReference"],
            "context_utilization": ["context_utilization", "ContextUtilization", "LLMContextPrecisionWithoutReference"],
            "context_recall": ["context_recall", "ContextRecall", "LLMContextRecall"],
            "context_relevance": ["context_relevance", "ContextRelevance"],
            "response_groundedness": ["response_groundedness", "ResponseGroundedness"],
            "context_entity_recall": ["context_entity_recall", "ContextEntityRecall"],
            "noise_sensitivity_relevant": ["noise_sensitivity", "NoiseSensitivity"],
            "noise_sensitivity_irrelevant": ["noise_sensitivity", "NoiseSensitivity"],
        }

        catalog: dict[str, Any] = {}
        for metric_name, attrs in candidates.items():
            metric_object = None
            for attr in attrs:
                if hasattr(ragas_metrics, attr):
                    raw_value = getattr(ragas_metrics, attr)
                    if isinstance(raw_value, type):
                        if metric_name == "noise_sensitivity_relevant":
                            metric_object = raw_value(mode="relevant", name="noise_sensitivity_relevant")
                        elif metric_name == "noise_sensitivity_irrelevant":
                            metric_object = raw_value(mode="irrelevant", name="noise_sensitivity_irrelevant")
                        else:
                            metric_object = raw_value()
                    else:
                        metric_object = raw_value
                    break
            catalog[metric_name] = metric_object
        return catalog


def _load_metric_cache(cache_path: Path) -> dict[str, Any]:
    if not cache_path.exists():
        return {}
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _build_metric_cache_key(row: dict[str, Any], metric_name: str, model_label: str) -> str:
    payload = {
        "metric": metric_name,
        "model": model_label,
        "question": row.get("question") or row.get("user_input", ""),
        "answer": row.get("answer") or row.get("response", ""),
        "reference": row.get("reference") or row.get("ground_truth") or row.get("ground_truths") or [],
        "contexts": row.get("contexts") or row.get("retrieved_contexts") or [],
    }
    normalized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _rows_from_dataset(dataset: Dataset) -> list[dict[str, Any]]:
    return [dataset[index] for index in range(dataset.num_rows)]


def _filter_rows(rows: list[dict[str, Any]], *, require_contexts: bool = False, require_ground_truth: bool = False) -> list[dict[str, Any]]:
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
                    "reason": "No citation or network context exposed a PDF identifier for this strict-grounding case.",
                }
            )

    return {
        "checked_rows": checked_rows,
        "wrong_document_count": len(wrong_document_cases),
        "wrong_document_cases": wrong_document_cases,
        "unverifiable_count": len(unverifiable_cases),
        "unverifiable_cases": unverifiable_cases,
    }


def _write_csv_with_fallback(dataframe: pd.DataFrame, target_path: Path) -> None:
    try:
        dataframe.to_csv(target_path, index=False)
    except PermissionError:
        fallback_name = f"{target_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}{target_path.suffix}"
        dataframe.to_csv(target_path.with_name(fallback_name), index=False)


def _write_json_with_fallback(payload: dict[str, Any], target_path: Path) -> None:
    serialized = json.dumps(payload, indent=2, ensure_ascii=False)
    try:
        target_path.write_text(serialized, encoding="utf-8")
    except PermissionError:
        fallback_name = f"{target_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}{target_path.suffix}"
        target_path.with_name(fallback_name).write_text(serialized, encoding="utf-8")


def run_ragas_evaluation(
    dataset: Dataset,
    metrics_config: dict[str, Any] | None = None,
    output_dir: str | Path = "artifacts/ragas",
) -> dict[str, Any]:
    """Run RAGAS conditionally and save JSON + CSV reports."""
    metrics_config = metrics_config or {}
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    answer_relevancy_threshold = float(
        metrics_config.get("answer_relevancy_threshold", os.getenv("RAGAS_ANSWER_RELEVANCY_THRESHOLD", "0.65"))
    )
    faithfulness_threshold = float(
        metrics_config.get("faithfulness_threshold", os.getenv("RAGAS_FAITHFULNESS_THRESHOLD", "0.70"))
    )
    answer_accuracy_threshold = float(
        metrics_config.get("answer_accuracy_threshold", os.getenv("RAGAS_ANSWER_ACCURACY_THRESHOLD", "0.70"))
    )
    context_precision_threshold = float(
        metrics_config.get("context_precision_threshold", os.getenv("RAGAS_CONTEXT_PRECISION_THRESHOLD", "0.70"))
    )
    context_utilization_threshold = float(
        metrics_config.get("context_utilization_threshold", os.getenv("RAGAS_CONTEXT_UTILIZATION_THRESHOLD", "0.70"))
    )
    context_recall_threshold = float(
        metrics_config.get("context_recall_threshold", os.getenv("RAGAS_CONTEXT_RECALL_THRESHOLD", "0.70"))
    )
    context_relevance_threshold = float(
        metrics_config.get("context_relevance_threshold", os.getenv("RAGAS_CONTEXT_RELEVANCE_THRESHOLD", "0.70"))
    )
    response_groundedness_threshold = float(
        metrics_config.get("response_groundedness_threshold", os.getenv("RAGAS_RESPONSE_GROUNDEDNESS_THRESHOLD", "0.70"))
    )
    context_entity_recall_threshold = float(
        metrics_config.get("context_entity_recall_threshold", os.getenv("RAGAS_CONTEXT_ENTITY_RECALL_THRESHOLD", "0.70"))
    )
    noise_sensitivity_relevant_threshold = float(
        metrics_config.get("noise_sensitivity_relevant_threshold", os.getenv("RAGAS_NOISE_SENSITIVITY_RELEVANT_THRESHOLD", "0.30"))
    )
    noise_sensitivity_irrelevant_threshold = float(
        metrics_config.get("noise_sensitivity_irrelevant_threshold", os.getenv("RAGAS_NOISE_SENSITIVITY_IRRELEVANT_THRESHOLD", "0.30"))
    )

    metrics_profile = get_metrics_profile()
    ragas_llm, ragas_embeddings, llm_issue, provider_meta = build_ragas_dependencies()
    metric_catalog = _build_ragas_metric_catalog(ragas_llm, ragas_embeddings)
    cache_path = output_path / "ragas_cache.json"
    metric_cache = _load_metric_cache(cache_path)

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

    def execute_metric(metric_name: str, eligible_rows: list[dict[str, Any]], reason_if_empty: str) -> None:
        payload["metric_row_counts"][metric_name] = len(eligible_rows)

        if metrics_profile == "fast" and metric_name != "answer_relevancy":
            payload["skipped_metrics"].append(
                {
                    "metric": metric_name,
                    "reason": "RAGAS_METRICS_PROFILE=fast only runs answer_relevancy for quick local feedback.",
                }
            )
            return

        if not eligible_rows:
            payload["skipped_metrics"].append({"metric": metric_name, "reason": reason_if_empty})
            return

        model_label = provider_meta.get("model", get_model_label())
        cached_metric_rows: list[dict[str, Any]] = []
        uncached_rows: list[dict[str, Any]] = []
        for row in eligible_rows:
            cache_key = _build_metric_cache_key(row, metric_name, model_label)
            cached_entry = metric_cache.get(cache_key)
            if cached_entry and cached_entry.get("score") is not None:
                cached_metric_rows.append({
                    "id": row.get("id"),
                    "question": row.get("question") or row.get("user_input"),
                    metric_name: cached_entry.get("score"),
                    "cache_hit": True,
                })
            else:
                uncached_rows.append(row)

        metric_object = metric_catalog.get(metric_name)
        if metric_object is None and not cached_metric_rows:
            reason = llm_issue or "Metric not available in installed RAGAS version."
            payload["skipped_metrics"].append({"metric": metric_name, "reason": reason})
            return

        fresh_metric_rows: list[dict[str, Any]] = []
        if uncached_rows:
            if llm_issue:
                if cached_metric_rows:
                    uncached_rows = []
                else:
                    payload["skipped_metrics"].append({"metric": metric_name, "reason": llm_issue})
                    return

            try:
                eligible_dataset = Dataset.from_list(uncached_rows)
                provider = get_llm_provider()
                run_config = RunConfig(
                    timeout=int(os.getenv("RAGAS_TIMEOUT_SECONDS", "180")),
                    max_retries=int(os.getenv("RAGAS_MAX_RETRIES", "2")),
                    max_wait=int(os.getenv("RAGAS_MAX_WAIT_SECONDS", "20")),
                    max_workers=int(os.getenv("RAGAS_MAX_WORKERS", "1" if provider in {"ollama", "gemini"} else "2")),
                )
                evaluation_result = evaluate(
                    dataset=eligible_dataset,
                    metrics=[metric_object],
                    llm=ragas_llm,
                    embeddings=ragas_embeddings,
                    run_config=run_config,
                    raise_exceptions=False,
                    show_progress=False,
                    batch_size=int(os.getenv("RAGAS_BATCH_SIZE", "1")),
                    experiment_name=f"ui_chatbot_{metric_name}",
                )
                result_df = evaluation_result.to_pandas()

                if metric_name not in result_df.columns:
                    payload["skipped_metrics"].append(
                        {"metric": metric_name, "reason": "Metric result column was missing from the RAGAS output."}
                    )
                    return

                valid_scores = result_df[metric_name].dropna()
                if valid_scores.empty and not cached_metric_rows:
                    payload["skipped_metrics"].append(
                        {
                            "metric": metric_name,
                            "reason": "Metric returned no valid scores, likely due to evaluator quota exhaustion or provider errors.",
                        }
                    )
                    return

                fresh_metric_rows = result_df.to_dict(orient="records")
                for source_row, metric_row in zip(uncached_rows, fresh_metric_rows, strict=False):
                    score = metric_row.get(metric_name)
                    cache_key = _build_metric_cache_key(source_row, metric_name, model_label)
                    if score is not None and not pd.isna(score):
                        metric_cache[cache_key] = {
                            "score": float(score),
                            "metric": metric_name,
                            "model": model_label,
                            "cached_at_utc": datetime.now().isoformat(),
                        }
                        metric_row["cache_hit"] = False
            except Exception as exc:
                payload["skipped_metrics"].append({"metric": metric_name, "reason": f"RAGAS evaluation failed: {exc}"})
                return

        metric_rows = cached_metric_rows + fresh_metric_rows
        if not metric_rows:
            payload["skipped_metrics"].append({"metric": metric_name, "reason": "No metric rows were produced."})
            return

        result_df = pd.DataFrame(metric_rows)
        valid_scores = result_df[metric_name].dropna() if metric_name in result_df.columns else pd.Series(dtype=float)
        if valid_scores.empty:
            payload["skipped_metrics"].append(
                {"metric": metric_name, "reason": "Metric rows were produced but all scores were null."}
            )
            return

        payload["executed_metrics"].append(metric_name)
        payload["metric_details"][metric_name] = metric_rows
        payload["summary"][metric_name] = round(float(valid_scores.mean()), 4)

    execute_metric(
        "answer_relevancy",
        rows_for_answer_relevancy,
        reason_if_empty="No in-scope rows were available for answer relevancy evaluation.",
    )
    execute_metric(
        "answer_accuracy",
        rows_with_ground_truth,
        reason_if_empty="Answer accuracy requires a reference/ground-truth answer.",
    )
    execute_metric(
        "faithfulness",
        rows_with_contexts,
        reason_if_empty="No contexts/citations were captured from UI or network.",
    )
    execute_metric(
        "context_precision",
        rows_with_contexts_and_ground_truth,
        reason_if_empty="Context precision requires both retrieved contexts and a reference/ground-truth answer.",
    )
    execute_metric(
        "context_utilization",
        rows_with_contexts,
        reason_if_empty="Context utilization requires retrieved contexts plus the generated response.",
    )
    execute_metric(
        "context_recall",
        rows_with_contexts_and_ground_truth,
        reason_if_empty="Context recall requires both retrieved contexts and a reference/ground-truth answer.",
    )
    execute_metric(
        "context_relevance",
        rows_with_contexts,
        reason_if_empty="Context relevance requires retrieved contexts plus the user input.",
    )
    execute_metric(
        "response_groundedness",
        rows_with_contexts,
        reason_if_empty="Response groundedness requires a response and retrieved contexts.",
    )
    execute_metric(
        "context_entity_recall",
        rows_with_contexts_and_ground_truth,
        reason_if_empty="Context entity recall requires retrieved contexts and a reference/ground-truth answer with entities to compare.",
    )
    execute_metric(
        "noise_sensitivity_relevant",
        rows_with_contexts_and_ground_truth,
        reason_if_empty="Noise sensitivity requires user_input, response, reference, and retrieved contexts.",
    )
    execute_metric(
        "noise_sensitivity_irrelevant",
        rows_with_contexts_and_ground_truth,
        reason_if_empty="Noise sensitivity requires user_input, response, reference, and retrieved contexts.",
    )

    combined_rows: dict[str, dict[str, Any]] = {}
    for metric_name, metric_rows in payload["metric_details"].items():
        for index, row in enumerate(metric_rows):
            row_id = str(row.get("id") or row.get("question") or f"{metric_name}_{index}")
            combined_rows.setdefault(
                row_id,
                {
                    "id": row.get("id"),
                    "question": row.get("question") or row.get("user_input"),
                },
            )
            combined_rows[row_id][metric_name] = row.get(metric_name)

    payload["rows"] = list(combined_rows.values())

    if payload["rows"]:
        results_df = pd.DataFrame(payload["rows"])
    else:
        results_df = dataset.to_pandas()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    _write_csv_with_fallback(results_df, output_path / "ragas_results.csv")
    _write_csv_with_fallback(results_df, output_path / f"ragas_results_{timestamp}.csv")
    _write_json_with_fallback(payload, output_path / "ragas_results.json")
    _write_json_with_fallback(payload, output_path / f"ragas_results_{timestamp}.json")
    _write_json_with_fallback(metric_cache, cache_path)

    payload["enterprise_reporting"] = create_enterprise_reporting_assets(
        PROJECT_ROOT,
        ragas_results=payload,
    )
    _write_json_with_fallback(payload, output_path / "ragas_results.json")
    return payload
