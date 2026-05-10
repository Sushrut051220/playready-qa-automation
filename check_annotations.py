import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path('.env'), override=True)
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import AgentThreadCreationOptions, ThreadMessageOptions
from azure.identity import DefaultAzureCredential

endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT", "").strip()
agent_id = os.environ.get("FOUNDRY_AGENT_ID", "").strip()
credential = DefaultAzureCredential()
client = AgentsClient(endpoint=endpoint, credential=credential)

thread_options = AgentThreadCreationOptions(
    messages=[ThreadMessageOptions(role="user", content="What is PlayReady?")]
)
run = client.create_thread_and_process_run(agent_id=agent_id, thread=thread_options, polling_interval=1)
print(f"Run status: {run.status}")

messages = client.messages.list(thread_id=run.thread_id, run_id=run.id, order="desc", limit=5)
for msg in messages:
    if msg.role != "assistant":
        continue
    for block in (msg.content or []):
        if getattr(block, "type", "") != "text":
            continue
        text_val = block.text
        print(f"Answer: {getattr(text_val, 'value', '')[:150]}")
        annotations = getattr(text_val, "annotations", []) or []
        print(f"Annotations count: {len(annotations)}")
        for ann in annotations:
            print(f"  Type: {getattr(ann, 'type', 'UNKNOWN')}")
            print(f"  Attrs: {[a for a in dir(ann) if not a.startswith('_')]}")
            print(f"  Repr: {repr(ann)[:300]}")
    break
