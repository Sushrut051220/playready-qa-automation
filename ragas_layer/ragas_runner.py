from __future__ import annotations

import asyncio
import concurrent.futures
import json
import os
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


# Metric metadata: description, direction, whether contexts are required
METRIC_METADATA = {
    "answer_relevancy": {
        "what_it_measures": "Is the answer relevant to the question?",
        "direction": "Higher is better",
        "requires_contexts": False,
    },
    "answer_accuracy": {
        "what_it_measures": "Does the answer match ground truth factually?",
        "direction": "Higher is better",
        "requires_contexts": False,
    },
    "faithfulness": {
        "what_it_measures": "Is the answer grounded in retrieved contexts?",
        "direction": "Higher is better",
        "requires_contexts": True,
    },
    "context_precision": {
        "what_it_measures": "Are retrieved contexts relevant to the ground truth?",
        "direction": "Higher is better",
        "requires_contexts": True,
    },
    "context_utilization": {
        "what_it_measures": "How well does the answer use the retrieved contexts?",
        "direction": "Higher is better",
        "requires_contexts": True,
    },
    "context_recall": {
        "what_it_measures": "Do retrieved contexts cover the ground truth?",
        "direction": "Higher is better",
        "requires_contexts": True,
    },
    "context_relevance": {
        "what_it_measures": "Are retrieved contexts relevant to the question?",
        "direction": "Higher is better",
        "requires_contexts": True,
    },
    "response_groundedness": {
        "what_it_measures": "Is the response grounded in retrieved contexts?",
        "direction": "Higher is better",
        "requires_contexts": True,
    },
    "context_entity_recall": {
        "what_it_measures": "Do retrieved contexts contain expected entities from ground truth?",
        "direction": "Higher is better",
        "requires_contexts": True,
    },
    "noise_sensitivity_relevant": {
        "what_it_measures": "Robustness to relevant noise in retrieved contexts.",
        "direction": "Lower is better",
        "requires_contexts": True,
    },
    "noise_sensitivity_irrelevant": {
        "what_it_measures": "Robustness to irrelevant noise in retrieved contexts.",
        "direction": "Lower is better",
        "requires_contexts": True,
    },
    "response_correctness": {
        "what_it_measures": "Factual + semantic correctness vs reference answer.",
        "direction": "Higher is better",
        "requires_contexts": False,
    },
    "answer_completeness": {
        "what_it_measures": "Does the answer cover all aspects of the question? (1-5 scale)",
        "direction": "Higher is better",
        "requires_contexts": False,
    },
}


class _AsyncEmbeddingAdapter:
    def __init__(self, embeddings):
        self._emb = embeddings

    def __getattr__(self, name):
        return getattr(self._emb, name)

    def embed_text(self, text):
        if hasattr(self._emb, "embed_text"):
            return self._emb.embed_text(text)
        if hasattr(self._emb, "embed_query"):
            return self._emb.embed_query(text)
        raise TypeError("No embed_text() or embed_query() on embeddings.")

    def embed_query(self, text):
        return self.embed_text(text)

    def embed_documents(self, texts):
        if hasattr(self._emb, "embed_documents"):
            return self._emb.embed_documents(texts)
        return [self.embed_text(t) for t in texts]

    async def aembed_text(self, text):
        return await asyncio.to_thread(self.embed_text, text)

    async def aembed_query(self, text):
        return await asyncio.to_thread(self.embed_text, text)

    async def aembed_documents(self, texts):
        return await asyncio.to_thread(self.embed_documents, texts)


