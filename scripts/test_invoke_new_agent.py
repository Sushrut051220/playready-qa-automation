import os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(".env"), override=True)
if "AZURE_OPENAI_API_KEY" in os.environ:
    del os.environ["AZURE_OPENAI_API_KEY"]

from azure.identity import DefaultAzureCredential, get_bearer_token_provider

endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
print(f"Project endpoint: {endpoint}")

# Try the OpenAI Responses API pattern (newer Foundry agents)
try:
    from openai import AzureOpenAI
    base = endpoint.replace("/api/projects/dev-playready-fdry-public-proj", "")
    print(f"Trying Responses API at: {base}")
    
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default"
    )
    
    client = AzureOpenAI(
        azure_endpoint=base,
        azure_ad_token_provider=token_provider,
        api_version="2024-12-01-preview",
    )
    
    print("\n=== Trying responses.create ===")
    if hasattr(client, "responses"):
        print("client.responses EXISTS")
        print(dir(client.responses))
    else:
        print("No responses attr - trying chat completions")
    
    # Try chat completion with tools
    print("\n=== Test: chat.completions.create ===")
    resp = client.chat.completions.create(
        model="qa-test",
        messages=[{"role": "user", "content": "What is PlayReady?"}],
        max_tokens=200,
        extra_body={"agent_version": "38"},
    )
    print(f"Response: {resp.choices[0].message.content[:300]}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
