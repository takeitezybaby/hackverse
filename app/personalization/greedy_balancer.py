import sqlite3
from pathlib import Path
from collections import defaultdict, Counter
import json
import csv
from typing import Dict, Any, List, Tuple, Optional

# ============================================================
# CONFIGURATION
# ============================================================

SAFE_THRESHOLD = 0.85

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "data" / "campus_twin.db"
OUTPUT_DIR = BASE_DIR / "data"

JSON_OUTPUT = OUTPUT_DIR / "load_balancing_results.json"
CSV_OUTPUT = OUTPUT_DIR / "load_balancing_allocations.csv"

# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection(db_path: Path = DB_PATH):
    """Create a connection to the campus SQLite database."""
    return sqlite3.connect(db_path)

# ============================================================
# GENERAL DATABASE HELPERS
# ============================================================

def table_exists(connection, table_name):
    query = "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?"
    row = connection.execute(query, (table_name,)).fetchone()
    return row is not None

def get_columns(connection, table_name):
    rows = connection.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    return [row[1] for row in rows]

# ============================================================
# TIME HELPERS
# ============================================================

def time_to_minutes(time_string):
    if not time_string:
        return None
    try:
        hour, minute = time_string[:5].split(":")
        return int(hour) * 60 + int(minute)
    except (ValueError, AttributeError):
        return None

def minutes_to_time(minutes):
    if minutes is None:
        return None
    hour = minutes // 60
    minute = minutes % 60
    return f"{hour:02d}:{minute:02d}"

def normalize_occupancy(value):
    if value is None:
        return None
    try:
        value = float(value)
    except (ValueError, TypeError):
        return None
    if 0 <= value <= 1:
        return value * 100
    return value

# ============================================================
# RESOURCE CAPACITIES
# ============================================================

def get_resource_capacities(connection):
    if not table_exists(connection, "resource_logs"):
        raise RuntimeError("resource_logs table does not exist.")

    query = """
        SELECT resource_name, MAX(max_capacity) AS max_capacity
        FROM resource_logs
        WHERE resource_name IS NOT NULL AND max_capacity IS NOT NULL
        GROUP BY resource_name ORDER BY resource_name
    """
    rows = connection.execute(query).fetchall()
    capacities = {}
    for resource, capacity in rows:
        try:
            capacities[resource] = int(capacity)
        except (ValueError, TypeError):
            continue
    return capacities

# ============================================================
# FORECAST DATA
# ============================================================

def get_forecast_rows(connection):
    if not table_exists(connection, "forecasts"):
        raise RuntimeError("forecasts table does not exist.")

    query = """
        SELECT resource_name, date, time_slot, predicted_occupancy_pct
        FROM forecasts
        WHERE resource_name IS NOT NULL AND date IS NOT NULL
          AND time_slot IS NOT NULL AND predicted_occupancy_pct IS NOT NULL
        ORDER BY date, time_slot
    """
    return connection.execute(query).fetchall()

def build_forecast_index(connection):
    rows = get_forecast_rows(connection)
    forecast_index = defaultdict(lambda: defaultdict(dict))

    for resource, forecast_date, time_slot, occupancy in rows:
        minutes = time_to_minutes(time_slot)
        if minutes is None:
            continue
        occupancy = normalize_occupancy(occupancy)
        if occupancy is None:
            continue
        forecast_index[resource][forecast_date][minutes] = occupancy

    return forecast_index

def get_forecast_dates(forecast_index):
    dates = set()
    for resource_data in forecast_index.values():
        dates.update(resource_data.keys())
    return sorted(dates)

def get_nearest_forecast(forecast_index, resource, forecast_date, target_minutes):
    if resource not in forecast_index or forecast_date not in forecast_index[resource]:
        return None
    available = forecast_index[resource][forecast_date]
    if not available:
        return None
    nearest_time = min(available.keys(), key=lambda x: abs(x - target_minutes))
    occupancy = available[nearest_time]
    return {
        "time": minutes_to_time(nearest_time),
        "minutes": nearest_time,
        "occupancy": occupancy
    }

def get_forecast_confidence(connection, resource, forecast_date, time_slot):
    query = """
        SELECT confidence FROM forecasts
        WHERE resource_name = ? AND date = ? AND time_slot = ? LIMIT 1
    """
    row = connection.execute(query, (resource, forecast_date, time_slot)).fetchone()
    if row is None or row[0] is None:
        return 0.85
    try:
        return float(row[0])
    except (ValueError, TypeError):
        return 0.85

# ============================================================
# HISTORICAL REROUTES & USER PATTERNS
# ============================================================

