import sys
sys.path.insert(0, '.')
from app.llm.client import OllamaLLMClient, DEFAULT_MODEL, DEFAULT_HOST

print(f"Model: '{DEFAULT_MODEL}'")
print(f"Host:  '{DEFAULT_HOST}'")

client = OllamaLLMClient()
result = client.answer_query(
    user_query="should i go the gym right now?",
    current_live_state="Gymnasium: 102.0% (overflow), Indoor Sports Complex: 86.7% (full), Main Library: 59.0% (moderate)",
    historical_context="- Gymnasium Tuesday 2023-09-12 -- Student report: super crowded in Gymnasium right now\n- 2023-09-05, Gymnasium: occupancy peaked at 90.0% (observed) / 100.0% (true demand) around 17:45."
)

print(f"\nResponse:\n{result}")
is_fallback = result.startswith("Answer for query") or result.startswith("Sorry,")
print(f"\nIs fallback/error string: {is_fallback}")
assert not is_fallback, "Still getting fallback — fix did not work"
print("PASS: real LLM response received")
