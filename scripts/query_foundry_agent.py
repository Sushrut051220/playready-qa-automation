"""
query_foundry_agent.py
======================
Bridge between the generated test cases and the Foundry agent.

What it does
------------
1. Reads test cases from data/test_cases.json (or --input path).
   Each case must have a "prompt" field.
   Cases produced by generate_ragas_testset.py also have "reference_contexts"
   and "ground_truth" — those are preserved as-is.

2. For every test case, sends the prompt directly to the Foundry agent
    (asst_VOH7AQlko6afXHWZczUGpNgf / Agent279) using the Azure AI Agents runtime SDK.
   This is the SAME agent that PlayreadyAi.Api / ChatController.cs calls —
   so the answer is guaranteed to come from the Foundry agent, not a proxy.

3. Collects:
   - answer        : the agent's text response
    - citations     : file-citation annotations returned by the agent thread
    - citation_quotes: quoted passages attached to file citations when available
   - agent_id      : confirms which agent responded
   - thread_id     : Foundry thread ID for audit trail

4. Writes a RAGAS-ready JSON to --output (default: data/ragas_eval_dataset.json).
    Each row has: question, answer, contexts, ground_truth, reference_contexts,
    agent_id, thread_id, citations, citation_quotes.

   With contexts populated from reference_contexts (PDF chunks from the
   generator), ALL 8 RAGAS evaluators can run — faithfulness, context_precision,
   context_recall, context_utilization, context_entity_recall,
   noise_sensitivity, answer_relevancy, answer_accuracy.

Usage
-----
    python scripts/query_foundry_agent.py
    python scripts/query_foundry_agent.py --input data/test_cases.json --output data/ragas_eval_dataset.json
    python scripts/query_foundry_agent.py --limit 5   # smoke test first 5 cases
    python scripts/query_foundry_agent.py --delay 2   # 2 s between calls

Environment variables required (.env)
--------------------------------------
    FOUNDRY_PROJECT_ENDPOINT  — e.g. https://dev-playready-fdry-public.services.ai.azure.com/api/projects/dev-playready-fdry-public-proj
    FOUNDRY_AGENT_ID          — e.g. asst_VOH7AQlko6afXHWZczUGpNgf
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env", override=False)


def _build_agent_client():
    """Return an (AgentsClient, agent_id) pair using DefaultAzureCredential."""
    from azure.ai.agents import AgentsClient
    from azure.identity import DefaultAzureCredential

    endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT", "").strip()
    agent_id = os.environ.get("FOUNDRY_AGENT_ID", "").strip()

    if not endpoint:
        raise ValueError("FOUNDRY_PROJECT_ENDPOINT is not set in .env")
    if not agent_id:
        raise ValueError("FOUNDRY_AGENT_ID is not set in .env")

    credential = DefaultAzureCredential()
    client = AgentsClient(endpoint=endpoint, credential=credential)
    return client, agent_id


def _query_agent(client, agent_id: str, question: str) -> dict:
    """
    Send one question to the Foundry agent and return a dict with:
      answer, citations, thread_id, agent_id
    """
    from azure.ai.agents.models import AgentThreadCreationOptions, ThreadMessageOptions

    thread_options = AgentThreadCreationOptions(
        messages=[ThreadMessageOptions(role="user", content=question)]
    )

    # Create a fresh thread and run for each question (stateless evaluation)
    run = client.create_thread_and_process_run(
        agent_id=agent_id,
        thread=thread_options,
        polling_interval=1,
    )
    thread_id = run.thread_id

    if run.status != "completed":
        return {
            "answer": f"[AGENT RUN FAILED: status={run.status}]",
            "citations": [],
            "citation_quotes": [],
            "thread_id": thread_id,
            "agent_id": agent_id,
            "run_status": run.status,
        }

    # Retrieve messages — last assistant message is the answer
    messages = client.messages.list(thread_id=thread_id, run_id=run.id, order="desc", limit=20)
    answer_text = ""
    citations: list[dict] = []
    citation_quotes: list[str] = []

    for msg in messages:
        if msg.role != "assistant":
            continue
        for block in (msg.content or []):
            if getattr(block, "type", "") != "text" or not hasattr(block, "text"):
                continue

            text_val = block.text
            answer_text += getattr(text_val, "value", str(text_val))

            for annotation in getattr(text_val, "annotations", []) or []:
                if getattr(annotation, "type", "") != "file_citation":
                    continue

                fc = getattr(annotation, "file_citation", None)
                if not fc:
                    continue

                file_id = getattr(fc, "file_id", "") or ""
                quote = getattr(fc, "quote", "") or ""
                citation_text = getattr(annotation, "text", "") or ""

                citations.append(
                    {
                        "file_id": file_id,
                        "quote": quote,
                        "text": citation_text,
                    }
                )
                if quote:
                    citation_quotes.append(quote)
        break  # only need the most recent assistant message

    return {
        "answer": answer_text.strip(),
        "citations": citations,
        "citation_quotes": citation_quotes,
        "thread_id": thread_id,
        "agent_id": agent_id,
        "run_status": run.status,
    }


def run(
    input_path: Path,
    output_path: Path,
    limit: int | None,
    delay: float,
) -> None:
    print(f"Loading test cases from: {input_path}")
    raw_cases: list[dict] = json.loads(input_path.read_text(encoding="utf-8-sig"))

    if not isinstance(raw_cases, list) or not raw_cases:
        print("ERROR: input file is empty or not a JSON array.")
        sys.exit(1)

    if limit:
        raw_cases = raw_cases[:limit]
        print(f"  Limiting to first {limit} cases.")

    print(f"  {len(raw_cases)} test cases to process.")
    print()

    client, agent_id = _build_agent_client()
    print(f"Foundry agent ID : {agent_id}")
    print(f"Project endpoint : {os.environ.get('FOUNDRY_PROJECT_ENDPOINT')}")
    print()

    output_rows: list[dict] = []

    for index, case in enumerate(raw_cases, start=1):
        question = (case.get("prompt") or "").strip()
        if not question:
            print(f"  [{index}/{len(raw_cases)}] SKIP — no prompt field")
            continue

        print(f"  [{index}/{len(raw_cases)}] {question[:80]}...")

        try:
            result = _query_agent(client, agent_id, question)
        except Exception as exc:
            print(f"    ERROR: {exc}")
            result = {
                "answer": f"[ERROR: {exc}]",
                "citations": [],
                "thread_id": "",
                "agent_id": agent_id,
                "run_status": "error",
            }

        # reference_contexts come from generate_ragas_testset.py (PDF chunks).
        # These become the "contexts" field for RAGAS context evaluators.
        reference_contexts: list[str] = list(case.get("reference_contexts") or [])

        # If no generated PDF chunks, fall back to quoted citation passages.
        # These are better than file-level citations because they preserve text evidence,
        # but they are still limited to whatever the agent runtime exposes.
        contexts = reference_contexts if reference_contexts else result["citation_quotes"]

        output_rows.append(
            {
                # RAGAS required fields
                "id": case.get("id", f"case_{index:03d}"),
                "question": question,
                "user_input": question,
                "answer": result["answer"],
                "response": result["answer"],
                "contexts": contexts,
                "retrieved_contexts": contexts,
                "ground_truth": case.get("ground_truth", ""),
                "reference": case.get("ground_truth", ""),
                # Provenance — proves this came from the Foundry agent directly
                "agent_id": result["agent_id"],
                "thread_id": result["thread_id"],
                "run_status": result["run_status"],
                "agent_citations": result["citations"],
                "agent_citation_quotes": result["citation_quotes"],
                # Pass-through fields from test case
                "expected_pdfs": case.get("expected_pdfs", []),
                "strict_grounding": case.get("strict_grounding", False),
                "expect_fallback": case.get("expect_fallback", False),
                "paraphrase_group": case.get("paraphrase_group", ""),
                "query_type": case.get("query_type", ""),
            }
        )

        print(f"    answer ({len(result['answer'])} chars)  "
              f"citations={len(result['citations'])}  "
              f"quotes={len(result['citation_quotes'])}  "
              f"contexts={len(contexts)}  "
              f"thread={result['thread_id']}")

        if delay > 0 and index < len(raw_cases):
            time.sleep(delay)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output_rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print()
    print(f"Wrote {len(output_rows)} rows → {output_path}")
    print()

    # Summary
    answered = sum(1 for r in output_rows if r["answer"] and not r["answer"].startswith("["))
    with_contexts = sum(1 for r in output_rows if r["contexts"])
    print(f"  answered        : {answered}/{len(output_rows)}")
    print(f"  with contexts   : {with_contexts}/{len(output_rows)}  ← these rows run all 8 RAGAS evaluators")
    print(f"  without contexts: {len(output_rows) - with_contexts}/{len(output_rows)}  ← these run answer_relevancy + answer_accuracy only")


def main() -> None:
    parser = argparse.ArgumentParser(description="Query Foundry agent for every test case and produce a RAGAS-ready dataset.")
    parser.add_argument("--input", default=str(PROJECT_ROOT / "data" / "test_cases.json"), help="Input test cases JSON")
    parser.add_argument("--output", default=str(PROJECT_ROOT / "data" / "ragas_eval_dataset.json"), help="Output RAGAS dataset JSON")
    parser.add_argument("--limit", type=int, default=0, help="Only process first N cases (0 = all)")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds to wait between agent calls (default 1.0)")
    args = parser.parse_args()

    run(
        input_path=Path(args.input),
        output_path=Path(args.output),
        limit=args.limit if args.limit > 0 else None,
        delay=args.delay,
    )


if __name__ == "__main__":
    main()
