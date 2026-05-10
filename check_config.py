from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path('.env'), override=True)
import os
print('AZURE_OPENAI_ENDPOINT:', os.environ.get('AZURE_OPENAI_ENDPOINT', 'NOT SET'))
print('AZURE_OPENAI_API_BASE:', os.environ.get('AZURE_OPENAI_API_BASE', 'NOT SET'))
print('OPENAI_API_BASE:', os.environ.get('OPENAI_API_BASE', 'NOT SET'))
print('AZURE_OPENAI_BASE_URL:', os.environ.get('AZURE_OPENAI_BASE_URL', 'NOT SET'))
print('AZURE_OPENAI_API_KEY:', os.environ.get('AZURE_OPENAI_API_KEY', 'NOT SET')[:20] if os.environ.get('AZURE_OPENAI_API_KEY') else 'NOT SET')
print('AZURE_OPENAI_CHAT_DEPLOYMENT:', os.environ.get('AZURE_OPENAI_CHAT_DEPLOYMENT', 'NOT SET'))
print('AZURE_OPENAI_API_VERSION:', os.environ.get('AZURE_OPENAI_API_VERSION', 'NOT SET'))
from foundry_layer.foundry_evaluator import _get_model_config
config = _get_model_config()
print('Config:', {k: v[:30] if isinstance(v,str) and len(v)>30 else v for k,v in config.items()})
