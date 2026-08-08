"""
Layer 2 — Forecasting Engine
==============================
Produces two predictions per resource/time-slot:
  1. predicted_occupancy_pct  — what the logs will likely show (observed, reroute-capped)
  2. predicted_demand_pct     — reroute-corrected true demand

Steps (see architecture doc):
  1. Bucket alignment (15-min)
  2. Anomaly-aware baseline selection
  3. Recency-weighted averaging
  4. State bucketing
  5. Cold-start fallback
  6. Demand reconstruction (corrects for reroute-censoring)
  7. Cause propagation
"""

import json
import os
import math
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass

# ── Import shared contracts ──────────────────────────────────────────────
from app.contracts import ForecastSlot, StatusBucket, RESOURCES

# ── Config (single source of truth) ─────────────────────────────────────
# We import data_gen.config for anomaly windows and constants.
# If this import fails (e.g. running outside the project root), we fall
# back to sane defaults so the module is still importable.
try:
    import sys
    _proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _proj_root not in sys.path:
        sys.path.insert(0, _proj_root)
    from data_gen.config import (
        START_DATE, NUM_DAYS, ANOMALIES,
        REROUTE_THRESHOLD_PCT, RESOURCE_CAPACITIES,
    )
except ImportError:
    from datetime import datetime as _dt
    START_DATE = _dt(2023, 9, 1)
    NUM_DAYS = 30
    REROUTE_THRESHOLD_PCT = 90
    ANOMALIES = {}
    RESOURCE_CAPACITIES = {}

# ── Constants ────────────────────────────────────────────────────────────
BUCKET_MINUTES = 15
HALF_LIFE_DAYS = 14          # exponential decay half-life
LOOKBACK_NORMAL = 28         # days to look back for normal baseline
LOOKBACK_ANOMALY = 90        # wider window for rare anomaly matches
CONGESTION_THRESHOLD = 65    # "high" starts at 65%

# ── Helpers ──────────────────────────────────────────────────────────────

