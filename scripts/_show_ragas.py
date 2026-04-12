import json, math

d = json.load(open("artifacts/ragas/ragas_results.json", encoding="utf-8"))

print("=" * 70)
print(f"  dataset_size   : {d['dataset_size']}")
print(f"  metrics_profile: {d['metrics_profile']}")
print(f"  provider       : {d['provider'].get('model','?')}")
print("=" * 70)

print("\n--- EXECUTED METRICS & SCORES ---")
for k, v in d["summary"].items():
    bar = int(v * 20) * "#" if isinstance(v, float) and not math.isnan(v) else "?"
    print(f"  {k:<35} {v:.4f}  [{bar:<20}]")

print("\n--- SKIPPED METRICS (why) ---")
for s in d["skipped_metrics"]:
    print(f"  [{s['metric']}]")
    print(f"    -> {s['reason']}")

print("\n--- PER-ROW SCORES (answer_accuracy) ---")
rows = d["metric_details"].get("answer_accuracy", [])
passed = 0
failed = 0
for r in rows:
    score = r.get("answer_accuracy")
    evaluated = "(evaluated)"
    label = "PASS" if isinstance(score, float) and score >= 0.7 else "FAIL"
    if label == "PASS":
        passed += 1
    else:
        failed += 1
    sid = str(r.get("id") or r.get("question") or "?")[:52]
    score_str = f"{score:.2f}" if isinstance(score, float) and not math.isnan(score) else " NaN"
    print(f"  {label}  {score_str}  {evaluated}  {sid}")

print(f"\n  PASS: {passed}  FAIL: {failed}  TOTAL: {len(rows)}")
print(f"  mean answer_accuracy: {d['summary'].get('answer_accuracy', 'N/A')}")
