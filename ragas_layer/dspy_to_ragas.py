from __future__ import annotations

from typing import Any

from datasets import Dataset


def convert_dspy_predictions_to_ragas_dataset(dspy_results: dict[str, Any] | list[dict[str, Any]]) -> Dataset:
    """Map DSPy-normalized results into a RAGAS-compatible Hugging Face dataset."""
    rows = dspy_results.get("results", []) if isinstance(dspy_results, dict) else dspy_results

    ragas_rows: list[dict[str, Any]] = []
    for row in rows:
        ground_truths = row.get("ground_truths") or []
        if isinstance(ground_truths, str):
            ground_truths = [ground_truths]

        contexts = row.get("contexts") or []
        if isinstance(contexts, str):
            contexts = [contexts]

        final_answer = row.get("normalized_answer") or row.get("answer", "")
        final_question = row.get("question", "")
        reference = ground_truths[0] if ground_truths else ""

        ragas_rows.append(
            {
                "id": row.get("id"),
                "question": final_question,
                "user_input": final_question,
                "answer": final_answer,
                "response": final_answer,
                "contexts": contexts,
                "retrieved_contexts": contexts,
                "ground_truths": ground_truths,
                "ground_truth": reference,
                "reference": reference,
                "expect_fallback": row.get("expect_fallback", False),
                "expected_pdfs": row.get("expected_pdfs", []),
                "matched_pdfs": row.get("matched_pdfs", []),
                "strict_grounding": row.get("strict_grounding", False),
                "source_match_status": row.get("source_match_status", "not_applicable"),
            }
        )

    return Dataset.from_list(ragas_rows)