def floor_to_bucket(dt: datetime) -> datetime:
    """Step 1: Floor a datetime to the nearest 15-min bucket."""
    return dt.replace(minute=(dt.minute // BUCKET_MINUTES) * BUCKET_MINUTES,
                      second=0, microsecond=0)


def get_anomaly_for_date(dt: datetime) -> Optional[Dict]:
    """Step 2: Check if a date falls inside any anomaly window.
    Returns the anomaly dict (with 'type' key) or None."""
    d = dt.date() if isinstance(dt, datetime) else dt
    for key, anom in ANOMALIES.items():
        a_start = anom.get('start_date')
        a_end = anom.get('end_date', anom.get('target_date', a_start))
        if a_start and a_end:
            if a_start.date() <= d <= a_end.date():
                return {**anom, 'key': key}
    return None


def recency_weight(days_ago: float) -> float:
    """Step 3: Exponential decay weight.  weight = 0.5 ^ (days_ago / half_life)"""
    return math.pow(0.5, days_ago / HALF_LIFE_DAYS)


# ── Data Loading (JSON-based, pre-DB) ───────────────────────────────────

class HistoricalData:
    """Loads and indexes the generated data for forecasting queries.
    When Layer 1 is ready, swap this for aiosqlite queries — the
    forecasting logic above this class does not change."""

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                'data'
            )
        self.data_dir = data_dir
        self._logs: Optional[List[dict]] = None
        self._checkins: Optional[List[dict]] = None
        self._ground_truth: Optional[List[dict]] = None
        # Pre-built indices (populated on first access)
        self._log_index: Optional[Dict] = None        # (resource, weekday, bucket_time) -> [rows]
        self._reroute_index: Optional[Dict] = None     # (original_resource, bucket_dt) -> count
        self._anomaly_dates: Optional[set] = None      # set of date objects that are anomaly days

    # ── Lazy loaders ─────────────────────────────────────────────────
    def _load_logs(self):
        if self._logs is not None:
            return
        path = os.path.join(self.data_dir, 'resource_logs.json')
        with open(path, 'r') as f:
            self._logs = json.load(f)
        # Build index: (resource_name, weekday_int, "HH:MM") -> [rows]
        self._log_index = {}
        self._anomaly_dates = set()
        # Pre-compute anomaly dates
        for key, anom in ANOMALIES.items():
            a_start = anom.get('start_date')
            a_end = anom.get('end_date', anom.get('target_date', a_start))
            if a_start and a_end:
                d = a_start.date()
                while d <= a_end.date():
                    self._anomaly_dates.add(d)
                    d += timedelta(days=1)

        for row in self._logs:
            ts = datetime.fromisoformat(row['timestamp'].replace('Z', ''))
            bucket = floor_to_bucket(ts)
            weekday = bucket.weekday()  # 0=Mon
            bucket_time = bucket.strftime('%H:%M')
            row_date = bucket.date()
            is_anomaly_day = row_date in self._anomaly_dates
            anomaly_type = None
            if is_anomaly_day:
                anom = get_anomaly_for_date(bucket)
                anomaly_type = anom.get('type') if anom else None

            key = (row['resource_name'], weekday, bucket_time)
            entry = {
                'occupancy_pct': row['occupancy_pct'],
                'current_occupancy': row['current_occupancy'],
                'max_capacity': row['max_capacity'],
                'date': row_date,
                'is_anomaly': is_anomaly_day,
                'anomaly_type': anomaly_type,
            }
            self._log_index.setdefault(key, []).append(entry)

    def _load_checkins(self):
        if self._checkins is not None:
            return
        path = os.path.join(self.data_dir, 'checkins.json')
        with open(path, 'r') as f:
            self._checkins = json.load(f)
        # Build reroute index: (original_resource, bucket_dt_iso) -> count
        self._reroute_index = {}
        for c in self._checkins:
            if 'rerouted_from' in c:
                orig_res = c['rerouted_from']
                checkin_dt = datetime.fromisoformat(c['checkin_time'].replace('Z', ''))
                bucket = floor_to_bucket(checkin_dt)
                key = (orig_res, bucket.isoformat())
                self._reroute_index[key] = self._reroute_index.get(key, 0) + 1

    def _load_ground_truth(self):
        if self._ground_truth is not None:
            return
        path = os.path.join(self.data_dir, 'events_ground_truth.json')
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
                self._ground_truth = data.get('events', [])
        else:
            self._ground_truth = []

    # ── Query methods ────────────────────────────────────────────────

    def get_matching_historical(
        self, resource_name: str, weekday: int, bucket_time: str,
        target_date, anomaly_type: Optional[str] = None
    ) -> List[dict]:
        """Step 2: Anomaly-aware baseline selection.
        If anomaly_type is set, return only rows from anomaly days of that type.
        If None, return only rows from normal (non-anomaly) days."""
        self._load_logs()
        key = (resource_name, weekday, bucket_time)
        rows = self._log_index.get(key, [])

        if anomaly_type:
            return [r for r in rows if r['is_anomaly'] and r['anomaly_type'] == anomaly_type]
        else:
            return [r for r in rows if not r['is_anomaly']]

    def get_any_weekday_rows(self, resource_name: str, weekday: int) -> List[dict]:
        """Step 5: Cold-start fallback — same weekday, any bucket."""
        self._load_logs()
        results = []
        for (res, wd, bt), rows in self._log_index.items():
            if res == resource_name and wd == weekday:
                results.extend(rows)
        return results

    def get_rerouted_away_count(self, resource_name: str, bucket_dt: datetime) -> int:
        """Step 6: How many users were rerouted away from this resource at this bucket."""
        self._load_checkins()
        key = (resource_name, floor_to_bucket(bucket_dt).isoformat())
        return self._reroute_index.get(key, 0)

    def get_max_capacity(self, resource_name: str) -> int:
        """Pull max_capacity from RESOURCE_CAPACITIES or from the logs themselves."""
        if resource_name in RESOURCE_CAPACITIES:
            return RESOURCE_CAPACITIES[resource_name]
        # Fallback: scan logs
        self._load_logs()
        for row in self._logs:
            if row['resource_name'] == resource_name:
                return row['max_capacity']
        return 100  # absolute fallback


# ── Singleton data holder ────────────────────────────────────────────────
_data: Optional[HistoricalData] = None

def get_data() -> HistoricalData:
    global _data
    if _data is None:
        _data = HistoricalData()
    return _data


# ── Core Forecasting ─────────────────────────────────────────────────────

