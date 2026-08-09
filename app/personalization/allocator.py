import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from app.personalization.profile import get_user_profile
from app.twin.forecast import generate_forecast
from data_gen.config import DEMO_NOW

_ALTERNATIVES_CACHE: Optional[List[Dict[str, Any]]] = None

def load_alternatives() -> List[Dict[str, Any]]:
    global _ALTERNATIVES_CACHE
    if _ALTERNATIVES_CACHE is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        json_path = os.path.join(base_dir, 'data', 'alternatives.json')
        _ALTERNATIVES_CACHE = []
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    _ALTERNATIVES_CACHE = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load alternatives.json: {e}")
    return _ALTERNATIVES_CACHE


def generate_user_recommendations(user_id: str, target_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Layer 3 Personalization Engine:
    Evaluates student's routine visit patterns against Layer 2's 7-Step Forecast.
    If predicted congestion exceeds threshold (>=75%), calculates load-balanced alternative schedule.
    Produces exact allocation_payload required by Layer 4 RAG LLM engine + React UI schedule.
    """
    if not target_date:
        target_date = DEMO_NOW.strftime("%Y-%m-%d")

    profile = get_user_profile(user_id)
    patterns = profile.get("usual_patterns", {})
    alternatives_pool = load_alternatives()

    schedule_items = []
    primary_allocation_payload = None
    load_balance_score = 95

    item_idx = 1
    for key, pat in patterns.items():
        res_name = pat.get("resource")
        usual_time = pat.get("usual_time", "12:00")
        
        if not res_name:
            continue

        # Query Layer 2 Forecast for this resource at usual_time
        try:
            fc_list = generate_forecast(res_name, target_date)
            # Find closest 15-min slot
            matching_slot = next((s for s in fc_list if s.time_slot == usual_time), None)
            if not matching_slot and fc_list:
                matching_slot = fc_list[0]
            
            pred_occ = matching_slot.predicted_occupancy_pct if matching_slot else 50.0
            pred_demand = matching_slot.predicted_demand_pct if matching_slot else pred_occ
            cause_str = matching_slot.cause if matching_slot else "Normal routine"
        except Exception as e:
            pred_occ = 85.0
            pred_demand = 85.0
            cause_str = "Peak demand"

        is_congested = pred_occ >= 75.0
        
        # Look up load-balanced alternative
        rec_time = usual_time
        rec_location = res_name
        rec_occ = pred_occ
        time_saved = 0
        rec_reasoning = "Occupancy within normal capacity limits."

        if is_congested:
            load_balance_score -= 5
            # Search for matching alternative in pool
            match_alts = [a for a in alternatives_pool if a.get("original_resource") == res_name]
            if match_alts:
                best_alt = match_alts[0]
                rec_reasoning = f"{res_name} predicted to hit {int(pred_occ)}% congestion peak at {usual_time}."
                if best_alt.get("alt_type") == "time_shift":
                    s_time = best_alt.get("suggested_time", "")
                    if "→" in s_time:
                        rec_time = s_time.split("→")[1]
                    rec_occ = max(35.0, pred_occ - 34.0)
                    time_saved = 25
                    rec_reasoning += f" Shifting visit to {rec_time} avoids wait times."
                elif best_alt.get("alt_type") == "location_shift":
                    rec_location = best_alt.get("alt_resource", res_name)
                    rec_occ = max(40.0, pred_occ - 30.0)
                    time_saved = 20
                    rec_reasoning += f" Redirecting to {rec_location} balances capacity."
            else:
                # Fallback shift 30 min earlier
                try:
                    t_obj = datetime.strptime(usual_time, "%H:%M") - timedelta(minutes=30)
                    rec_time = t_obj.strftime("%H:%M")
                except Exception:
                    rec_time = "18:30"
                rec_occ = max(45.0, pred_occ - 30.0)
                time_saved = 25
                rec_reasoning = f"Predicted congestion peak ({int(pred_occ)}%) at {usual_time}. Early entry at {rec_time} saves 25 mins."

            if not primary_allocation_payload:
                primary_allocation_payload = {
                    "user_id": user_id,
                    "student_name": profile.get("name", f"Student {user_id}"),
                    "resource": res_name,
                    "usual_time": usual_time,
                    "predicted_occupancy": f"{int(pred_occ)}%",
                    "assigned_alternative": rec_time if rec_time != usual_time else rec_location,
                    "reason": rec_reasoning
                }

        schedule_items.append({
            "id": f"sched_{item_idx}",
            "category": "workout" if "gym" in res_name.lower() else "study",
            "status": "pending",
            "habit": {
                "id": f"h_{item_idx}",
                "time": usual_time,
                "activity": f"{res_name} Visit",
                "location": res_name,
                "usualOccupancy": int(pred_occ),
                "isCongested": is_congested,
                "statusText": f"Predicted: {int(pred_occ)}% Full ({cause_str})"
            },
            "recommendation": {
                "id": f"r_{item_idx}",
                "time": rec_time,
                "activity": f"{rec_location} (Alternative)",
                "location": rec_location,
                "predictedOccupancy": int(rec_occ),
                "timeSavedMinutes": time_saved,
                "statusText": f"Predicted: {int(rec_occ)}% Full",
                "reasoning": rec_reasoning
            }
        })
        item_idx += 1

    # Fallback primary payload if all routines were low-occupancy
    if not primary_allocation_payload:
        primary_allocation_payload = None

    return {
        "user_id": user_id,
        "student_name": profile.get("name", f"Student {user_id}"),
        "load_balance_score": max(70, load_balance_score),
        "primary_allocation": primary_allocation_payload,
        "schedule": schedule_items
    }


def generate_personalized_day_schedule(user_id: str = "u_0042") -> dict:
    """
    Analyzes the user's usual daily routine habits against Layer 2 congestion forecasts.
    Generates a complete personalized day schedule with before/after comparison and
    suggested time/venue shifts for each item throughout the day.
    """
    rec_data = generate_user_recommendations(user_id)
    student_name = rec_data.get("student_name", f"Student {user_id}")
    schedule_items = rec_data.get("schedule", [])
    
    itinerary = []
    total_time_saved = 0
    shifts_suggested = 0
    
    for item in schedule_items:
        h = item.get("habit", {})
        r = item.get("recommendation", {})
        usual_t = h.get("time", "")
        usual_loc = h.get("location", "")
        usual_occ = h.get("usualOccupancy", 50)
        is_c = h.get("isCongested", False)
        
        rec_t = r.get("time", usual_t)
        rec_loc = r.get("location", usual_loc)
        rec_occ = r.get("predictedOccupancy", usual_occ)
        reason = r.get("reasoning", "Optimal slot.")
        saved = r.get("timeSavedMinutes", 0)
        
        if is_c:
            shifts_suggested += 1
            total_time_saved += saved
            if rec_loc != usual_loc:
                action_label = f"Redirect to {rec_loc}"
            else:
                action_label = f"Shift time to {rec_t}"
        else:
            action_label = "Confirmed (No change needed)"
        
        itinerary.append({
            "usual_time": usual_t,
            "usual_location": usual_loc,
            "usual_occupancy": f"{usual_occ}%",
            "is_congested": is_c,
            "optimized_time": rec_t,
            "optimized_location": rec_loc,
            "optimized_occupancy": f"{rec_occ}%",
            "action": action_label,
            "reason": reason,
            "time_saved_mins": saved
        })

    # Sort chronologically by usual_time
    itinerary.sort(key=lambda x: x["usual_time"])
    
    return {
        "user_id": user_id,
        "student_name": student_name,
        "load_balance_score": rec_data.get("load_balance_score", 92),
        "total_routine_visits": len(itinerary),
        "shifts_suggested": shifts_suggested,
        "total_time_saved_mins": total_time_saved,
        "itinerary": itinerary
    }
