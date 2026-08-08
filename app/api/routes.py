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
