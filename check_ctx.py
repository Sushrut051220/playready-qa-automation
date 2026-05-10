import json
d = json.loads(open('data/ragas_eval_dataset.json', encoding='utf-8').read())
for i, row in enumerate(d[:3]):
    ctx = row.get('contexts') or row.get('retrieved_contexts') or []
    print(f'Row {i}: contexts={len(ctx)} items')
    if ctx:
        print(f'  First context: {str(ctx[0])[:100]}')
    else:
        print('  EMPTY - no contexts!')