def weighted_average(rows: List[dict], target_date, field: str = 'occupancy_pct') -> Tuple[float, float]:
    """Step 3: Recency-weighted average.
    Returns (weighted_avg, confidence)."""
    if not rows:
        return 0.0, 0.0

    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, '%Y-%m-%d').date()

    total_w = 0.0
    weighted_sum = 0.0
    for r in rows:
        days_ago = max(0, (target_date - r['date']).days)
        w = recency_weight(days_ago)
        weighted_sum += r[field] * w
        total_w += w

    if total_w == 0:
        return 0.0, 0.0

    avg = weighted_sum / total_w
    # Confidence: more data points → higher, capped at 0.95
    confidence = min(0.95, len(rows) * 0.15 + 0.3)
    return avg, confidence


def generate_forecast(resource_name: str, target_date: str, target_time: str) -> ForecastSlot:
    """Generate a single forecast for a resource at a specific date+time.
    Implements all 7 steps from the architecture spec."""
    data = get_data()

    # Step 1: Bucket alignment
    target_dt = datetime.strptime(f"{target_date} {target_time}", "%Y-%m-%d %H:%M")
    bucket_dt = floor_to_bucket(target_dt)
    weekday = bucket_dt.weekday()
    bucket_time = bucket_dt.strftime('%H:%M')

    # Step 2: Anomaly-aware baseline selection
    anomaly = get_anomaly_for_date(bucket_dt)
    anomaly_type = anomaly.get('type') if anomaly else None
    cause_label = anomaly_type  # Step 7: propagated into output

    rows = data.get_matching_historical(resource_name, weekday, bucket_time, bucket_dt.date(), anomaly_type)

    # Step 5: Cold-start fallback
    is_cold_start = False
    if not rows:
        fallback_rows = data.get_any_weekday_rows(resource_name, weekday)
        if anomaly_type:
            fallback_rows = [r for r in fallback_rows if r['is_anomaly'] and r['anomaly_type'] == anomaly_type]
        else:
            fallback_rows = [r for r in fallback_rows if not r['is_anomaly']]

        if fallback_rows:
            rows = fallback_rows
            is_cold_start = True

    # Step 3: Recency-weighted average on observed occupancy
    predicted_pct, confidence = weighted_average(rows, target_date)
    if is_cold_start:
        confidence = max(0.0, confidence - 0.2)  # penalize cold-start confidence

    # Step 4: State bucketing
    status = StatusBucket.from_pct(predicted_pct).value

    # Step 6: Demand reconstruction
    # Build demand series for the matching rows
    demand_rows = []
    for r in rows:
        # For each historical row, reconstruct demand = observed + rerouted_away
        hist_bucket_dt = datetime.combine(r['date'], bucket_dt.time())
        rerouted_away = data.get_rerouted_away_count(resource_name, hist_bucket_dt)
        cap = r.get('max_capacity', data.get_max_capacity(resource_name))
        observed = r['current_occupancy'] if 'current_occupancy' in r else (r['occupancy_pct'] / 100.0 * cap)
        true_demand = observed + rerouted_away
        demand_pct = (true_demand / cap * 100) if cap > 0 else 0.0
        demand_rows.append({**r, 'demand_pct': demand_pct})

    predicted_demand_pct, _ = weighted_average(demand_rows, target_date, field='demand_pct') if demand_rows else (predicted_pct, 0.0)

    return ForecastSlot(
        resource_name=resource_name,
        time_slot=bucket_time,
        predicted_occupancy_pct=round(predicted_pct, 1),
        predicted_status=status,
        confidence=round(confidence, 2),
        date=target_date,
        predicted_demand_pct=round(predicted_demand_pct, 1),
        cause=cause_label,
        is_cold_start=is_cold_start,
    )


def generate_daily_forecast(resource_name: str, target_date: str) -> List[ForecastSlot]:
    """Generate forecasts for every 15-min bucket from 06:00 to 23:45."""
    forecasts = []
    for hour in range(6, 24):
        for minute in (0, 15, 30, 45):
            time_str = f"{hour:02d}:{minute:02d}"
            forecasts.append(generate_forecast(resource_name, target_date, time_str))
    return forecasts


