import json
r = json.loads(open('artifacts/ragas/ragas_results.json', encoding='utf-8').read())
print('Executed:', r.get('executed_metrics', []))
print()
print('Skipped:')
for s in r.get('skipped_metrics', []):
    print(f"  {s['metric']}: {s['reason'][:100]}")
