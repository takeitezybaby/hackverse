import sys
sys.path.insert(0, '.')
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

cases = [
    # Original failing query
    ("at what time should i go to library", "u_0042"),
    # Variant timing queries
    ("what is the best time to visit the gym today?", "u_0042"),
    ("when is the library least crowded?", None),
    ("when should i go to the cafeteria?", None),
    # Non-timing should still work
    ("is the library open now?", None),
    ("should i go to gym right now?", "u_0042"),
]

for query, uid in cases:
    payload = {"query": query}
    if uid:
        payload["user_id"] = uid
    r = client.post("/api/ask", json=payload)
    d = r.json()
    answer = d.get("answer", "")

    invented = "7 PM" in answer or "7pm" in answer.lower()
    dummy    = answer.startswith("Answer for query")
    err      = answer.startswith("Sorry,")
    status   = "FAIL" if (invented or dummy or err) else "PASS"

    print(f"\n[{status}] Q: {query}")
    print(f"        A: {answer}")
    if invented: print("        !! INVENTED TIME DETECTED")
    if dummy:    print("        !! DUMMY TEMPLATE")
    if err:      print("        !! ERROR STRING")
