from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

cred = DefaultAzureCredential()
tp = get_bearer_token_provider(cred, "https://cognitiveservices.azure.com/.default")
client = AzureOpenAI(
    azure_endpoint="https://dev-playready-fdry-public.services.ai.azure.com",
    api_version="2024-08-01-preview",
    azure_ad_token_provider=tp,
)
r = client.chat.completions.create(
    model="gpt-4.1-mini",
    messages=[{"role": "user", "content": "say hi"}]
)
print(r.choices[0].message.content)
