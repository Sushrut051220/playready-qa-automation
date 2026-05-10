import json
r = json.loads(open('artifacts/ragas/ragas_results.json', encoding='utf-8').read())
for row in r.get('rows', []):
    print('id:', row.get('id'))
    print('has_contexts:', row.get('has_contexts'))
    print('has_ground_truth:', row.get('has_ground_truth'))
    print('skipped_metrics_notes:', row.get('skipped_metrics_notes'))
