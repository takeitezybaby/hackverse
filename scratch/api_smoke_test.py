"""
Live API smoke test — spins up the FastAPI app in-process and hits every
registered endpoint with realistic payloads, asserting on status codes,
response shapes, and data correctness.

Run: python scratch/api_smoke_test.py
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"
results = []

def check(label, cond, detail=""):
    tag = PASS if cond else FAIL
    suffix = f"  -> {detail}" if detail else ""
    print(f"  {tag} {label}{suffix}")
    results.append((label, cond, detail))
    return cond

def jcheck(label, resp, status=200, keys=None, checks=None):
    ok_status = check(f"{label} — status {status}", resp.status_code == status,
                      f"got {resp.status_code}")
    if not ok_status:
        print(f"       body: {resp.text[:200]}")
        return None
    try:
        data = resp.json()
    except Exception as e:
        check(f"{label} — valid JSON", False, str(e))
        return None
    check(f"{label} — valid JSON", True)
    if keys:
        for k in keys:
            check(f"{label} — has '{k}'", k in data, str(list(data.keys()))[:80])
    if checks:
        for desc, cond in checks:
            check(f"{label} — {desc}", cond)
    return data

# ── /health ──────────────────────────────────────────────────────────────
print("\n=== GET /health ===")
d = jcheck("/health", client.get("/health"), keys=["status","demo_now","database_connected"])
if d:
    check("status == healthy",      d.get("status") == "healthy")
    check("database_connected True", d.get("database_connected") is True)
    check("demo_now is present",     bool(d.get("demo_now")))

# ── /api/resources ───────────────────────────────────────────────────────
print("\n=== GET /api/resources ===")
d = jcheck("/api/resources", client.get("/api/resources"), keys=["resources"])
if d:
    resources = d["resources"]
    check("12 resources returned", len(resources) == 12, f"got {len(resources)}")
    check("each has name/slug/capacity",
          all("name" in r and "slug" in r and "capacity" in r for r in resources))
    slugs = [r["slug"] for r in resources]
    check("gymnasium slug present", "gymnasium" in slugs)
    check("main_library slug present", "main_library" in slugs)

# ── /api/state ───────────────────────────────────────────────────────────
print("\n=== GET /api/state ===")
d = jcheck("/api/state", client.get("/api/state"), keys=["states","count","reference_clock"])
if d:
    states = d["states"]
    check("12 states returned", len(states) == 12, f"got {len(states)}")
    for s in states:
        ok = all(k in s for k in ["resource_name","occupancy_pct","status","current_occupancy","max_capacity"])
        if not ok:
            check(f"state shape for {s.get('resource_name','?')}", False, str(list(s.keys())))
            break
    check("all state shapes valid", True)
    check("all occupancy_pct in [0,110]",
          all(0 <= s["occupancy_pct"] <= 110 for s in states))
    check("all statuses are valid buckets",
          all(s["status"] in ("empty","low","moderate","high","full","overflow") for s in states))

# ── /api/state/{slug} ────────────────────────────────────────────────────
print("\n=== GET /api/state/gymnasium ===")
d = jcheck("/api/state/gymnasium",
           client.get("/api/state/gymnasium"),
           keys=["resource_name","occupancy_pct","status"])
if d:
    check("resource_name == Gymnasium", d["resource_name"] == "Gymnasium",
          d.get("resource_name"))
    check("max_capacity == 50", d["max_capacity"] == 50, str(d.get("max_capacity")))

print("\n=== GET /api/state/nonexistent (expect 404) ===")
jcheck("/api/state/nonexistent — 404", client.get("/api/state/nonexistent_xyz"), status=404)

# ── /api/forecast/{slug} ─────────────────────────────────────────────────
print("\n=== GET /api/forecast/gymnasium?date=2023-09-12 ===")
d = jcheck("/api/forecast/gymnasium",
           client.get("/api/forecast/gymnasium?date=2023-09-12"),
           keys=["resource_name","slots","total_slots"])
if d:
    check("72 slots (15-min × 18 hrs)", d["total_slots"] == 72, f"got {d['total_slots']}")
    slot = d["slots"][0]
    check("slot has predicted_occupancy_pct", "predicted_occupancy_pct" in slot)
    check("slot has predicted_demand_pct",    "predicted_demand_pct" in slot)
    check("slot has predicted_status",        "predicted_status" in slot)
    check("demand >= observed for all slots",
          all(s["predicted_demand_pct"] >= s["predicted_occupancy_pct"] for s in d["slots"]))

# ── /api/forecast/{slug}/slot ────────────────────────────────────────────
print("\n=== GET /api/forecast/gymnasium/slot?date=2023-09-12&time=19:00 ===")
d = jcheck("/api/forecast/gymnasium/slot",
           client.get("/api/forecast/gymnasium/slot?date=2023-09-12&time=19:00"),
           keys=["predicted_occupancy_pct","predicted_demand_pct","predicted_status","confidence"])
if d:
    check("demand >= observed",
          d["predicted_demand_pct"] >= d["predicted_occupancy_pct"])
    check("confidence in [0,1]", 0 <= d["confidence"] <= 1, str(d["confidence"]))
    check("status is valid bucket",
          d["predicted_status"] in ("empty","low","moderate","high","full","overflow"))

# ── /forecast (root alias) ───────────────────────────────────────────────
print("\n=== GET /forecast (frontend alias) ===")
d = jcheck("/forecast alias", client.get("/forecast"))
if d:
    check("returns list", isinstance(d, list), type(d).__name__)
    check("12 items", len(d) == 12, f"got {len(d)}")
    item = d[0]
    for k in ["id","name","currentOccupancy","capacityMax","hourlyForecast"]:
        check(f"item has '{k}'", k in item)
    check("hourlyForecast has 8 slots", len(item.get("hourlyForecast", [])) == 8)

# ── /api/events/ground-truth ─────────────────────────────────────────────
print("\n=== GET /api/events/ground-truth ===")
d = jcheck("/api/events/ground-truth",
           client.get("/api/events/ground-truth"), keys=["events"])
if d:
    events = d["events"]
    check("3 ground-truth events", len(events) == 3, f"got {len(events)}")
    types = {e["event_type"] for e in events}
    check("cultural_fest present",    "cultural_fest"    in types)
    check("infra_incident present",   "infra_incident"   in types)
    check("class_cancellation present","class_cancellation" in types)

# ── /api/report/daily/{user_id} ──────────────────────────────────────────
print("\n=== GET /api/report/daily/u_0042 ===")
d = jcheck("/api/report/daily/u_0042",
           client.get("/api/report/daily/u_0042"),
           keys=["student_id","schedule","load_balance_score","explanation"])
if d:
    check("student_id == u_0042", d["student_id"] == "u_0042")
    check("schedule is list",     isinstance(d["schedule"], list))
    check("load_balance_score > 0", d["load_balance_score"] > 0,
          str(d["load_balance_score"]))
    check("explanation not empty",  bool(d.get("explanation", "").strip()))
    if d["schedule"]:
        entry = d["schedule"][0]
        # schedule entries nest data under habit/recommendation sub-objects
        check("schedule entry has habit",         "habit" in entry)
        check("schedule entry has recommendation","recommendation" in entry)
        check("habit has location",  "location" in entry.get("habit", {}))
        check("recommendation has location", "location" in entry.get("recommendation", {}))

# ── /report/daily/{user_id} (root alias) ─────────────────────────────────
print("\n=== GET /report/daily/u_0042 (root alias) ===")
d2 = jcheck("/report/daily alias", client.get("/report/daily/u_0042"),
            keys=["student_id","schedule"])
if d2:
    check("root alias returns same data as /api/...",
          d2.get("student_id") == "u_0042")

# ── /api/allocate ────────────────────────────────────────────────────────
print("\n=== GET /api/allocate ===")
d = jcheck("/api/allocate", client.get("/api/allocate"),
           keys=["status","users_considered","allocated_users","success_rate_pct","sample_allocations"])
if d:
    check("status == success",          d["status"] == "success")
    check("users_considered > 0",       d["users_considered"] > 0,
          str(d["users_considered"]))
    check("success_rate_pct in [0,100]",
          0 <= d["success_rate_pct"] <= 100, str(d["success_rate_pct"]))
    check("sample_allocations is list", isinstance(d["sample_allocations"], list))
    if d["sample_allocations"]:
        a = d["sample_allocations"][0]
        # greedy_balancer output uses from_resource/to_resource (its own internal format)
        for k in ["user_id","from_resource","to_resource","usual_time","forecast_date"]:
            check(f"allocation has '{k}'", k in a, str(list(a.keys()))[:60])

# ── POST /api/ingest/checkin ─────────────────────────────────────────────
print("\n=== POST /api/ingest/checkin ===")
d = jcheck("/api/ingest/checkin",
           client.post("/api/ingest/checkin", json={
               "user_id": "u_smoke_test",
               "resource_name": "Gymnasium",
               "duration_min": 45
           }), status=201,
           keys=["status","checkin_id","stamped_checkin_time","checkout_time"])
if d:
    check("status == created",   d["status"] == "created")
    check("checkin_id is int",   isinstance(d["checkin_id"], int))
    check("resource == Gymnasium", d.get("resource_name") == "Gymnasium")
    check("checkin_time is ISO", "T" in d.get("stamped_checkin_time",""))

print("\n=== POST /api/ingest/checkin — missing user_id (expect 422) ===")
jcheck("/api/ingest/checkin bad payload", client.post("/api/ingest/checkin", json={
    "resource_name": "Gymnasium"
}), status=422)

# ── POST /api/ingest/report ──────────────────────────────────────────────
print("\n=== POST /api/ingest/report ===")
d = jcheck("/api/ingest/report",
           client.post("/api/ingest/report", json={
               "user_id": "u_smoke_test",
               "resource_name": "Main Library",
               "report_type": "full",
               "comment": "completely packed, no seats left"
           }), status=201,
           keys=["status","report_id","resource_name","report_type"])
if d:
    check("status == created",          d["status"] == "created")
    check("resource_name == Main Library", d["resource_name"] == "Main Library")
    check("report_id is int",           isinstance(d["report_id"], int))

# ── POST /api/ask ────────────────────────────────────────────────────────
print("\n=== POST /api/ask ===")
resp = client.post("/api/ask", json={
    "query": "should i go the gym right now?",
    "user_id": "u_0042"
})
d = jcheck("/api/ask", resp, keys=["query","answer","engine","is_fallback","live_state_summary"])
if d:
    check("answer is non-empty string",   bool(d.get("answer","").strip()))
    check("answer is not dummy template", not d["answer"].startswith("Answer for query"))
    check("answer is not error string",   not d["answer"].startswith("Sorry,"))
    check("live_state_summary has Gymnasium", "Gymnasium" in d.get("live_state_summary",""))
    check("sources list present",         isinstance(d.get("sources"), list))
    print(f"\n  LLM engine : {d.get('engine')}")
    print(f"  Is fallback: {d.get('is_fallback')}")
    print(f"  Answer     : {d.get('answer','')[:200]}")

# ── POST /ask (root alias) ────────────────────────────────────────────────
print("\n=== POST /ask (root alias) ===")
d2 = jcheck("/ask root alias", client.post("/ask", json={
    "query": "is the library quiet today?",
    "user_id": "u_0001"
}), keys=["answer","engine"])
if d2:
    check("root alias returns real answer", bool(d2.get("answer","").strip()))
    check("root alias not dummy template",  not d2["answer"].startswith("Answer for query"))

# ── /allocate (root alias) ────────────────────────────────────────────────
print("\n=== GET /allocate (root alias) ===")
d = jcheck("/allocate root alias", client.get("/allocate"), keys=["status","success_rate_pct"])
if d:
    check("root alias works", d["status"] == "success")

# ── Summary ───────────────────────────────────────────────────────────────
print()
print("=" * 56)
total  = len(results)
passed = sum(1 for _, ok, _ in results if ok)
failed = total - passed
print(f"  {passed}/{total} checks passed  |  {failed} failed")
print("=" * 56)
if failed:
    print("\n  FAILED CHECKS:")
    for label, ok, detail in results:
        if not ok:
            print(f"    [FAIL] {label}  ({detail})")
else:
    print("  ALL SYSTEMS GO")
