import json

with open('data/snapshots/all_snapshots.json') as f:
    snaps = json.load(f)

print('=== BUG 1 CHECK: true demand should be >= observed occupancy ===')
violations = []
for s in snaps:
    observed = s['summary']['peak_occupancy_pct']
    true_demand = s['peak_demand_pct']
    if true_demand < observed:
        violations.append(s)

if violations:
    print(f'FAIL: {len(violations)} snapshots where true_demand < observed')
    for v in violations[:3]:
        print(f"  {v['resource']} {v['date']}: observed={v['summary']['peak_occupancy_pct']} true={v['peak_demand_pct']}")
else:
    print('PASS: true_demand >= observed for all snapshots')

zero_demand = [s for s in snaps if s['peak_demand_pct'] == 0.0 and s['summary']['peak_occupancy_pct'] > 0]
print(f'Snapshots with 0.0% true demand but nonzero observed: {len(zero_demand)} (should be 0)')

print()
print('=== BUG 1 SPOT-CHECK: resources with known reroutes ===')
sci = [s for s in snaps if s['resource'] == 'Science Library']
for s in sci[:4]:
    obs = s['summary']['peak_occupancy_pct']
    td = s['peak_demand_pct']
    print(f"  Science Library {s['date']}: observed={obs}% true_demand={td}% embed snippet: {s['embed_text'][:90]}")

print()
print('=== BUG 2 CHECK: allocation numbers should differ across dates for same resource ===')
comp_a = [s for s in snaps if s['resource'] == 'Computer Lab A']
alloc_texts = {}
for s in comp_a[:8]:
    alloc_texts[s['date']] = s['allocation_summary']
    print(f"  Computer Lab A {s['date']} ({s['day_of_week']}): {s['allocation_summary']}")

unique_alloc = len(set(alloc_texts.values()))
print(f'\nUnique allocation_summary values across 8 dates: {unique_alloc} (should be > 1)')
if unique_alloc > 1:
    print('PASS: allocation numbers differ per date')
else:
    print('FAIL: still identical across dates')
