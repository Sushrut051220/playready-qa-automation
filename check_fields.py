import json
d = json.loads(open('data/ragas_eval_dataset.json', encoding='utf-8').read())
row = d[0]
print('Keys:', list(row.keys()))
print()
print('contexts:', bool(row.get('contexts')))
print('retrieved_contexts:', bool(row.get('retrieved_contexts')))
print('ground_truth:', bool(row.get('ground_truth')))
print('reference:', bool(row.get('reference')))
print('expected_pdfs:', bool(row.get('expected_pdfs')))
print('agent_citations:', row.get('agent_citations'))
print('agent_citation_quotes:', row.get('agent_citation_quotes'))
