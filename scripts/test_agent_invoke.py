import os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(".env"), override=True)
if "AZURE_OPENAI_API_KEY" in os.environ:
    del os.environ["AZURE_OPENAI_API_KEY"]

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.core.credentials import AccessToken
import json

endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
project = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())

# Explore .agents methods
print("=== Methods on project.agents ===")
for m in dir(project.agents):
    if not m.startswith("_"):
        print(f"  {m}")

# Get the version object - explore its methods
print("\n=== Get agent version object ===")
version = project.agents.get_version("qa-test", "37")
print(f"Type: {type(version).__name__}")
print(f"\nMethods on version object:")
for m in dir(version):
    if not m.startswith("_") and not m in ("from_dict", "as_dict", "items", "keys", "values", "get", "update", "copy"):
        print(f"  {m}")

# Try send_request directly to invoke endpoints
print("\n=== Try project.send_request to invoke agent ===")
print("Trying: POST /agents/qa-test/versions/37/run")
try:
    from azure.core.rest import HttpRequest
    req = HttpRequest(
        method="POST",
        url=f"{endpoint}/agents/qa-test/versions/37/run?api-version=2025-05-15-preview",
        json={"input": "What is PlayReady?"},
    )
    resp = project.send_request(req)
    print(f"Status: {resp.status_code}")
    print(f"Body: {resp.text()[:500]}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {str(e)[:300]}")

# Also try beta API
print("\n=== Methods on project.beta ===")
for m in dir(project.beta):
    if not m.startswith("_"):
        print(f"  {m}")
