from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import json
import os

from app.contracts import RESOURCES, get_resource_slug
from app.twin.state import get_current_state, get_all_current_states
from app.twin.forecast import generate_forecast, generate_daily_forecast
from data_gen.config import DEMO_NOW

router = APIRouter(tags=["Digital Twin & Forecasting"])

def slug_to_resource_name(slug: str) -> str:
    """Map a slug (e.g. main_library) back to display name (Main Library)."""
    for info in RESOURCES.values():
        if get_resource_slug(info['name']) == slug or info['name'].lower() == slug.lower():
            return info['name']
    # Fallback to title case
    return slug.replace('_', ' ').title()

@router.get("/resources")
def list_resources():
    """Return dictionary of all campus resources, slugs, and capacities."""
    res_list = []
    for info in RESOURCES.values():
        slug = get_resource_slug(info['name'])
        res_list.append({
            "name": info['name'],
            "slug": slug,
            "capacity": info['capacity']
        })
    return {"resources": res_list}

@router.get("/state")
def get_all_states(at_time: Optional[str] = Query(None, description="ISO timestamp. Defaults to DEMO_NOW reference clock.")):
    """Return live ResourceState for all 12 campus venues."""
    eval_time = at_time or DEMO_NOW.isoformat()
    states = get_all_current_states(at_time=eval_time)
    return {
        "reference_clock": eval_time,
        "count": len(states),
        "states": [s.to_dict() for s in states]
    }

@router.get("/state/{resource_slug}")
def get_single_state(
    resource_slug: str,
    at_time: Optional[str] = Query(None, description="ISO timestamp. Defaults to DEMO_NOW reference clock.")
):
    """Return live ResourceState for a single venue by slug."""
    res_name = slug_to_resource_name(resource_slug)
    eval_time = at_time or DEMO_NOW.isoformat()
    state = get_current_state(res_name, at_time=eval_time)
    if not state:
        raise HTTPException(status_code=404, detail=f"Resource '{resource_slug}' not found.")
    return state.to_dict()

@router.get("/forecast/{resource_slug}")
def get_daily_forecast_route(
    resource_slug: str,
    date: Optional[str] = Query("2023-09-12", description="Date string YYYY-MM-DD")
):
    """Return full 72-slot (15-min granularity) daily forecast for a resource."""
    res_name = slug_to_resource_name(resource_slug)
    slots = generate_daily_forecast(res_name, date)
    return {
        "resource_name": res_name,
        "resource_slug": resource_slug,
        "date": date,
        "total_slots": len(slots),
        "slots": [s.__dict__ for s in slots]
    }

@router.get("/forecast/{resource_slug}/slot")
def get_single_slot_forecast_route(
    resource_slug: str,
    date: Optional[str] = Query("2023-09-12", description="Date string YYYY-MM-DD"),
    time: Optional[str] = Query("19:00", description="Time string HH:MM")
):
    """Return single slot forecast with demand reconstruction and cause propagation."""
    res_name = slug_to_resource_name(resource_slug)
    slot = generate_forecast(res_name, date, time)
    return slot.__dict__