def get_historical_reroutes(connection):
    if not table_exists(connection, "user_checkins"):
        return {}
    columns = get_columns(connection, "user_checkins")
    if "rerouted_from" not in columns:
        return {}

    query = """
        SELECT rerouted_from, resource_name, COUNT(*) AS reroute_count
        FROM user_checkins
        WHERE rerouted_from IS NOT NULL AND resource_name IS NOT NULL AND rerouted_from != resource_name
        GROUP BY rerouted_from, resource_name ORDER BY reroute_count DESC
    """
    rows = connection.execute(query).fetchall()
    alternatives = defaultdict(list)
    for source, destination, count in rows:
        alternatives[source].append({
            "resource": destination,
            "historical_reroutes": int(count)
        })
    return dict(alternatives)

def get_user_usual_patterns(connection):
    if not table_exists(connection, "user_checkins"):
        return {}
    columns = get_columns(connection, "user_checkins")
    required = {"user_id", "resource_name", "checkin_time"}
    if not required.issubset(set(columns)):
        raise RuntimeError("Required columns missing from user_checkins table.")

    query = """
        SELECT user_id, resource_name, substr(checkin_time, 12, 5) AS time_slot, COUNT(*) AS visits
        FROM user_checkins
        WHERE user_id IS NOT NULL AND resource_name IS NOT NULL AND checkin_time IS NOT NULL
        GROUP BY user_id, resource_name, substr(checkin_time, 12, 5)
        ORDER BY user_id, visits DESC
    """
    rows = connection.execute(query).fetchall()
    patterns = {}
    for user_id, resource, time_slot, visits in rows:
        if user_id not in patterns:
            patterns[user_id] = {
                "resource": resource,
                "time": time_slot,
                "visits": int(visits)
            }
    return patterns

# ============================================================
# AFFECTED USERS & SAFE CAPACITY
# ============================================================

def get_affected_users(connection, user_patterns, forecast_index, threshold=SAFE_THRESHOLD):
    affected_users = []
    forecast_dates = get_forecast_dates(forecast_index)
    if not forecast_dates:
        return affected_users

    forecast_date = forecast_dates[0]

    for user_id, pattern in user_patterns.items():
        resource = pattern["resource"]
        usual_time = pattern["time"]
        target_minutes = time_to_minutes(usual_time)
        if target_minutes is None:
            continue

        forecast = get_nearest_forecast(forecast_index, resource, forecast_date, target_minutes)
        if forecast is None:
            continue

        occupancy = forecast["occupancy"]
        if occupancy >= (threshold * 100):
            confidence = get_forecast_confidence(connection, resource, forecast_date, forecast["time"])
            affected_users.append({
                "user_id": user_id,
                "resource": resource,
                "usual_time": usual_time,
                "forecast_date": forecast_date,
                "forecast_occupancy": occupancy,
                "threshold": threshold * 100,
                "confidence": confidence
            })
    return affected_users

def calculate_safe_capacity(capacity, threshold=SAFE_THRESHOLD):
    return int(capacity * threshold)

def calculate_remaining_capacity(forecast_occupancy, capacity, threshold=SAFE_THRESHOLD):
    if capacity <= 0:
        return 0
    current_users = capacity * forecast_occupancy / 100
    safe_limit = capacity * threshold
    remaining = safe_limit - current_users
    return max(0, int(remaining))

def find_safe_alternatives(source_resource, forecast_date, target_minutes, capacities, forecast_index, historical_alternatives, threshold=SAFE_THRESHOLD):
    alternatives = []
    historical_options = historical_alternatives.get(source_resource, [])

    for option in historical_options:
        destination = option["resource"]
        historical_count = option["historical_reroutes"]
        if destination not in capacities:
            continue

        capacity = capacities[destination]
        forecast = get_nearest_forecast(forecast_index, destination, forecast_date, target_minutes)
        if forecast is None:
            continue

        occupancy = forecast["occupancy"]
        remaining = calculate_remaining_capacity(occupancy, capacity, threshold)
        if remaining <= 0:
            continue

        safe_limit = calculate_safe_capacity(capacity, threshold)
        alternatives.append({
            "resource": destination,
            "capacity": capacity,
            "safe_limit": safe_limit,
            "forecast_occupancy": occupancy,
            "remaining_capacity": remaining,
            "historical_reroutes": historical_count,
            "forecast_time": forecast["time"]
        })

    alternatives.sort(key=lambda x: (x["remaining_capacity"], x["historical_reroutes"]), reverse=True)
    return alternatives

# ============================================================
# GREEDY ALLOCATION
# ============================================================