def cache_forecasts_to_db(db_path: Optional[str] = None, target_date: Optional[str] = None):
    """
    Pre-computes and caches forecasts for all resources into the SQLite database.
    If target_date is specified, caches that date. Otherwise, caches all 30 days of the dataset.
    """
    import sqlite3
    if db_path is None:
        db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'data', 'campus_twin.db'
        )
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Ensure table exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, resource_name TEXT, date TEXT,
            time_slot TEXT, predicted_occupancy_pct REAL, predicted_demand_pct REAL,
            predicted_status TEXT, confidence REAL, cause TEXT, is_cold_start BOOLEAN
        );
    ''')
    
    dates_to_cache = []
    if target_date:
        dates_to_cache.append(target_date)
    else:
        # Cache for all 30 days in dataset
        start = START_DATE
        for d in range(NUM_DAYS):
            curr = start + timedelta(days=d)
            dates_to_cache.append(curr.strftime('%Y-%m-%d'))
            
    resources = list(RESOURCES.values())
    total_slots = 0
    
    for date_str in dates_to_cache:
        # Clear existing entries for this date to avoid duplicates
        cursor.execute("DELETE FROM forecasts WHERE date = ?", (date_str,))
        
        for res_info in resources:
            res_name = res_info['name']
            daily = generate_daily_forecast(res_name, date_str)
            for slot in daily:
                cursor.execute('''
                    INSERT INTO forecasts (
                        resource_name, date, time_slot, predicted_occupancy_pct,
                        predicted_demand_pct, predicted_status, confidence, cause, is_cold_start
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    slot.resource_name, slot.date, slot.time_slot,
                    slot.predicted_occupancy_pct, slot.predicted_demand_pct,
                    slot.predicted_status, slot.confidence, slot.cause, slot.is_cold_start
                ))
                total_slots += 1
                
    conn.commit()
    conn.close()
    print(f"Successfully cached {total_slots} forecast slots across {len(dates_to_cache)} days in SQLite DB.")


# ── CLI Test ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=== Layer 2 Forecast Engine — Smoke Test ===\n")

    # Normal day: Tuesday Sep 5
    fc = generate_forecast('Gymnasium', '2023-09-05', '19:00')
    print(f"Gymnasium Tue 19:00 (normal):")
    print(f"  Observed forecast: {fc.predicted_occupancy_pct}%  Status: {fc.predicted_status}")
    print(f"  Demand forecast:   {fc.predicted_demand_pct}%")
    print(f"  Cause: {fc.cause}  Cold-start: {fc.is_cold_start}  Confidence: {fc.confidence}")

    # Infra incident day: Sep 10 (Computer Lab A offline)
    fc2 = generate_forecast('Computer Lab A', '2023-09-10', '14:00')
    print(f"\nComputer Lab A Sep 10 14:00 (infra incident):")
    print(f"  Observed forecast: {fc2.predicted_occupancy_pct}%  Status: {fc2.predicted_status}")
    print(f"  Demand forecast:   {fc2.predicted_demand_pct}%")
    print(f"  Cause: {fc2.cause}  Cold-start: {fc2.is_cold_start}")

    # Fest day: Sep 15 (cafeteria spike)
    fc3 = generate_forecast('Central Cafeteria', '2023-09-15', '12:30')
    print(f"\nCentral Cafeteria Sep 15 12:30 (fest):")
    print(f"  Observed forecast: {fc3.predicted_occupancy_pct}%  Status: {fc3.predicted_status}")
    print(f"  Cause: {fc3.cause}")

    # Exam week: Sep 26 (library surge)
    fc4 = generate_forecast('Main Library', '2023-09-26', '20:00')
    print(f"\nMain Library Sep 26 20:00 (exam week):")
    print(f"  Observed forecast: {fc4.predicted_occupancy_pct}%  Status: {fc4.predicted_status}")
    print(f"  Cause: {fc4.cause}")

    # Full daily forecast
    daily = generate_daily_forecast('Gymnasium', '2023-09-12')
    print(f"\nGymnasium daily forecast Sep 12: {len(daily)} slots")
    peak = max(daily, key=lambda x: x.predicted_occupancy_pct)
    print(f"  Peak: {peak.time_slot} at {peak.predicted_occupancy_pct}% ({peak.predicted_status})")
    print(f"  Peak demand: {peak.predicted_demand_pct}%")
