import json
d = json.loads(open('data/ragas_eval_dataset.json', encoding='utf-8').read())
for i, row in enumerate(d[:3]):
    ctx = row.get('contexts') or []
    ret_ctx = row.get('retrieved_contexts') or []
    gt = row.get('ground_truth') or ''
    ref = row.get('reference') or ''
    print(f'Row {i}:')
    print(f'  contexts: {len(ctx)} items, type: {type(ctx[0]) if ctx else "N/A"}')
    print(f'  retrieved_contexts: {len(ret_ctx)} items')
    print(f'  ground_truth: {gt[:60] if gt else "EMPTY"}')
    print(f'  reference: {ref[:60] if ref else "EMPTY"}')
    print(f'  contexts is list of strings: {isinstance(ctx[0], str) if ctx else False}')
