"""
Full pre-flight check: backend routes, DB, FAISS index, and frontend wiring.
Run with: python scratch/preflight.py
"""
import sys, os, json, urllib.request, subprocess, time, socket
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"

results = []

def check(label, cond, detail=""):
    status = PASS if cond else FAIL
    suffix = f"  -> {detail}" if detail else ""
    print(f"  {status} {label}{suffix}")
    results.append(cond)
    return cond

print("\n=== 1. Data files ===")
required_files = [
    "data/campus_twin.db",
    "data/resource_logs.json",
    "data/checkins.json",
    "data/snapshots/all_snapshots.json",
    "data/crowdsourced_reports.json",
    "data/load_balancing_results.json",
    "data/events_ground_truth.json",
    "data/faiss_index.bin",
    "data/faiss_metadata.json",
    "data/faiss_documents.json",
]
for f in required_files:
    exists = os.path.exists(f)
    size = os.path.getsize(f) if exists else 0
    check(f, exists, f"{size//1024}KB" if exists else "MISSING")

print("\n=== 2. Python imports ===")
try:
    from app.main import app
    check("app.main imports cleanly", True)
except Exception as e:
    check("app.main imports cleanly", False, str(e))

try:
    import faiss
    check("faiss-cpu installed", True, f"version available")
except ImportError as e:
    check("faiss-cpu installed", False, str(e))

try:
    from app.rag.retriever import CampusRAG
    rag = CampusRAG()
    n = rag.seed_from_snapshots()
    check(f"RAG index loads ({n} vectors)", n == 480, f"expected 480 got {n}")
except Exception as e:
    check("RAG index loads", False, str(e))

try:
    from app.twin.state import get_all_current_states
    states = get_all_current_states("2023-09-12T19:00:00")
    check(f"Digital twin state ({len(states)} resources)", len(states) == 12, f"expected 12 got {len(states)}")
except Exception as e:
    check("Digital twin state", False, str(e))

try:
    from app.twin.forecast import generate_forecast
    fc = generate_forecast("Gymnasium", "2023-09-12", "19:00")
    ok = fc.predicted_demand_pct >= fc.predicted_occupancy_pct
    check(f"Forecast engine (demand {fc.predicted_demand_pct}% >= observed {fc.predicted_occupancy_pct}%)", ok)
except Exception as e:
    check("Forecast engine", False, str(e))

try:
    from app.personalization import generate_user_recommendations
    rec = generate_user_recommendations("u_0042")
    check("Personalization engine (u_0042)", "schedule" in rec, str(list(rec.keys())))
except Exception as e:
    check("Personalization engine", False, str(e))

print("\n=== 3. Ollama daemon ===")
try:
    with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=5) as r:
        models = [m["name"] for m in json.loads(r.read()).get("models", [])]
    check("Ollama UP", True, f"{len(models)} models")
    check("granite-embedding:278m present", any("granite-embedding" in m for m in models), str(models))
    check("granite3.1-dense:8b present",    any("granite3.1-dense" in m for m in models), str(models))
except Exception as e:
    check("Ollama UP", False, str(e))
    check("granite-embedding:278m present", False, "daemon unreachable")
    check("granite3.1-dense:8b present",    False, "daemon unreachable")

print("\n=== 4. DB schema & row counts ===")
import sqlite3
conn = sqlite3.connect("data/campus_twin.db")
tables = {r[0]: 0 for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
for t in tables:
    tables[t] = conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
conn.close()

expected_tables = {
    "user_checkins": (1000, None),
    "resource_logs": (1000, None),
    "users":         (100,  None),
    "timetables":    (1,    None),
    "crowdsourced_reports": (1, None),
}
for t, (min_rows, _) in expected_tables.items():
    n = tables.get(t, 0)
    check(f"table {t} ({n} rows)", n >= min_rows, f"min expected {min_rows}")

print("\n=== 5. Frontend wiring ===")
check("frontend/demo.html exists", os.path.exists("frontend/demo.html"))
check("frontend/src/App.tsx exists", os.path.exists("frontend/src/App.tsx"))

# Check API_BASE is localhost:8000 in demo.html
with open("frontend/demo.html", encoding="utf-8") as f:
    html = f.read()
check("demo.html API_BASE points to localhost:8000", 'localhost:8000' in html)
check("demo.html fetches /forecast", '/forecast' in html)
check("demo.html fetches /api/ask", '/api/ask' in html)
check("demo.html fetches /api/report/daily", '/api/report/daily' in html)
check("demo.html fetches /api/ingest/checkin", '/api/ingest/checkin' in html)

# Check React app API URLs
with open("frontend/src/App.tsx", encoding="utf-8") as f:
    tsx = f.read()
check("App.tsx fetches /forecast from localhost:8000", 'localhost:8000' in tsx and '/forecast' in tsx)
check("App.tsx fetches /report/daily", '/report/daily' in tsx)

# Check all routes the frontend calls exist on the backend
routes_needed = ["/forecast", "/report/daily/{user_id}", "/ask", "/allocate",
                 "/api/ingest/checkin", "/api/ask", "/api/report/daily/{user_id}",
                 "/api/events/ground-truth"]
from app.main import app as fastapi_app
registered = [r.path for r in fastapi_app.routes if hasattr(r, 'path')]
for needed in routes_needed:
    check(f"route {needed} registered", needed in registered)

print()
total = len(results)
passed = sum(results)
failed = total - passed
print(f"{'='*50}")
print(f"  {passed}/{total} checks passed  |  {failed} failed")
print(f"{'='*50}")
if failed == 0:
    print("  ALL SYSTEMS GO - safe to run demo")
else:
    print("  FIX THE ABOVE BEFORE RUNNING DEMO")
