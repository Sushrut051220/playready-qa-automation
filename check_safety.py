import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path('.env'), override=True)
from azure.identity import DefaultAzureCredential
from azure.ai.evaluation import ViolenceEvaluator

credential = DefaultAzureCredential()
azure_ai_project = os.environ.get("FOUNDRY_PROJECT_ENDPOINT", "").strip()
print(f"Project: {azure_ai_project[:60]}...")

eval = ViolenceEvaluator(credential=credential, azure_ai_project=azure_ai_project)
result = eval(query="What is PlayReady?", response="PlayReady is a DRM technology by Microsoft.")
print(f"Result type: {type(result)}")
print(f"Result: {result}")
print(f"Keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
