"""
🔍 SWAGGER API FULL DUMP SCRIPT (FINAL DEBUG VERSION)
✅ Handles ANY dataset structure
✅ Never silently skips
✅ Prints input row for debugging
"""

import json
import argparse
from pathlib import Path
import requests


API_URL = "https://playreadyai-api-dev.azurewebsites.net/api/chat"


def call_swagger_api(prompt: str):
    payload = {
        "prompt": prompt,
        "agentKey": "Public"
    }

    response = requests.post(
        API_URL,
        json=payload,
        headers={"Content-Type": "application/json"}
    )

    if response.status_code != 200:
        print(f"❌ API Error: {response.text}")
        return {}

    return response.json()


def extract_data(api_response):
    result = api_response.get("result", {})
    return {
        "answer": result.get("answer"),
        "retrieved_chunks": result.get("retrievedChunks", [])
    }


def extract_question(case):
    # ✅ Try all possible keys
    for key in ["question", "user_input", "query", "prompt", "input"]:
        if case.get(key):
            return case.get(key)

    # ✅ Fallback: print whole case for debugging
    print("❌ Could not find question in this row:")
    print(json.dumps(case, indent=2))

    return None


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--input", default="data/test_cases_positive.json")
    parser.add_argument("--limit", type=int, default=5)

    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    data = data[:args.limit]

    output = []

    for i, case in enumerate(data, 1):

        question = extract_question(case)

        if not question:
            print(f"⚠️ Skipping [{i}] — no usable question found")
            continue

        print(f"\n🔍 [{i}/{len(data)}] {question}")

        raw = call_swagger_api(question)
        extracted = extract_data(raw)

        output.append({
            "id": case.get("id"),
            "question": question,
            "answer": extracted["answer"],
            "retrieved_chunks": extracted["retrieved_chunks"]
        })

    # ✅ Save output
    output_path = Path("debug/swagger_full_dump.json")
    output_path.parent.mkdir(exist_ok=True)

    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(f"\n✅ Saved: {output_path}")


if __name__ == "__main__":
    main()