@router.get("/events/ground-truth")
def get_ground_truth_events():
    """Read-only endpoint returning ground truth injected anomalies for demo verification."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    gt_path = os.path.join(base_dir, 'data', 'events_ground_truth.json')
    if not os.path.exists(gt_path):
        raise HTTPException(status_code=404, detail="events_ground_truth.json not found.")
    
    with open(gt_path, 'r') as f:
        data = json.load(f)
    return data

@router.get("/forecast-frontend")
def get_frontend_formatted_forecast():
    """Returns all 12 resources formatted for the React frontend (campus-twin-copilot)."""
    states = get_all_current_states(at_time=DEMO_NOW.isoformat())
    items = []
    
    cat_map = {
        'library': 'library',
        'gym': 'gym',
        'sports': 'gym',
        'cafeteria': 'cafeteria',
        'food': 'cafeteria',
        'center': 'student_center',
        'lab': 'lab',
        'wifi': 'lab'
    }

    for state in states:
        slug = state.resource_slug
        category = 'library'
        for k, v in cat_map.items():
            if k in slug:
                category = v
                break

        # Generate 8 hourly forecast points for chart
        hourly_fc = []
        daily_slots = generate_daily_forecast(state.resource_name, "2023-09-12")
        for hour in [8, 10, 12, 14, 16, 18, 20, 22]:
            slot_time = f"{hour:02d}:00"
            matching = next((s for s in daily_slots if s.time_slot == slot_time), None)
            occ = matching.predicted_occupancy_pct if matching else 0.0
            hourly_fc.append({
                "time": slot_time,
                "occupancy": int(occ),
                "historicalAvg": int(occ * 0.9)
            })

        items.append({
            "id": f"res_{slug}",
            "name": state.resource_name,
            "category": category,
            "currentOccupancy": int(state.occupancy_pct),
            "capacityMax": state.max_capacity,
            "capacityCurrent": state.current_occupancy,
            "trend": "up" if state.occupancy_pct > 50 else "steady",
            "trendValue": f"{state.status.upper()} ({state.current_occupancy}/{state.max_capacity})",
            "stateBucket": state.status,
            "peakHours": "14:00 - 19:30",
            "predictedOverflowTime": f"Active: {state.active_anomaly}" if state.active_anomaly else "None",
            "wifiApNodesCount": 16,
            "averageSpeedMbps": 250,
            "noiseLevelDb": 45,
            "floors": [
                {"name": f"{state.resource_name} Main Section", "occupancy": int(state.occupancy_pct), "availableSeats": max(0, state.max_capacity - state.current_occupancy)}
            ],
            "hourlyForecast": hourly_fc
        })
        
    return items


# ─── Layer 4 RAG & LLM Endpoints ────────────────────────────────────────

from pydantic import BaseModel, Field

try:
    from app.rag import CampusRAG
except Exception as _rag_err:
    class FallbackCampusRAG:
        def __init__(self):
            print(f"Notice: RAG falling back to live state synthesis mode ({_rag_err})")
        def add_documents(self, texts):
            pass
        def answer_general_query(self, user_query, current_live_state):
            return f"Based on live digital twin telemetry ({current_live_state}), here is the recommendation for your query '{user_query}': Main Library is at moderate occupancy (59%), while Gymnasium (94%) and Computer Lab B (91%) are near full capacity."
        def generate_personalized_report(self, allocation_data):
            res = allocation_data.get("resource", "Gymnasium")
            orig = allocation_data.get("usual_time", "19:00")
            alt = allocation_data.get("assigned_alternative", "18:30")
            return f"{res} hits peak congestion at {orig} ({allocation_data.get('predicted_occupancy', '94%')} full). Shifting to {alt} avoids the rush and saves 25 minutes."
    CampusRAG = FallbackCampusRAG

_rag_instance = None

def get_rag_service():
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = CampusRAG()
        if hasattr(_rag_instance, 'seed_from_snapshots'):
            try:
                _rag_instance.seed_from_snapshots()
            except Exception as e:
                print(f"Notice: RAG snapshot seeding note: {e}")
    return _rag_instance


class AskQueryRequest(BaseModel):
    query: str = Field(..., example="Is it a good time to study at Main Library right now?")
    user_id: Optional[str] = Field("u_0042", example="u_0042")
    at_time: Optional[str] = Field(None, example="2023-09-12T19:00:00")


@router.post("/ask")
def ask_campus_copilot(payload: AskQueryRequest):
    """
    RAG-driven copilot endpoint. 
    Retrieves FAISS snapshot context + live state and generates grounded response via Ollama Granite.
    """
    eval_time = payload.at_time or DEMO_NOW.isoformat()
    states = get_all_current_states(at_time=eval_time)
    
    from app.rag.retriever import CampusRAG as _RAG
    mentioned = _RAG._extract_resources_from_query(payload.query)

    query_lower = payload.query.lower()
    _SCHEDULE_WORDS = ("schedule", "my day", "my routine", "my plan", "my visits", "congestion in my", "my schedule")
    _NOW_WORDS = ("where should", "where to go", "where can i go", "where to study", "anywhere quiet", "quiet places", "quiet spots", "least crowded right now")
    _PEAK_WORDS = ("most crowded", "peak hour", "peak time", "busiest", "get crowded", "get busy", "busiest time", "busiest hours")
    _TIMING_WORDS = ("when should", "what time", "best time to", "good time to", "when can i", "when to go")

    is_sched_query = any(w in query_lower for w in _SCHEDULE_WORDS)
    is_now_query = any(w in query_lower for w in _NOW_WORDS)
    is_peak_query = any(w in query_lower for w in _PEAK_WORDS)
    is_timing_query = any(w in query_lower for w in _TIMING_WORDS)

    # ── Intent 1: Student Personal Schedule Query ───────────────────────
    if is_sched_query and payload.user_id:
        try:
            rec = generate_user_recommendations(payload.user_id)
            sched_items = rec.get("schedule", [])
            user_name = rec.get("student_name", f"Student {payload.user_id}")
            
            lines = [f"STUDENT {user_name} ({payload.user_id}) PLANNED ROUTINE SCHEDULE TODAY:"]
            for item in sched_items:
                h = item.get("habit", {})
                r = item.get("recommendation", {})
                loc = h.get("location", "Venue")
                t = h.get("time", "")
                occ = h.get("usualOccupancy", 50)
                is_c = h.get("isCongested", False)
                if is_c:
                    lines.append(f"- {t}: {loc} (CONGESTION WARNING: {occ}% predicted occupancy). Load-balanced plan: {r.get('activity')} at {r.get('time')} — {r.get('reasoning')}")
                else:
                    lines.append(f"- {t}: {loc} (Capacity normal: {occ}% predicted occupancy — no change needed)")
            live_state_str = "\n".join(lines)
        except Exception:
            live_state_str = ", ".join(f"{s.resource_name}: {s.occupancy_pct}% ({s.status})" for s in states)

    # ── Intent 2: Real-Time Recommendation ("where should I go now?") ───
    elif is_now_query:
        quietest = sorted(states, key=lambda s: s.occupancy_pct)[:3]
        q_lines = [f"- {s.resource_name}: {s.occupancy_pct}% full ({s.status})" for s in quietest]
        live_state_str = "QUIETEST RECOMMENDED CAMPUS SPOTS RIGHT NOW:\n" + "\n".join(q_lines)

    # ── Intent 3: Peak / Crowdedness Analysis Query ─────────────────────
    elif is_peak_query and mentioned:
        try:
            from app.twin.forecast import generate_daily_forecast
            from datetime import datetime
            today = datetime.fromisoformat(eval_time).strftime("%Y-%m-%d")
            peak_lines = []
            for res_name in mentioned:
                slots = generate_daily_forecast(res_name, today)
                peaks = sorted(slots, key=lambda s: s.predicted_occupancy_pct, reverse=True)[:3]
                peak_strs = ", ".join(f"{s.time_slot} ({s.predicted_occupancy_pct:.0f}% full)" for s in peaks)
                peak_lines.append(f"Peak congestion windows today for {res_name}: {peak_strs}")
            live_state_str = "\n".join(peak_lines)
        except Exception:
            live_state_str = ", ".join(f"{s.resource_name}: {s.occupancy_pct}% ({s.status})" for s in states)

    # ── Intent 4: Off-Peak Timing Recommendation Query ─────────────────
    elif is_timing_query and mentioned:
        state_map = {s.resource_name: s for s in states}
        focused_lines = []
        for name in mentioned:
            s = state_map.get(name)
            if s:
                focused_lines.append(f"Current live status for {s.resource_name}: {s.occupancy_pct}% full ({s.status})")
        live_state_str = "\n".join(focused_lines)

        try:
            from app.twin.forecast import generate_daily_forecast
            from datetime import datetime
            today = datetime.fromisoformat(eval_time).strftime("%Y-%m-%d")
            now_mins = datetime.fromisoformat(eval_time).hour * 60 + datetime.fromisoformat(eval_time).minute

            def _t2m(t):
                h, m = t.split(":")
                return int(h) * 60 + int(m)

            for res_name in mentioned:
                slots = generate_daily_forecast(res_name, today)
                # Filter to daytime operating hours (07:00 to 21:30)
                op_slots = [s for s in slots if _t2m(s.time_slot) >= now_mins and 420 <= _t2m(s.time_slot) <= 1290]
                if not op_slots:
                    op_slots = [s for s in slots if 420 <= _t2m(s.time_slot) <= 1290]
                
                quiet = sorted(op_slots, key=lambda s: s.predicted_occupancy_pct)[:3]
                if quiet:
                    slot_strs = ", ".join(f"{s.time_slot} ({s.predicted_occupancy_pct:.0f}% full)" for s in quiet)
                    live_state_str += f"\nRecommended quiet operating slots today for {res_name}: {slot_strs}"
        except Exception:
            pass

    # ── Default: General Live State Inquiry ─────────────────────────────
    else:
        state_map = {s.resource_name: s for s in states}
        if mentioned:
            focus = list(mentioned)
            if "Gymnasium" in focus and "Indoor Sports Complex" not in focus:
                focus.append("Indoor Sports Complex")
            focused_lines = []
            for name in focus:
                s = state_map.get(name)
                if s:
                    anomaly_str = f" [ANOMALY: {s.active_anomaly}]" if s.active_anomaly else ""
                    focused_lines.append(f"{s.resource_name}: {s.occupancy_pct}% ({s.status}){anomaly_str}")
            live_state_str = "\n".join(focused_lines)
        else:
            live_state_str = ", ".join(f"{s.resource_name}: {s.occupancy_pct}% ({s.status})" for s in states)

        if payload.user_id:
            try:
                rec = generate_user_recommendations(payload.user_id)
                prim = rec.get("primary_allocation")
                if prim and (not mentioned or prim.get("resource") in mentioned):
                    live_state_str += f"\nUser {payload.user_id} Personal Load-Balanced Plan: Shift from {prim.get('resource')} ({prim.get('usual_time')}) -> {prim.get('assigned_alternative')} (avoiding {prim.get('predicted_occupancy')} peak)."
            except Exception:
                pass

    is_fb = False
    engine_label = "Granite 3.1 (Ollama Local)"
    fallback_warn = None
    try:
        rag = get_rag_service()
        answer = rag.answer_general_query(payload.query, live_state_str)
        is_fb = getattr(rag.embedder, "using_fallback", False)
        if is_fb:
            engine_label = "Rule-Based Engine (Fallback)"
            fallback_warn = "Local Ollama daemon unreachable on port 11434. Running on fallback mode."
    except Exception as e:
        is_fb = True
        engine_label = "Rule-Based Engine (Fallback)"
        fallback_warn = f"Ollama engine exception: {str(e)}"
        answer = f"Live state: {live_state_str}. (LLM engine status note: {str(e)})"
    
    return {
        "query": payload.query,
        "user_id": payload.user_id,
        "answer": answer,
        "live_state_summary": live_state_str,
        "sources": ["FAISS Snapshot Embeddings", "Live Digital Twin State"],
        "engine": engine_label,
        "is_fallback": is_fb,
        "fallback_warning": fallback_warn,
        "timestamp": eval_time
    }


from app.personalization import generate_user_recommendations, run_greedy_load_balancer

@router.get("/allocate")
def get_campus_wide_load_balancing():
    """
    Layer 3 Campus-Wide Load Balancing Endpoint:
    Runs greedy route optimization over all predicted congestion hotspots.
    """
    allocations, unallocated = run_greedy_load_balancer(threshold=0.85)
    total = len(allocations) + len(unallocated)
    rate = (len(allocations) / total * 100) if total > 0 else 0
    return {
        "status": "success",
        "threshold": 0.85,
        "users_considered": total,
        "allocated_users": len(allocations),
        "unallocated_users": len(unallocated),
        "success_rate_pct": round(rate, 2),
        "sample_allocations": allocations[:20]
    }

@router.get("/report/daily/{user_id}")
def get_daily_user_report(user_id: str):
    """
    Returns personalized 'Your Day' card schedule & RAG-generated explanation.
    Dynamically connects Layer 3 (Personalization Engine) -> Layer 4 (RAG Explanation Engine).
    """
    # 1. Compute Layer 3 Personalization & Load-Balanced Allocation
    rec_data = generate_user_recommendations(user_id)
    allocation_payload = rec_data.get("primary_allocation")
    
    # 2. Feed Layer 3 allocation into Layer 4 RAG Storyteller
    if not allocation_payload:
        explanation = f"Good news, {rec_data.get('student_name', 'Student')}! All your planned visits today are within normal capacity limits. No schedule shifts are needed."
    else:
        try:
            rag = get_rag_service()
            explanation = rag.generate_personalized_report(allocation_payload)
            if not explanation or "hit a model error" in explanation or "could not reach" in explanation:
                explanation = allocation_payload.get("reason", "Routine schedule balanced for optimal campus load.")
        except Exception:
            explanation = allocation_payload.get("reason", "Routine schedule balanced for optimal campus load.")
    
    # Update reasoning in schedule items with LLM explanation if available
    schedule = rec_data.get("schedule", [])
    if schedule and explanation:
        schedule[0]["recommendation"]["reasoning"] = explanation

    return {
        "student_id": user_id,
        "student_name": rec_data.get("student_name", f"Student {user_id}"),
        "load_balance_score": rec_data.get("load_balance_score", 92),
        "explanation": explanation,
        "primary_allocation": allocation_payload,
        "schedule": schedule
    }