def _build_ragas_metric_catalog(ragas_llm, ragas_embeddings):
    from ragas.metrics._faithfulness import Faithfulness
    from ragas.metrics._answer_relevance import ResponseRelevancy
    from ragas.metrics._factual_correctness import FactualCorrectness
    from ragas.metrics._context_precision import LLMContextPrecisionWithReference, ContextUtilization
    from ragas.metrics._context_recall import LLMContextRecall
    from ragas.metrics._context_entities_recall import ContextEntityRecall
    from ragas.metrics._noise_sensitivity import NoiseSensitivity
    from ragas.metrics._nv_metrics import ContextRelevance, ResponseGroundedness
    from ragas.metrics._answer_correctness import AnswerCorrectness
    from ragas.metrics._simple_criteria import SimpleCriteriaScore

    answer_relevancy_strictness = int(os.getenv("RAGAS_ANSWER_RELEVANCY_STRICTNESS", "1"))

    return {
        "faithfulness": Faithfulness(llm=ragas_llm) if ragas_llm else None,
        "answer_relevancy": ResponseRelevancy(
            llm=ragas_llm,
            embeddings=ragas_embeddings,
            strictness=answer_relevancy_strictness,
        ) if ragas_llm and ragas_embeddings else None,
        "answer_accuracy": FactualCorrectness(llm=ragas_llm, name="answer_accuracy") if ragas_llm else None,
        "context_precision": LLMContextPrecisionWithReference(llm=ragas_llm, name="context_precision") if ragas_llm else None,
        "context_utilization": ContextUtilization(llm=ragas_llm) if ragas_llm else None,
        "context_recall": LLMContextRecall(llm=ragas_llm) if ragas_llm else None,
        "context_relevance": ContextRelevance(llm=ragas_llm) if ragas_llm else None,
        "response_groundedness": ResponseGroundedness(llm=ragas_llm) if ragas_llm else None,
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
        ) if ragas_llm else None,
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


def _rows_from_dataset(dataset):
    if isinstance(dataset, list):
        return dataset
    num_rows = getattr(dataset, "num_rows", None)
    if isinstance(num_rows, int):
        return [dataset[i] for i in range(num_rows)]
    raise TypeError(f"Unsupported dataset type: {type(dataset)}")


def _filter_rows(rows, *, require_contexts=False, require_ground_truth=False):
    filtered = []
    for row in rows:
        contexts = row.get("contexts") or row.get("retrieved_contexts") or []
        ground_truth = row.get("ground_truth") or row.get("reference") or row.get("ground_truths") or []
        if require_contexts and not contexts:
            continue
        if require_ground_truth and not ground_truth:
            continue
        filtered.append(row)
    return filtered


def _build_document_grounding_audit(dataset):
    checked_rows = 0
    wrong_document_cases = []
    unverifiable_cases = []

    for row in _rows_from_dataset(dataset):
        strict_grounding = bool(row.get("strict_grounding", False))
        expected_pdfs = set(row.get("expected_pdfs") or [])
        matched_pdfs = set(row.get("matched_pdfs") or [])
        if not strict_grounding or not expected_pdfs:
            continue
        checked_rows += 1
        if matched_pdfs and expected_pdfs.isdisjoint(matched_pdfs):
            wrong_document_cases.append({
                "id": row.get("id"),
                "question": row.get("question") or row.get("user_input"),
                "expected_pdfs": sorted(expected_pdfs),
                "matched_pdfs": sorted(matched_pdfs),
                "reason": "Answer/citation evidence points to an unexpected PDF.",
            })
        elif not matched_pdfs:
            unverifiable_cases.append({
                "id": row.get("id"),
                "question": row.get("question") or row.get("user_input"),
                "expected_pdfs": sorted(expected_pdfs),
                "reason": "No citation or network context exposed a PDF identifier for this strict-grounding case.",
            })

    return {
        "checked_rows": checked_rows,
        "wrong_document_count": len(wrong_document_cases),
        "wrong_document_cases": wrong_document_cases,
        "unverifiable_count": len(unverifiable_cases),
        "unverifiable_cases": unverifiable_cases,
    }


def _write_csv_with_fallback(dataframe, target_path):
    try:
        dataframe.to_csv(target_path, index=False)
    except PermissionError:
        fallback_name = f"{target_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}{target_path.suffix}"
        dataframe.to_csv(target_path.with_name(fallback_name), index=False)


def _write_json_with_fallback(payload, target_path):
    serialized = json.dumps(payload, indent=2, ensure_ascii=False)
    try:
        target_path.write_text(serialized, encoding="utf-8")
    except PermissionError:
        fallback_name = f"{target_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}{target_path.suffix}"
        target_path.with_name(fallback_name).write_text(serialized, encoding="utf-8")


