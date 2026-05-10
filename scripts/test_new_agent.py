import os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(".env"), override=True)
if "AZURE_OPENAI_API_KEY" in os.environ:
    del os.environ["AZURE_OPENAI_API_KEY"]

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
client = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())

# Get the new agent version
print("=== Fetching qa-test:37 ===")
agent = client.agents.get_version("qa-test", "37")
print(f"ID: {agent.id}")
print(f"Name: {agent.name}")
print(f"Version: {agent.version}")
print(f"Description: {agent.description}")
print(f"\n=== Definition ===")
defn = agent.definition
print(f"Kind: {getattr(defn, 'kind', 'N/A')}")
print(f"Model: {getattr(defn, 'model', 'N/A')}")
print(f"\n=== Full attributes ===")
for attr in dir(defn):
    if not attr.startswith("_"):
        try:
            val = getattr(defn, attr)
            if not callable(val):
                print(f"  {attr}: {str(val)[:200]}")
        except Exception:
            pass

print(f"\n=== Tools / Capabilities ===")
for attr in ["tools", "tool_resources", "instructions", "knowledge_base", "data_sources"]:
    val = getattr(defn, attr, None)
    if val:
        print(f"  {attr}: {str(val)[:300]}")

print(f"\n=== Available client.agents methods for invoke ===")
methods = [m for m in dir(client.agents) if not m.startswith("_") and callable(getattr(client.agents, m))]
print(methods)
