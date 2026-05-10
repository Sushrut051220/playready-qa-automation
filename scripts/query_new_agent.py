"""
Query the NEW Foundry agent (DevAgent:47) and produce RAGAS-ready dataset.
Drop-in replacement for query_foundry_agent.py with same output schema.
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from langsmith import traceable

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=True)
os.environ.pop("AZURE_OPENAI_API_KEY", None)

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient


def _build_client():
    endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
    project_client = AIProjectClient(
        endpoint=endpoint,
        credential=DefaultAzureCredential(),
    )
    openai_client = project_client.get_openai_client()
    agent_name = os.environ.get("FOUNDRY_AGENT_NAME", "DevAgent")
    agent_version = os.environ.get("FOUNDRY_AGENT_VERSION", "47")
    return openai_client, agent_name, agent_version


@traceable(
    name="NewAgent-Query",
    tags=["foundry", "rag", "playready"],
    metadata={"component": "agent_call"}
)
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
            "contexts": [],
            "thread_id": "",
            "agent_id": f"{agent_name}:{agent_version}",
            "run_status": "failed",
            "latency_seconds": round(time.time() - start_time, 2),
            "token_usage": {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0},
        }

    latency = round(time.time() - start_time, 2)

    # Token usage
    usage = response.usage
    token_usage = {
        "total_tokens": getattr(usage, "total_tokens", 0),
        "prompt_tokens": getattr(usage, "input_tokens", 0),
        "completion_tokens": getattr(usage, "output_tokens", 0),
    }

    # Extract answer + citations + contexts
    answer_text = ""
    citations = []
    citation_quotes = []
    contexts = []

    for item in response.output or []:
        item_type = getattr(item, "type", "")

        # Search call outputs = our contexts (chunks are in model_extra["output"] as JSON string)
        if item_type == "azure_ai_search_call_output":
            extra = getattr(item, "model_extra", None) or {}
            output_str = extra.get("output", "")
            if output_str:
                try:
                    import json as _json
                    parsed = _json.loads(output_str)
                    docs = parsed.get("documents", [])
                    for doc in docs:
                        chunk_text = doc.get("content", "")
                        if chunk_text:
                            contexts.append(chunk_text)
                except Exception:
                    if output_str:
                        contexts.append(output_str[:3000])

        # Assistant message = our answer
        elif item_type == "message":
            for content_item in (getattr(item, "content", []) or []):
                if getattr(content_item, "type", "") == "output_text" or hasattr(content_item, "text"):
                    answer_text += getattr(content_item, "text", "")
                    for ann in getattr(content_item, "annotations", []) or []:
                        ann_type = getattr(ann, "type", "")
                        if ann_type == "url_citation":
                            url = getattr(ann, "url", "")
                            title = getattr(ann, "title", "")
                            text = getattr(ann, "text", "") or ""
                            citations.append({
                                "type": "url_citation",
                                "url": url,
                                "title": title,
                                "text": text,
                                "start_index": getattr(ann, "start_index", 0),
                                "end_index": getattr(ann, "end_index", 0),
                            })
                            if title:
                                citation_quotes.append(title)

    return {
        "answer": answer_text,
        "citations": citations,
        "citation_quotes": citation_quotes,
        "contexts": contexts,
        "thread_id": "",
        "agent_id": f"{agent_name}:{agent_version}",
        "run_status": "completed",
        "latency_seconds": latency,
        "token_usage": token_usage,
    }



@traceable(
    name="NewAgent-Batch-Run",
    tags=["batch", "evaluation"],
    metadata={"type": "ragas_generation"}
)
def run(input_path: Path, output_path: Path, limit: int = 0, offset: int = 0, delay: float = 1.0) -> None:
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
        result = _query_agent(
    client,
    agent_name,
    agent_version,
    question,
    langsmith_extra={
        "metadata": {
            "test_case_id": case_id,
            "query_type": case.get("query_type", ""),
            "suite": input_path.name,
            "expected_behavior": case.get("expected_behavior", ""),
        }
    }
)
        print(f"    answer ({len(result['answer'])} chars)  "
              f"citations={len(result['citations'])}  "
              f"contexts={len(result['contexts'])}  "
              f"latency={result['latency_seconds']}s  "
              f"tokens={result['token_usage']['total_tokens']}")

        row = {
            "id": case_id,
            "question": question,
            "user_input": question,
            "answer": result["answer"],
            "response": result["answer"],
            "contexts": result["contexts"],
            "retrieved_contexts": result["contexts"],
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
    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {len(results)} rows -> {output_path}")

    answered = sum(1 for r in results if r["run_status"] == "completed")
    with_ctx = sum(1 for r in results if r["contexts"])
    print(f"\n  answered      : {answered}/{len(results)}")
    print(f"  with contexts : {with_ctx}/{len(results)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Query NEW Foundry agent (Responses API).")
    parser.add_argument("--input", default=str(PROJECT_ROOT / "data" / "test_cases.json"))
    parser.add_argument("--output", default=str(PROJECT_ROOT / "data" / "ragas_eval_dataset.json"))
    parser.add_argument("--limit", type=int, default=0, help="First N cases (0 = all)")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N (negative for last N)")
    parser.add_argument("--delay", type=float, default=1.0)
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
