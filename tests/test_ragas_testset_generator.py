from __future__ import annotations

import json
from pathlib import Path

from scripts.generate_ragas_testset import build_seed_test_cases, write_output_file


def test_build_seed_test_cases_creates_expected_schema() -> None:
    registry = [
        {
            "pdf_id": "pdf_alpha",
            "pdf_name": "Alpha Guide.pdf",
            "topic": "alpha onboarding",
            "expected_keywords": ["alpha", "guide", "onboarding"],
            "sample_questions": [
                "What is Alpha onboarding?",
                "How do I start Alpha setup?",
            ],
        }
    ]

    cases = build_seed_test_cases(
        registry=registry,
        desired_count=2,
        fallback_patterns=["I don't know"],
        forbidden_patterns=["outside my scope"],
        strict_grounding=True,
    )

    assert len(cases) == 2
    assert cases[0]["expected_pdfs"] == ["pdf_alpha"]
    assert cases[0]["strict_grounding"] is True
    assert "prompt" in cases[0]
    assert "ground_truth" in cases[0]


def test_write_output_file_creates_json_and_backup(tmp_path: Path) -> None:
    output_path = tmp_path / "test_cases.json"
    output_path.write_text("[]", encoding="utf-8")
    archive_dir = tmp_path / "archive"

    payload = [{"id": "generated_001", "prompt": "Sample"}]
    write_output_file(payload, output_path=output_path, archive_dir=archive_dir)

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    backups = list(archive_dir.glob("*.json"))

    assert saved == payload
    assert backups
