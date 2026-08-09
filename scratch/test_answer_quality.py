import sys
sys.path.insert(0, '.')
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

queries = [
    ("is it good if i go to gym right now?", "u_0042"),
    ("should i go to the library now?", "u_0042"),
    ("how crowded is the cafeteria?", None),
    ("which places are free right now?", None),
]

for query, user_id in queries:
    payload = {"query": query}
    if user_id:
        payload["user_id"] = user_id
    r = client.post("/api/ask", json=payload)
    d = r.json()
    print(f"\nQ: {query}")
    print(f"   Prompt state sent: {d.get('live_state_summary', '')[:120]}")
    print(f"   Answer: {d.get('answer','')}")
    print(f"   Engine: {d.get('engine')} | Fallback: {d.get('is_fallback')}")
    assert not d["answer"].startswith("Answer for query"), "Dummy template returned!"
    assert not d["answer"].startswith("Sorry,"), "Error string returned!"
