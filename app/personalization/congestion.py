"""
app/personalization/congestion.py

Congestion Matcher & Risk Evaluator for Layer 3 Personalization.
Evaluates resource congestion thresholds, computes status buckets, 
and matches user routines against live forecasts to identify congestion risks
and safe alternative time windows.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.twin.forecast import generate_forecast
from data_gen.config import DEMO_NOW

# ============================================================
# CONGESTION CONFIGURATION & THRESHOLDS
# ============================================================

DEFAULT_CONGESTION_THRESHOLD = 75.0  # Occupancy % threshold for congestion risk

STATUS_THRESHOLDS = [
    (15.0, "empty"),
    (40.0, "low"),
    (70.0, "moderate"),
    (85.0, "high"),
    (95.0, "full"),
    (float("inf"), "overflow")
]


def get_status_bucket(occupancy_pct: float) -> str:
    """
    Returns a human-readable status bucket string (empty, low, moderate, high, full, overflow)
    based on the given occupancy percentage.
    """
    for limit, status in STATUS_THRESHOLDS:
        if occupancy_pct < limit:
            return status
    return "overflow"


def is_resource_congested(occupancy_pct: float, threshold: float = DEFAULT_CONGESTION_THRESHOLD) -> bool:
    """
    Returns True if occupancy meets or exceeds the congestion threshold.
    """
    return occupancy_pct >= threshold


def evaluate_routine_congestion(
    resource_name: str,
    usual_time: str,
    target_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluates forecast congestion for a specific resource at a given routine time slot.
    
    Returns:
        Dict containing predicted occupancy, demand, status bucket, congestion flag, and cause.
    """
    if not target_date:
        target_date = DEMO_NOW.strftime("%Y-%m-%d")

    try:
        fc_list = generate_forecast(resource_name, target_date)
        matching_slot = next((s for s in fc_list if s.time_slot == usual_time), None)
        if not matching_slot and fc_list:
            matching_slot = fc_list[0]

        pred_occ = matching_slot.predicted_occupancy_pct if matching_slot else 50.0
        pred_demand = matching_slot.predicted_demand_pct if matching_slot else pred_occ
        cause = matching_slot.cause if matching_slot else "Normal routine"
    except Exception as e:
        pred_occ = 85.0
        pred_demand = 85.0
        cause = "Peak demand"

    congested = is_resource_congested(pred_occ)
    status_bucket = get_status_bucket(pred_occ)

    return {
        "resource": resource_name,
        "date": target_date,
        "usual_time": usual_time,
        "predicted_occupancy": pred_occ,
        "predicted_demand": pred_demand,
        "status_bucket": status_bucket,
        "is_congested": congested,
        "cause": cause
    }


def find_safe_time_window(
    resource_name: str,
    usual_time: str,
    target_date: Optional[str] = None,
    window_minutes: int = 60,
    max_acceptable_occ: float = 60.0
) -> Optional[Dict[str, Any]]:
    """
    Searches within +/- window_minutes around usual_time for the quietest/safest time slot
    for the same resource.
    """
    if not target_date:
        target_date = DEMO_NOW.strftime("%Y-%m-%d")

    try:
        usual_dt = datetime.strptime(usual_time, "%H:%M")
        fc_list = generate_forecast(resource_name, target_date)
        
        candidates = []
        for slot in fc_list:
            try:
                slot_dt = datetime.strptime(slot.time_slot, "%H:%M")
                diff = abs((slot_dt - usual_dt).total_seconds()) / 60.0
                if 0 < diff <= window_minutes:
                    candidates.append({
                        "time_slot": slot.time_slot,
                        "occupancy": slot.predicted_occupancy_pct,
                        "diff_minutes": diff
                    })
            except ValueError:
                continue

        if not candidates:
            return None

        # Filter by safe occupancy and pick lowest occupancy, then closest time
        safe_candidates = [c for c in candidates if c["occupancy"] <= max_acceptable_occ]
        pool = safe_candidates if safe_candidates else candidates
        
        best_slot = min(pool, key=lambda c: (c["occupancy"], c["diff_minutes"]))
        return best_slot

    except Exception:
        return None