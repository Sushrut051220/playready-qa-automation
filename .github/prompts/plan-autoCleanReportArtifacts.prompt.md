## Plan: Auto-Clean Report Artifacts

Implement automatic retention cleanup after each report generation so only the latest run is kept for enterprise report archives, plus only canonical files for DSPy/RAGAS outputs. This gives you one clear report set for both testing approaches.

**Steps**
1. Add retention cleanup helpers in [audit/reporting.py](audit/reporting.py) to delete old timestamped folders in [artifacts/reports](artifacts/reports), keeping only newest 1.
2. Invoke cleanup automatically inside [create_enterprise_reporting_assets](audit/reporting.py#L605) after each successful report build.
3. Add timestamped file cleanup in [artifacts/dspy](artifacts/dspy) and [artifacts/ragas](artifacts/ragas), while preserving canonical files:
- [artifacts/dspy/dspy_results.json](artifacts/dspy/dspy_results.json)
- [artifacts/dspy/dspy_score_summary.json](artifacts/dspy/dspy_score_summary.json)
- [artifacts/ragas/ragas_results.json](artifacts/ragas/ragas_results.json)
- [artifacts/ragas/ragas_cache.json](artifacts/ragas/ragas_cache.json)
4. Add env-configurable policy (default: keep 1, auto-clean enabled) so retention can be changed later without code changes.
5. Ensure the same cleanup path works for both approaches since both converge through [audit/reporting.py](audit/reporting.py#L605).
6. Update assertions in [tests/test_ragas_eval.py](tests/test_ragas_eval.py) for retention-aware behavior.
7. Verify by running report generation twice and confirming only one archive remains.

**Relevant files**
- [audit/reporting.py](audit/reporting.py)
- [tests/test_ragas_eval.py](tests/test_ragas_eval.py)
- [artifacts/reports](artifacts/reports)
- [artifacts/dspy](artifacts/dspy)
- [artifacts/ragas](artifacts/ragas)
- [reports/Latest_Report.xlsx](reports/Latest_Report.xlsx)

**Verification**
1. Run twice and check [artifacts/reports](artifacts/reports) has exactly one timestamped folder.
2. Confirm [reports/Latest_Report.xlsx](reports/Latest_Report.xlsx) exists and refreshes.
3. Confirm timestamped files are removed from [artifacts/dspy](artifacts/dspy) and [artifacts/ragas](artifacts/ragas), canonical files retained.
4. Run [tests/test_ragas_eval.py](tests/test_ragas_eval.py) and confirm pass.

**Locked decisions from your inputs**
- Keep latest 1 run.
- Auto-clean after every report generation.
- Clean timestamped artifacts in DSPy and RAGAS too.