import sys
sys.path.insert(0, '.')
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

cases = [
    # Venue + timing → Mode 1 (FAISS + forecast slots)
    ("when should i go to the library",      "u_0042", "FAISS"),
    ("when should i go to the gym",          "u_0042", "FAISS"),
    ("at what time should i go to library",  "u_0042", "FAISS"),
    ("what is the best time for the gym",    "u_0042", "FAISS"),
    ("when is the cafeteria least crowded",  None,     "FAISS"),
    # No venue + schedule intent → Mode 3 (Personalisation)
    ("check my schedule and find congestion","u_0042", "Personalisation"),
    ("what does my day look like",           "u_0042", "Personalisation"),
    ("show me my routine",                   "u_0042", "Personalisation"),
    # Plain venue query → Mode 1
    ("is it good if i go to gym right now",  "u_0042", "FAISS"),
]

all_pass = True
for query, uid, expected_source in cases:
    payload = {"query": query}
    if uid:
        payload["user_id"] = uid
    r = client.post("/api/ask", json=payload)
    d = r.json()
    sources = str(d.get("sources", ""))
    routed_correctly = expected_source in sources
    answer = d.get("answer", "")
    is_dummy = answer.startswith("Answer for query") or answer.startswith("Sorry,")
    ok = routed_correctly and not is_dummy
    all_pass = all_pass and ok
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] ({expected_source:15s}) Q: {query}")
    if not ok:
        print(f"       sources={sources}")
        print(f"       answer={answer[:150]}")

print(f"\n{'ALL PASS' if all_pass else 'FAILURES DETECTED'}")
