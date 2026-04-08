from __future__ import annotations

import json
from pathlib import Path

import pytest

from audit.compliance_validator import run_compliance_audit


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.compliance
@pytest.mark.regression
def test_framework_compliance_audit() -> None:
    report = run_compliance_audit(PROJECT_ROOT)

    assert (PROJECT_ROOT / "artifacts" / "reports" / "compliance_audit.json").exists(), (
        "Compliance audit report was not created."
    )
    assert report["summary"]["failure_count"] == 0, json.dumps(report, indent=2)
