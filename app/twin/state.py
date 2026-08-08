"""
Layer 2 — Digital Twin State
==============================
Provides the 'live' snapshot of a resource: current occupancy,
status bucket, and whether any anomaly is active right now.

Pre-DB: reads from resource_logs.json.
Post-DB: swap to aiosqlite queries (same interface).
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict

from app.contracts import StatusBucket, RESOURCES

try:
    import sys
    _proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _proj_root not in sys.path:
        sys.path.insert(0, _proj_root)
    from data_gen.config import ANOMALIES, RESOURCE_CAPACITIES
except ImportError:
    ANOMALIES = {}
    RESOURCE_CAPACITIES = {}

from app.twin.forecast import get_anomaly_for_date, floor_to_bucket


@dataclass
class ResourceState:
    """Live snapshot of a single resource."""
    resource_name: str
    resource_slug: str
    timestamp: str
    current_occupancy: int
    max_capacity: int
    occupancy_pct: float
    status: str               # StatusBucket value
    active_anomaly: Optional[str] = None  # anomaly type if active

    def to_dict(self) -> dict:
        return asdict(self)


# ── Data Loading (JSON, pre-DB) ─────────────────────────────────────────

_logs_cache: Optional[List[dict]] = None

def _load_logs() -> List[dict]:
    global _logs_cache
    if _logs_cache is not None:
        return _logs_cache
    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'data'
    )
    path = os.path.join(data_dir, 'resource_logs.json')
    with open(path, 'r') as f:
        _logs_cache = json.load(f)
    return _logs_cache


def get_current_state(resource_name: str, at_time: Optional[str] = None, db_counts: Optional[Dict[str, int]] = None) -> Optional[ResourceState]:
    """Get the most recent (or specific-time) state of a resource.
    
    Args:
        resource_name: Display name of the resource.
        at_time: Optional ISO timestamp. If None, returns the latest reading.
        db_counts: Optional pre-queried map of resource_name -> live checkin count.
    """
    logs = _load_logs()
    resource_logs = [r for r in logs if r['resource_name'] == resource_name]
    
    if not resource_logs:
        return None

    if at_time:
        target_dt = datetime.fromisoformat(at_time.replace('Z', ''))
        target_bucket = floor_to_bucket(target_dt)
        # Find the exact bucket match
        best = None
        for r in resource_logs:
            ts = datetime.fromisoformat(r['timestamp'].replace('Z', ''))
            if floor_to_bucket(ts) == target_bucket:
                best = r
                break
        if not best:
            # Fallback: closest before target
            before = [r for r in resource_logs 
                      if datetime.fromisoformat(r['timestamp'].replace('Z', '')) <= target_dt]
            if before:
                best = max(before, key=lambda r: r['timestamp'])
    else:
        best = max(resource_logs, key=lambda r: r['timestamp'])

    if not best:
        return None

    ts_dt = datetime.fromisoformat(best['timestamp'].replace('Z', ''))
    anomaly = get_anomaly_for_date(ts_dt)
    slug = resource_name.lower().replace(' ', '_').replace('-', '_').replace('__', '_')

    current_occ = best['current_occupancy']
    cap = best['max_capacity']

    # Dynamically check live check-ins
    if db_counts is not None:
        if resource_name in db_counts:
            current_occ = max(current_occ, db_counts[resource_name])
    else:
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'campus_twin.db')
        if os.path.exists(db_path):
            try:
                import sqlite3
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                eval_time = best['timestamp'].replace('Z', '')
                cursor.execute("""
                    SELECT count(*) FROM user_checkins 
                    WHERE resource_name = ? 
                      AND checkin_time <= ? 
                      AND checkout_time > ?
                """, (resource_name, eval_time, eval_time))
                row = cursor.fetchone()
                if row and row[0] > 0:
                    current_occ = max(current_occ, row[0])
                conn.close()
            except Exception:
                pass

    occ_pct = (current_occ / cap * 100.0) if cap > 0 else 0.0

    return ResourceState(
        resource_name=resource_name,
        resource_slug=slug,
        timestamp=best['timestamp'],
        current_occupancy=current_occ,
        max_capacity=cap,
        occupancy_pct=round(occ_pct, 1),
        status=StatusBucket.from_pct(occ_pct).value,
        active_anomaly=anomaly.get('type') if anomaly else None,
    )


def get_all_current_states(at_time: Optional[str] = None) -> List[ResourceState]:
    """Get the live state of every resource at once using a single batched DB query."""
    # Batch query SQLite for all 12 venues at once
    db_counts = {}
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'campus_twin.db')
    if os.path.exists(db_path):
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            eval_time = at_time.replace('Z', '') if at_time else '2023-09-12T19:00:00'
            cursor.execute("""
                SELECT resource_name, count(*) FROM user_checkins 
                WHERE checkin_time <= ? AND checkout_time > ?
                GROUP BY resource_name
            """, (eval_time, eval_time))
            for row in cursor.fetchall():
                db_counts[row[0]] = row[1]
            conn.close()
        except Exception:
            pass

    states = []
    for slug, info in RESOURCES.items():
        state = get_current_state(info['name'], at_time, db_counts=db_counts)
        if state:
            states.append(state)
    return states


# ── CLI Test ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=== Digital Twin State — Smoke Test ===\n")
    
    # Latest state
    state = get_current_state('Gymnasium')
    if state:
        print(f"Gymnasium (latest): {state.occupancy_pct}% ({state.status}) @ {state.timestamp}")
    
    # State at a specific time (infra incident day)
    state2 = get_current_state('Computer Lab A', '2023-09-10T14:00:00')
    if state2:
        print(f"Computer Lab A (Sep 10 14:00): {state2.occupancy_pct}% ({state2.status})")
        print(f"  Active anomaly: {state2.active_anomaly}")
    
    # All resources at exam week
    print(f"\nAll states at Sep 26 20:00:")
    all_states = get_all_current_states('2023-09-26T20:00:00')
    for s in sorted(all_states, key=lambda x: -x.occupancy_pct)[:5]:
        print(f"  {s.resource_name}: {s.occupancy_pct}% ({s.status})")