def _build_threshold_results(payload, run_timestamp):
    """
    Build threshold result rows with PASS/FAIL/SKIPPED, metric descriptions,
    direction, context requirements, and run timestamp.
    """
    thresholds = payload.get("thresholds", {})
    summary = payload.get("summary", {})
    executed_metrics = set(payload.get("executed_metrics", []))
    skipped_lookup = {s["metric"]: s["reason"] for s in payload.get("skipped_metrics", [])}
    metric_row_counts = payload.get("metric_row_counts", {})

    lower_is_better = {"noise_sensitivity_relevant", "noise_sensitivity_irrelevant"}

    results = []
    for metric_name, threshold_value in thresholds.items():
        is_executed = metric_name in executed_metrics
        avg_score = summary.get(metric_name)
        rows_evaluated = metric_row_counts.get(metric_name, 0)
        skip_reason = skipped_lookup.get(metric_name, "")

        meta = METRIC_METADATA.get(metric_name, {})
        what_it_measures = meta.get("what_it_measures", "")
        direction = meta.get("direction", "")
        requires_contexts = meta.get("requires_contexts", False)

        if metric_name in lower_is_better:
            operator = "<="
        else:
            operator = ">="

        if not is_executed:
            pass_fail = "SKIPPED"
        elif avg_score is None:
            pass_fail = "SKIPPED"
        else:
            if metric_name in lower_is_better:
                pass_fail = "PASS" if avg_score <= threshold_value else "FAIL"
            else:
                pass_fail = "PASS" if avg_score >= threshold_value else "FAIL"

        results.append({
            "evaluator": metric_name,
            "what_it_measures": what_it_measures,
            "operator": operator,
            "threshold": threshold_value,
            "direction": direction,
            "executed": "YES" if is_executed else "NO",
            "pass_fail": pass_fail,
            "average_score": avg_score if avg_score is not None else "",
            "rows_evaluated": rows_evaluated,
            "requires_contexts": "YES" if requires_contexts else "NO",
            "skip_reason": skip_reason,
            "run_timestamp": run_timestamp,
        })

    return results


