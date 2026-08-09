import sys
sys.path.insert(0, '.')
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

schedule_queries = [
    "check my schedule and when can i find congestion",
    "what's my day looking like?",
    "when should i visit the gym based on my routine?",
    "show me my plan for today",
]

venue_queries = [
    "is it good if i go to gym right now?",
    "how crowded is the library?",
]

print("=== SCHEDULE QUERIES (should use Mode 3 / personalisation) ===")
for q in schedule_queries:
    r = client.post("/api/ask", json={"query": q, "user_id": "u_0042"})
    d = r.json()
    print(f"\nQ: {q}")
    print(f"   Sources: {d.get('sources')}")
    print(f"   Answer : {d.get('answer','')[:300]}")
    assert "Personalisation Engine" in str(d.get("sources")), \
        f"FAIL: should have used personalisation engine, got: {d.get('sources')}"
print("\n[ALL SCHEDULE QUERIES used personalisation engine]")

print("\n=== VENUE QUERIES (should use Mode 1 / RAG) ===")
for q in venue_queries:
    r = client.post("/api/ask", json={"query": q, "user_id": "u_0042"})
    d = r.json()
    print(f"\nQ: {q}")
    print(f"   Sources: {d.get('sources')}")
    print(f"   Answer : {d.get('answer','')[:200]}")
    assert "FAISS" in str(d.get("sources")), \
        f"FAIL: should have used FAISS/RAG, got: {d.get('sources')}"
print("\n[ALL VENUE QUERIES used RAG engine]")
