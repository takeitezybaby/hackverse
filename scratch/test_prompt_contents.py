import sys
sys.path.insert(0, '.')
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch
from app.llm import prompts

captured_prompt = {}

original_build = prompts.build_general_query_prompt
def capturing_build(user_query, current_live_state, historical_context=""):
    captured_prompt['live_state'] = current_live_state
    captured_prompt['context'] = historical_context
    return original_build(user_query, current_live_state, historical_context)

client = TestClient(app)

with patch.object(prompts, 'build_general_query_prompt', capturing_build):
    r = client.post("/api/ask", json={"query": "is it good if i go to gym right now?", "user_id": "u_0042"})

print("=== LIVE STATE SENT TO PROMPT ===")
print(captured_prompt.get('live_state', '(not captured)'))
print("\n=== HISTORICAL CONTEXT SENT TO PROMPT (first 300 chars) ===")
print(captured_prompt.get('context', '(not captured)')[:300])
print("\n=== FINAL ANSWER ===")
print(r.json().get('answer'))
