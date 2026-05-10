import json
q = json.load(open('artifacts/foundry/foundry_quality.json'))
s = json.load(open('artifacts/foundry/foundry_safety.json'))
print('=== QUALITY ===')
print('Status:', q['status'], '| Rows:', q.get('rows_evaluated', 0))
if q.get('rows'):
    r = q['rows'][0]
    for k in ['coherence','fluency','relevance','groundedness','similarity']:
        print(f'  {k}:', r.get(k, 'MISSING'))
print()
print('=== SAFETY ===')
print('Status:', s['status'], '| Rows:', s.get('rows_evaluated', 0))
if s.get('rows'):
    r = s['rows'][0]
    for k in ['violence','sexual','self_harm','hate_unfairness']:
        print(f'  {k}:', r.get(k, 'MISSING'))
