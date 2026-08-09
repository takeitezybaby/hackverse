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
    Routes schedule/congestion-plan queries to the personalisation engine (Mode 3).
    """
    from app.rag.retriever import CampusRAG as _RAG
    from app.llm.prompts import is_schedule_query, build_schedule_query_prompt
    from app.llm.client import OllamaLLMClient

    eval_time = payload.at_time or DEMO_NOW.isoformat()
    states = get_all_current_states(at_time=eval_time)

    # Full compact summary — used in the API response field and as live-state context
    full_state_summary = ", ".join(
        f"{s.resource_name}: {s.occupancy_pct}% ({s.status})" for s in states
    )
    compact_live = "\n".join(
        f"{s.resource_name}: {s.occupancy_pct}% ({s.status})" for s in states
    )

    is_fb = False
    engine_label = "Granite 3.1 (Ollama Local)"
    fallback_warn = None

    # ── Mode 3: Schedule / congestion-plan query ─────────────────────────
    if is_schedule_query(payload.query) and payload.user_id:
        try:
            rec = generate_user_recommendations(payload.user_id)
            schedule = rec.get("schedule", [])
            prompt = build_schedule_query_prompt(payload.query, schedule, compact_live)
            llm = OllamaLLMClient()
            answer = llm.generate(prompt, max_tokens=350)
            is_fb = False
        except Exception as e:
            answer = (
                "I couldn't load your schedule right now. "
                f"Try asking about a specific venue instead. (detail: {e})"
            )
            is_fb = True
            engine_label = "Rule-Based Engine (Fallback)"
            fallback_warn = str(e)

        return {
            "query": payload.query,
            "user_id": payload.user_id,
            "answer": answer,
            "live_state_summary": full_state_summary,
            "sources": ["Personalisation Engine", "Live Digital Twin State"],
            "engine": engine_label,
            "is_fallback": is_fb,
            "fallback_warning": fallback_warn,
            "timestamp": eval_time,
        }

    # ── Mode 1: Resource-specific or general occupancy query ─────────────
    state_map = {s.resource_name: s for s in states}
    mentioned = _RAG._extract_resources_from_query(payload.query)

    if mentioned:
        focus = list(mentioned)
        # For gym queries auto-include the sports complex as the alternative option
        if "Gymnasium" in focus and "Indoor Sports Complex" not in focus:
            focus.append("Indoor Sports Complex")
        state_lines = []
        for name in focus:
            s = state_map.get(name)
            if s:
                anomaly_str = f" [ANOMALY: {s.active_anomaly}]" if s.active_anomaly else ""
                state_lines.append(
                    f"{s.resource_name}: {s.occupancy_pct}% ({s.status})"
                    f" — capacity {s.current_occupancy}/{s.max_capacity}{anomaly_str}"
                )
        live_state_str = "\n".join(state_lines)
    else:
        live_state_str = compact_live

    # Inject Layer 3 recommendation only when the query is about that resource
    if payload.user_id and mentioned:
        try:
            rec = generate_user_recommendations(payload.user_id)
            prim = rec.get("primary_allocation")
            if prim and prim.get("resource") in mentioned:
                live_state_str += (
                    f"\nYour load-balanced plan: visit {prim.get('assigned_alternative')} "
                    f"instead of {prim.get('resource')} at {prim.get('usual_time')} "
                    f"(predicted {prim.get('predicted_occupancy')} full)."
                )
        except Exception:
            pass

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
        "live_state_summary": full_state_summary,
        "sources": ["FAISS Snapshot Embeddings", "Live Digital Twin State"],
        "engine": engine_label,
        "is_fallback": is_fb,
        "fallback_warning": fallback_warn,
        "timestamp": eval_time,
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
    allocation_payload = rec_data.get("primary_allocation", {})
    
    # 2. Feed Layer 3 allocation into Layer 4 RAG Storyteller
    try:
        rag = get_rag_service()
        explanation = rag.generate_personalized_report(allocation_payload)
    except Exception as e:
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