def run_ragas_evaluation(dataset, metrics_config=None, output_dir="artifacts/ragas"):
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
    response_correctness_threshold = float(
        metrics_config.get("response_correctness_threshold", os.getenv("RAGAS_RESPONSE_CORRECTNESS_THRESHOLD", "0.70"))
    )
    answer_completeness_threshold = float(
        metrics_config.get("answer_completeness_threshold", os.getenv("RAGAS_ANSWER_COMPLETENESS_THRESHOLD", "3.0"))
    )

    metrics_profile = get_metrics_profile()
    ragas_llm, ragas_embeddings, llm_issue, provider_meta = build_ragas_dependencies()
    if llm_issue:
        raise RuntimeError(f"LLM/embedding provider is not ready: {llm_issue}")

    if ragas_embeddings is not None:
        ragas_embeddings = _AsyncEmbeddingAdapter(ragas_embeddings)

    metric_catalog = _build_ragas_metric_catalog(ragas_llm, ragas_embeddings)

    rows = _rows_from_dataset(dataset)
    dataset_size = len(rows)

    rows_for_answer_relevancy = [row for row in rows if not bool(row.get("expect_fallback", False))]
    rows_with_ground_truth = _filter_rows(rows, require_ground_truth=True)
    rows_with_contexts = _filter_rows(rows, require_contexts=True)
    rows_with_contexts_and_ground_truth = _filter_rows(rows, require_contexts=True, require_ground_truth=True)

    payload = {
        "dataset_size": dataset_size,
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
        "document_grounding_audit": _build_document_grounding_audit(Dataset.from_list(rows)),
    }

    def execute_metric(metric_name, eligible_rows, reason_if_empty):
        payload["metric_row_counts"][metric_name] = len(eligible_rows)
        if not eligible_rows:
            payload["skipped_metrics"].append({"metric": metric_name, "reason": reason_if_empty})
            return

        metric_object = metric_catalog.get(metric_name)
        if metric_object is None:
            raise RuntimeError(
                f"Metric '{metric_name}' is not available in the installed RAGAS version. "
                "Install missing ragas extras or update the ragas package."
            )

        eligible_dataset = Dataset.from_list(eligible_rows)

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
            timeout=int(os.getenv("RAGAS_TIMEOUT_SECONDS", "180")),
            max_retries=int(os.getenv("RAGAS_MAX_RETRIES", "2")),
            max_wait=int(os.getenv("RAGAS_MAX_WAIT_SECONDS", "20")),
            max_workers=int(os.getenv("RAGAS_MAX_WORKERS", "1" if provider in {"ollama", "gemini"} else "2")),
        )

        eval_kwargs = dict(
            dataset=eligible_dataset,
            metrics=[metric_object],
            llm=ragas_llm,
            embeddings=ragas_embeddings,
            run_config=run_config,
            raise_exceptions=True,
            show_progress=False,
            batch_size=int(os.getenv("RAGAS_BATCH_SIZE", "1")),
            experiment_name=f"ui_chatbot_{metric_name}",
        )

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            evaluation_result = pool.submit(evaluate, **eval_kwargs).result(
                timeout=int(os.getenv("RAGAS_THREAD_TIMEOUT_SECONDS", "600"))
            )

        result_df = evaluation_result.to_pandas()

        if metric_name not in result_df.columns:
            mode_match = next((c for c in result_df.columns if c.startswith(f"{metric_name}(mode=")), None)
            natural_name = getattr(metric_object, "name", None)
            if mode_match:
                result_df = result_df.rename(columns={mode_match: metric_name})
            elif natural_name and natural_name != metric_name and natural_name in result_df.columns:
                result_df = result_df.rename(columns={natural_name: metric_name})
            else:
                raise RuntimeError(
                    f"Metric '{metric_name}' result column was missing from RAGAS output. "
                    f"Available columns: {list(result_df.columns)}"
                )

        valid_scores = result_df[metric_name].dropna()
        if valid_scores.empty:
            raise RuntimeError(
                f"Metric '{metric_name}' returned no valid scores. "
                "This indicates evaluator quota exhaustion or provider errors."
            )

        metric_rows = result_df.to_dict(orient="records")
        if not metric_rows:
            raise RuntimeError(f"Metric '{metric_name}' produced no output rows after evaluation.")

        payload["executed_metrics"].append(metric_name)
        payload["metric_details"][metric_name] = metric_rows
        payload["summary"][metric_name] = round(float(valid_scores.mean()), 4)

    execute_metric("answer_relevancy", rows_for_answer_relevancy, "No in-scope rows were available for answer relevancy evaluation.")
    execute_metric("answer_accuracy", rows_with_ground_truth, "Answer accuracy requires a reference/ground-truth answer.")
    execute_metric("faithfulness", rows_with_contexts, "No contexts/citations were captured from UI or network.")
    execute_metric("context_precision", rows_with_contexts_and_ground_truth, "Context precision requires both retrieved contexts and a reference/ground-truth answer.")
    execute_metric("context_utilization", rows_with_contexts, "Context utilization requires retrieved contexts plus the generated response.")
    execute_metric("context_recall", rows_with_contexts_and_ground_truth, "Context recall requires both retrieved contexts and a reference/ground-truth answer.")
    execute_metric("context_relevance", rows_with_contexts, "Context relevance requires retrieved contexts plus the user input.")
    execute_metric("response_groundedness", rows_with_contexts, "Response groundedness requires a response and retrieved contexts.")
    execute_metric("context_entity_recall", rows_with_contexts_and_ground_truth, "Context entity recall requires retrieved contexts and a reference/ground-truth answer with entities to compare.")
    execute_metric("noise_sensitivity_relevant", rows_with_contexts_and_ground_truth, "Noise sensitivity requires user_input, response, reference, and retrieved contexts.")
    execute_metric("noise_sensitivity_irrelevant", rows_with_contexts_and_ground_truth, "Noise sensitivity requires user_input, response, reference, and retrieved contexts.")
    execute_metric("response_correctness", rows_with_ground_truth, "Response correctness requires a reference/ground-truth answer.")
    execute_metric("answer_completeness", rows_for_answer_relevancy, "No in-scope rows were available for answer completeness evaluation.")

    # Single run timestamp for entire report
    run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Build threshold results with PASS/FAIL/SKIPPED + metadata + timestamp
    payload["threshold_results"] = _build_threshold_results(payload, run_timestamp)

    # Combine per-metric row results into unified rows
    combined_rows = {}
    for metric_name, metric_rows in payload["metric_details"].items():
        for index, row in enumerate(metric_rows):
            row_id = str(row.get("id") or row.get("question") or row.get("user_input") or f"{metric_name}_{index}")
            combined_rows.setdefault(row_id, {
                "id": row.get("id"),
                "question": row.get("question") or row.get("user_input"),
            })
            combined_rows[row_id][metric_name] = row.get(metric_name)

    payload["rows"] = list(combined_rows.values())

    # Enrich rows: skip notes, context status, PASS/FAIL per cell, timestamp
    all_skipped_metric_names = [s["metric"] for s in payload["skipped_metrics"]]
    thresholds = payload["thresholds"]
    lower_is_better = {"noise_sensitivity_relevant", "noise_sensitivity_irrelevant"}

    for row in payload["rows"]:
        row_id = row.get("id") or row.get("question") or ""
        original_row = next((r for r in rows if (r.get("id") or r.get("question") or "") == row_id), {})
        has_contexts = bool(original_row.get("contexts") or original_row.get("retrieved_contexts"))
        has_ground_truth = bool(original_row.get("ground_truth") or original_row.get("reference"))

        # Per-row PASS/FAIL for each executed metric
        for metric_name in payload["executed_metrics"]:
            score = row.get(metric_name)
            if score is not None and isinstance(score, (int, float)):
                thresh = thresholds.get(metric_name)
                if thresh is not None:
                    if metric_name in lower_is_better:
                        row[f"{metric_name}_result"] = "PASS" if score <= thresh else "FAIL"
                    else:
                        row[f"{metric_name}_result"] = "PASS" if score >= thresh else "FAIL"

        # Mark skipped metric columns as "SKIPPED"
        for skipped_metric in all_skipped_metric_names:
            if skipped_metric not in row or row[skipped_metric] is None:
                row[skipped_metric] = "SKIPPED"
                row[f"{skipped_metric}_result"] = "SKIPPED"

        # Context and ground truth flags
        row["has_contexts"] = has_contexts
        row["has_ground_truth"] = has_ground_truth

        # Skip reason note
        if not has_contexts and not has_ground_truth:
            row["skipped_metrics_notes"] = (
                "No retrieved contexts or ground truth available for this row. "
                "Foundry agent did not expose citation chunks. "
                "Context-based and reference-based metrics cannot be computed."
            )
        elif not has_contexts:
            row["skipped_metrics_notes"] = (
                "No retrieved contexts available. "
                "Foundry agent did not return citation chunks for this query. "
                "Context-based metrics (faithfulness, context_precision, context_recall, etc.) skipped."
            )
        elif not has_ground_truth:
            row["skipped_metrics_notes"] = (
                "No ground truth / reference answer available. "
                "Reference-based metrics (answer_accuracy, context_precision, context_recall, etc.) skipped."
            )
        else:
            row["skipped_metrics_notes"] = "All applicable metrics executed for this row."

        # Timestamp at the very end
        row["run_timestamp"] = run_timestamp

    # Build DataFrame with controlled column order
    if payload["rows"]:
        all_metric_names = list(thresholds.keys())
        ordered_columns = ["id", "question"]
        for m in all_metric_names:
            ordered_columns.append(m)
            ordered_columns.append(f"{m}_result")
        ordered_columns.extend(["has_contexts", "has_ground_truth", "skipped_metrics_notes", "run_timestamp"])

        results_df = pd.DataFrame(payload["rows"])
        final_columns = [c for c in ordered_columns if c in results_df.columns]
        results_df = results_df[final_columns]
    else:
        results_df = pd.DataFrame(rows)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    _write_csv_with_fallback(results_df, output_path / "ragas_results.csv")
    _write_csv_with_fallback(results_df, output_path / f"ragas_results_{timestamp}.csv")
    _write_json_with_fallback(payload, output_path / "ragas_results.json")
    _write_json_with_fallback(payload, output_path / f"ragas_results_{timestamp}.json")

    # Threshold summary CSV with PASS/FAIL/SKIPPED + metadata + timestamp
    threshold_df = pd.DataFrame(payload["threshold_results"])
    _write_csv_with_fallback(threshold_df, output_path / "threshold_results.csv")

    payload["enterprise_reporting"] = create_enterprise_reporting_assets(
        PROJECT_ROOT,
        ragas_results=payload,
        report_mode="bridge",
    )
    _write_json_with_fallback(payload, output_path / "ragas_results.json")

    return payload