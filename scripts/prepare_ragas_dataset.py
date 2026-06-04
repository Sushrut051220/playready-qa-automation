"""
✅ PREPARE RAGAS DATASET FROM EXISTING DATA
✅ Uses retrieved_chunks already available
✅ Converts to RAGAS format
"""

import json
from pathlib import Path


INPUT_FILE = "data/your_file.json"
OUTPUT_FILE = "data/ragas_ready.json"


def extract_contexts(chunks):
    contexts = []

    for c in chunks:
        if c.get("content"):
            contexts.append(c["content"])

    return contexts


def main():
    data = json.loads(Path(INPUT_FILE).read_text(encoding="utf-8"))

    output = []

    for row in data:
        question = row.get("question")
        answer = row.get("answer") or ""
        chunks = row.get("retrieved_chunks", [])

        contexts = extract_contexts(chunks)

        output.append({
            "id": row.get("id"),
            "question": question,
            "answer": answer,
            "contexts": contexts,
            "ground_truth": ""
        })

    Path(OUTPUT_FILE).write_text(
        json.dumps(output, indent=2),
        encoding="utf-8"
    )

    print(f"✅ RAGAS dataset ready: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()