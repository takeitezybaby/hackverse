from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta
import sqlite3
import os

from app.contracts import DB_FILE, TABLE_USER_CHECKINS, TABLE_CROWDSOURCED_REPORTS
from data_gen.config import DEMO_NOW

router = APIRouter(prefix="/ingest", tags=["Ingestion"])

# Global offset for sequential live demo check-ins (advances +2 mins per live ingestion)
_demo_offset_minutes = 0

def get_db_path():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, 'data', DB_FILE)

class CheckinRequest(BaseModel):
    user_id: str = Field(..., example="u_0042")
    resource_name: str = Field(..., example="Gymnasium")
    checkin_time: Optional[str] = Field(None, description="ISO format string. If omitted, uses DEMO_NOW + offset.")
    checkout_time: Optional[str] = None
    duration_min: Optional[int] = Field(60, example=60)
    is_planned: Optional[bool] = True
    source: Optional[str] = Field("live_demo", example="live_demo")
    rerouted_from: Optional[str] = None

class ReportRequest(BaseModel):
    user_id: str = Field(..., example="u_0042")
    resource_name: str = Field(..., example="Computer Lab A")
    report_type: str = Field(..., example="full", description="full | moderate | empty | issue")
    timestamp: Optional[str] = None
    comment: Optional[str] = Field(None, example="AC is broken, very hot")

@router.post("/checkin", status_code=status.HTTP_201_CREATED)
def ingest_checkin(payload: CheckinRequest):
    global _demo_offset_minutes
    
    # Process check-in timestamp
    if not payload.checkin_time or "2026-" in payload.checkin_time:
        # Stamp with DEMO_NOW + incremental demo offset
        stamped_dt = DEMO_NOW + timedelta(minutes=_demo_offset_minutes)
        _demo_offset_minutes += 2  # Advance 2 mins for next live checkin
        checkin_time_str = stamped_dt.isoformat()
    else:
        checkin_time_str = payload.checkin_time

    duration = payload.duration_min or 60
    if not payload.checkout_time:
        in_dt = datetime.fromisoformat(checkin_time_str.replace('Z', ''))
        out_dt = in_dt + timedelta(minutes=duration)
        checkout_time_str = out_dt.isoformat()
    else:
        checkout_time_str = payload.checkout_time

    in_dt = datetime.fromisoformat(checkin_time_str.replace('Z', ''))
    day_of_week = in_dt.strftime('%A')

    db_path = get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO {TABLE_USER_CHECKINS} (
                user_id, resource_name, checkin_time, checkout_time, 
                duration_min, day_of_week, is_planned, source, rerouted_from
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.user_id, payload.resource_name, checkin_time_str, checkout_time_str,
            duration, day_of_week, payload.is_planned, payload.source, payload.rerouted_from
        ))
        checkin_id = cursor.lastrowid
        conn.commit()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to persist checkin: {str(e)}")

    return {
        "status": "created",
        "checkin_id": checkin_id,
        "user_id": payload.user_id,
        "resource_name": payload.resource_name,
        "stamped_checkin_time": checkin_time_str,
        "checkout_time": checkout_time_str,
        "demo_offset_minutes": _demo_offset_minutes
    }

@router.post("/report", status_code=status.HTTP_201_CREATED)
def ingest_report(payload: ReportRequest):
    timestamp_str = payload.timestamp or DEMO_NOW.isoformat()
    
    db_path = get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO {TABLE_CROWDSOURCED_REPORTS} (
                user_id, resource_name, report_type, timestamp, comment
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            payload.user_id, payload.resource_name, payload.report_type, timestamp_str, payload.comment
        ))
        report_id = cursor.lastrowid
        conn.commit()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to persist report: {str(e)}")

    return {
        "status": "created",
        "report_id": report_id,
        "user_id": payload.user_id,
        "resource_name": payload.resource_name,
        "report_type": payload.report_type,
        "timestamp": timestamp_str
    }