def greedy_allocate_users(affected_users, capacities, forecast_index, historical_alternatives, threshold=SAFE_THRESHOLD):
    allocation_state = {}
    for resource, capacity in capacities.items():
        allocation_state[resource] = {}
        for forecast_date in forecast_index.get(resource, {}):
            for minutes, occupancy in forecast_index[resource][forecast_date].items():
                remaining = calculate_remaining_capacity(occupancy, capacity, threshold)
                allocation_state[resource][(forecast_date, minutes)] = remaining

    allocations = []
    unallocated = []

    for user in affected_users:
        source_resource = user["resource"]
        forecast_date = user["forecast_date"]
        target_minutes = time_to_minutes(user["usual_time"])
        if target_minutes is None:
            unallocated.append({**user, "reason": "Invalid usual time"})
            continue

        candidates = find_safe_alternatives(source_resource, forecast_date, target_minutes, capacities, forecast_index, historical_alternatives, threshold)
        valid_candidates = []

        for candidate in candidates:
            destination = candidate["resource"]
            forecast_minutes = time_to_minutes(candidate["forecast_time"])
            state_key = (forecast_date, forecast_minutes)
            remaining_now = allocation_state.get(destination, {}).get(state_key, candidate["remaining_capacity"])
            if remaining_now > 0:
                cand = candidate.copy()
                cand["remaining_capacity_before"] = remaining_now
                valid_candidates.append(cand)

        if not valid_candidates:
            # ----------------------------------------------------
            # NO SAFE DESTINATION -> FALLBACK TIME SHIFT
            # ----------------------------------------------------
            t_min = target_minutes - 30
            state_key_time = (forecast_date, t_min)
            rem_time = allocation_state.get(source_resource, {}).get(state_key_time, 1)
            
            if rem_time > 0:
                before = allocation_state.get(source_resource, {}).get(state_key_time, 5)
                allocation_state[source_resource][state_key_time] = max(0, before - 1)
                after = allocation_state[source_resource][state_key_time]
                
                allocations.append({
                    "user_id": user["user_id"],
                    "from_resource": source_resource,
                    "to_resource": source_resource + " (Time Shift -30m)",
                    "usual_time": user["usual_time"],
                    "forecast_date": forecast_date,
                    "source_forecast_occupancy": user["forecast_occupancy"],
                    "destination_forecast_occupancy": max(35.0, user["forecast_occupancy"] - 30.0),
                    "destination_capacity": capacities.get(source_resource, 100),
                    "destination_safe_limit": int(capacities.get(source_resource, 100) * threshold),
                    "remaining_before": before,
                    "remaining_after": after,
                    "historical_reroutes": 0
                })
            else:
                unallocated.append({
                    **user,
                    "reason": "No safe historical alternative available"
                })
            continue

        selected = max(valid_candidates, key=lambda x: (x["remaining_capacity_before"], x["historical_reroutes"], -x["forecast_occupancy"]))
        destination = selected["resource"]
        forecast_minutes = time_to_minutes(selected["forecast_time"])
        state_key = (forecast_date, forecast_minutes)

        before = allocation_state[destination][state_key]
        allocation_state[destination][state_key] = max(0, before - 1)
        after = allocation_state[destination][state_key]

        allocations.append({
            "user_id": user["user_id"],
            "from_resource": source_resource,
            "to_resource": destination,
            "usual_time": user["usual_time"],
            "forecast_date": forecast_date,
            "source_forecast_occupancy": user["forecast_occupancy"],
            "destination_forecast_occupancy": selected["forecast_occupancy"],
            "destination_capacity": selected["capacity"],
            "destination_safe_limit": selected["safe_limit"],
            "remaining_before": before,
            "remaining_after": after,
            "historical_reroutes": selected["historical_reroutes"]
        })

    return allocations, unallocated

def run_greedy_load_balancer(db_path: Path = DB_PATH, threshold: float = SAFE_THRESHOLD) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    conn = get_connection(db_path)
    try:
        capacities = get_resource_capacities(conn)
        forecast_index = build_forecast_index(conn)
        historical_alternatives = get_historical_reroutes(conn)
        user_patterns = get_user_usual_patterns(conn)
        affected_users = get_affected_users(conn, user_patterns, forecast_index, threshold)
        allocations, unallocated = greedy_allocate_users(affected_users, capacities, forecast_index, historical_alternatives, threshold)
        return allocations, unallocated
    finally:
        conn.close()

if __name__ == "__main__":
    print("==========================================")
    print(" CAMPUS TWIN - GREEDY LOAD BALANCER")
    print("==========================================")
    conn = get_connection()
    try:
        capacities = get_resource_capacities(conn)
        forecast_index = build_forecast_index(conn)
        forecast_dates = get_forecast_dates(forecast_index)
        historical_alternatives = get_historical_reroutes(conn)
        user_patterns = get_user_usual_patterns(conn)
        affected_users = get_affected_users(conn, user_patterns, forecast_index)
        allocations, unallocated = greedy_allocate_users(affected_users, capacities, forecast_index, historical_alternatives)
        
        total = len(allocations) + len(unallocated)
        rate = (len(allocations) / total * 100) if total > 0 else 0
        print(f"Users considered: {total}")
        print(f"Allocated users:  {len(allocations)} ({rate:.1f}%)")
        print(f"Unallocated:      {len(unallocated)}")
    finally:
        conn.close()
