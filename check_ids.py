import json
d = json.loads(open('data/ragas_eval_dataset.json', encoding='utf-8').read())
r = json.loads(open('artifacts/ragas/ragas_results.json', encoding='utf-8').read())
print('Dataset row IDs:', [row.get('id') for row in d])
print()
print('Result row IDs:', [row.get('id') for row in r.get('rows', [])])
print()
print('Combined row questions:', [row.get('question') for row in r.get('rows', [])])
