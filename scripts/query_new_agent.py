"""
Query the Foundry agent and produce a RAGAS-ready dataset.

Architecture (stable / old-style):
- Answer/response comes from the Foundry agent runtime
- Ground truth comes from the input test cases
- Contexts/retrieved_contexts come from reference_contexts in the input test cases
- Citations/citation quotes come from the agent response when available

This keeps RAGAS evaluation stable, because contexts do not depend on
live retrieval behavior from the agent.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=True)

# Force Entra ID / DefaultAzureCredential path if API key exists in env
os.environ.pop("AZURE_OPENAI_API_KEY", None)


def _build_client():
    endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]

    project_client = AIProjectClient(
        endpoint=endpoint,
        credential=DefaultAzureCredential(),
    )

    openai_client = project_client.get_openai_client()
    agent_name = os.environ.get("FOUNDRY_AGENT_NAME", "PublicAgent")
    agent_version = os.environ.get("FOUNDRY_AGENT_VERSION", "8")

    return openai_client, agent_name, agent_version


def _extract_answer_and_citations(response) -> tuple[str, list[dict], list[str]]:
    answer_text = ""
    citations: list[dict] = []
    citation_quotes: list[str] = []

    for item in (getattr(response, "output", None) or []):
        item_type = getattr(item, "type", "")

        if item_type != "message":
            continue

        for content_item in (getattr(item, "content", None) or []):
            text_value = getattr(content_item, "text", "") or ""
            if text_value:
                answer_text += text_value

            for ann in (getattr(content_item, "annotations", None) or []):
                ann_type = getattr(ann, "type", "")

                # Handle both url_citation and file_citation if present
                if ann_type in {"url_citation", "file_citation"}:
                    citation_entry = {
                        "type": ann_type,
                        "url": getattr(ann, "url", ""),
                        "title": getattr(ann, "title", ""),
                        "text": getattr(ann, "text", "") or "",
                        "file_id": getattr(ann, "file_id", ""),
                        "filename": getattr(ann, "filename", ""),
                        "start_index": getattr(ann, "start_index", 0),
                        "end_index": getattr(ann, "end_index", 0),
                    }
                    citations.append(citation_entry)

                    # Prefer title, then filename, then annotated text
                    quote = (
                        citation_entry["title"]
                        or citation_entry["filename"]
                        or citation_entry["text"]
                    )
                    if quote:
                        citation_quotes.append(quote)

    return answer_text, citations, citation_quotes


def _query_agent(client, agent_name: str, agent_version: str, question: str) -> dict:
    start_time = time.time()

    try:
        response = client.responses.create(
            input=[{"role": "user", "content": question}],
            extra_body={
                "agent_reference": {
                    "name": agent_name,
                    "version": agent_version,
                    "type": "agent_reference",
                }
            },
        )
    except Exception as e:
        return {
            "answer": f"[AGENT CALL FAILED: {type(e).__name__}: {str(e)[:200]}]",
            "citations": [],
            "citation_quotes": [],
            "thread_id": "",
            "agent_id": f"{agent_name}:{agent_version}",
            "run_status": "failed",
            "latency_seconds": round(time.time() - start_time, 2),
            "token_usage": {
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
            },
        }

    latency = round(time.time() - start_time, 2)

    usage = getattr(response, "usage", None)
    token_usage = {
        "total_tokens": getattr(usage, "total_tokens", 0),
        "prompt_tokens": getattr(usage, "input_tokens", 0),
        "completion_tokens": getattr(usage, "output_tokens", 0),
    }

    answer_text, citations, citation_quotes = _extract_answer_and_citations(response)

    return {
        "answer": answer_text,
        "citations": citations,
        "citation_quotes": citation_quotes,
        "thread_id": "",
        "agent_id": f"{agent_name}:{agent_version}",
        "run_status": "completed",
        "latency_seconds": latency,
        "token_usage": token_usage,
    }


def run(
    input_path: Path,
    output_path: Path,
    limit: int = 0,
    offset: int = 0,
    delay: float = 1.0,
) -> None:
    print(f"Loading test cases from: {input_path}")

    raw_cases = json.loads(input_path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw_cases, list) or not raw_cases:
        print("ERROR: input file is empty or not a JSON array.")
        sys.exit(1)

    if offset:
        if offset < 0:
            raw_cases = raw_cases[offset:]
            print(f"  Taking last {abs(offset)} cases.")
        else:
            raw_cases = raw_cases[offset:]
            print(f"  Skipping first {offset} cases.")

    if limit:
        raw_cases = raw_cases[:limit]
        print(f"  Limiting to {limit} cases.")

    print(f"  {len(raw_cases)} test cases to process.")

    client, agent_name, agent_version = _build_client()
    print(f"\nFoundry agent : {agent_name}:{agent_version}")
    print(f"Project       : {os.environ.get('FOUNDRY_PROJECT_ENDPOINT')}\n")

    results = []

    for i, case in enumerate(raw_cases, start=1):
        question = case.get("prompt") or case.get("question") or ""
        case_id = case.get("id", f"case_{i}")

        print(f"  [{i}/{len(raw_cases)}] {question[:80]}...")

        result = _query_agent(client, agent_name, agent_version, question)

        # Stable / old-style behavior:
        # contexts come from the test case's reference_contexts, not live agent retrieval
        contexts = case.get("reference_contexts", []) or []

        print(
            f"    answer ({len(result['answer'])} chars)  "
            f"citations={len(result['citations'])}  "
            f"contexts={len(contexts)}  "
            f"latency={result['latency_seconds']}s  "
            f"tokens={result['token_usage']['total_tokens']}"
        )

        row = {
            "id": case_id,
            "question": question,
            "user_input": question,
            "answer": result["answer"],
            "response": result["answer"],

            # IMPORTANT: use test-case reference_contexts for stable evaluation
            "contexts": contexts,
            "retrieved_contexts": contexts,

            "ground_truth": case.get("ground_truth", ""),
            "reference": case.get("ground_truth", ""),

            "agent_id": result["agent_id"],
            "thread_id": result["thread_id"],
            "run_status": result["run_status"],

            "agent_citations": result["citations"],
            "agent_citation_quotes": result["citation_quotes"],

            "expected_pdfs": case.get("expected_pdfs", []),
            "strict_grounding": case.get("strict_grounding", False),
            "expect_fallback": case.get("expect_fallback", False),
            "paraphrase_group": case.get("paraphrase_group", ""),
            "query_type": case.get("query_type", ""),

            "latency_seconds": result["latency_seconds"],
            "token_usage": result["token_usage"],

            "source_test_suite": input_path.name,
        }

        results.append(row)

        if delay and i < len(raw_cases):
            time.sleep(delay)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nWrote {len(results)} rows -> {output_path}")

    answered = sum(1 for r in results if r["run_status"] == "completed")
    with_ctx = sum(1 for r in results if r["contexts"])
    with_citations = sum(1 for r in results if r["agent_citations"])

    print(f"\n  answered      : {answered}/{len(results)}")
    print(f"  with contexts : {with_ctx}/{len(results)}")
    print(f"  with citations: {with_citations}/{len(results)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Query Foundry agent and produce a RAGAS-ready dataset."
    )
    parser.add_argument(
        "--input",
        default=str(PROJECT_ROOT / "data" / "test_cases.json"),
        help="Input test cases JSON",
    )
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "data" / "ragas_eval_dataset.json"),
        help="Output RAGAS dataset JSON",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Only process first N cases (0 = all)",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Skip first N cases (negative for last N)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds to wait between agent calls (default 1.0)",
    )

    args = parser.parse_args()

    run(
        input_path=Path(args.input),
        output_path=Path(args.output),
        limit=args.limit,
        offset=args.offset,
        delay=args.delay,
    )


if __name__ == "__main__":
    main()