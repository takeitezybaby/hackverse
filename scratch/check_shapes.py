import sys
sys.path.insert(0, '.')
import json

# Check 1: what does generate_forecast signature actually require?
import inspect
from app.twin.forecast import generate_forecast
print("generate_forecast signature:", inspect.signature(generate_forecast))

# Check 2: what does allocator actually call?
# (allocator.py line 54: generate_forecast(res_name, target_date) — only 2 args)
# Simulate what happens
try:
    result = generate_forecast("Gymnasium", "2023-09-12")
    print("2-arg call succeeded:", result)
except TypeError as e:
    print("2-arg call FAILS with TypeError:", e)

# Check 3: what does /api/allocate sample_allocations actually look like?
from app.personalization import run_greedy_load_balancer
allocs, unalloc = run_greedy_load_balancer(threshold=0.85)
print("\nSample allocation keys:", list(allocs[0].keys()) if allocs else "none")
print("Sample allocation:", json.dumps(allocs[0], indent=2) if allocs else "none")

# Check 4: what does primary_allocation from allocator look like?
from app.personalization.allocator import generate_user_recommendations
rec = generate_user_recommendations("u_0042")
print("\nprimary_allocation keys:", list(rec["primary_allocation"].keys()))
print("primary_allocation:", json.dumps(rec["primary_allocation"], indent=2))

# Check 5: what does a schedule entry look like?
print("\nSchedule entry[0] keys:", list(rec["schedule"][0].keys()) if rec["schedule"] else "empty")
if rec["schedule"]:
    print("Schedule entry[0]:", json.dumps(rec["schedule"][0], indent=2))
