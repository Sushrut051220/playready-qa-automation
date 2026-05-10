from dotenv import load_dotenv
load_dotenv('.env', override=True)
from llm_provider import build_ragas_dependencies
ragas_llm, _, issue, meta = build_ragas_dependencies()
print('Issue:', issue)
print('Meta:', meta)
print('Type:', type(ragas_llm))
print('Model attr:', getattr(ragas_llm, 'model', 'NOT FOUND'))
print('Client:', type(getattr(ragas_llm, 'client', None)))
c = getattr(ragas_llm, 'client', None)
if c:
    print('Client model:', getattr(c, 'model', 'NOT FOUND'))
    print('Client _model:', getattr(c, '_model', 'NOT FOUND'))
