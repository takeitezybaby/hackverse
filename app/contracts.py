"""
SHARED CONTRACTS — Campus Digital Twin
=======================================
This file defines ALL data structures shared between layers.
EVERY team member imports from here. NEVER define these shapes inline.

Rule: If you need to change a contract, announce it in the group chat first.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum
import json


# ─── Status Buckets (Layer 2) ───────────────────────────────────────────

class StatusBucket(str, Enum):
    EMPTY = "empty"          # <20%
    LOW = "low"              # 20-40%
    MODERATE = "moderate"    # 40-65%
    HIGH = "high"            # 65-85%
    FULL = "full"            # 85-95%
    OVERFLOW = "overflow"    # >95%

    @classmethod
    def from_pct(cls, pct: float) -> "StatusBucket":
        if pct < 20: return cls.EMPTY
        if pct < 40: return cls.LOW
        if pct < 65: return cls.MODERATE
        if pct < 85: return cls.HIGH
        if pct < 95: return cls.FULL
        return cls.OVERFLOW


# ─── Resource Definition (shared across all layers) ─────────────────────

RESOURCES = {
    "main_library":              {"name": "Main Library",              "capacity": 300},
    "science_library":           {"name": "Science Library",           "capacity": 120},
    "central_cafeteria":         {"name": "Central Cafeteria",         "capacity": 250},
    "food_court":                {"name": "Food Court",                "capacity": 200},
    "gymnasium":                 {"name": "Gymnasium",                 "capacity": 80},
    "indoor_sports_complex":     {"name": "Indoor Sports Complex",     "capacity": 100},
    "student_center":            {"name": "Student Center",            "capacity": 150},
    "computer_lab_a":            {"name": "Computer Lab A",            "capacity": 60},
    "computer_lab_b":            {"name": "Computer Lab B",            "capacity": 60},
    "wifi_zone_academic_block":  {"name": "WiFi Zone - Academic Block","capacity": 500},
    "wifi_zone_library":         {"name": "WiFi Zone - Library",       "capacity": 200},
    "wifi_zone_cafeteria":       {"name": "WiFi Zone - Cafeteria",     "capacity": 300},
}

def get_resource_slug(name: str) -> str:
    """Convert display name to slug. Use this everywhere for consistency."""
    return name.lower().replace(' ', '_').replace('-', '_').replace('__', '_')


# ─── Layer 1 → Layer 2: Ingestion payloads ──────────────────────────────

@dataclass
class ResourceReading:
    """A single occupancy reading for a resource."""
    resource_name: str
    timestamp: str           # ISO format: "2023-09-05T14:30:00"
    current_occupancy: int
    max_capacity: int

    @property
    def occupancy_pct(self) -> float:
        return (self.current_occupancy / self.max_capacity * 100) if self.max_capacity > 0 else 0.0

    @property
    def status(self) -> StatusBucket:
        return StatusBucket.from_pct(self.occupancy_pct)


@dataclass
class UserCheckin:
    """A user check-in / wifi-connect event."""
    user_id: str
    resource_name: str
    checkin_time: str         # ISO format
    checkout_time: Optional[str] = None
    duration_min: Optional[int] = None


@dataclass
class CrowdsourcedReport:
    """A user-submitted report like 'library is full'."""
    user_id: str
    resource_name: str
    report_type: str          # "full" | "moderate" | "empty" | "issue"
    timestamp: str
    comment: Optional[str] = None


# ─── Layer 2 → Layer 3: Forecast output ─────────────────────────────────

@dataclass
class ForecastSlot:
    """Predicted occupancy for a resource at a specific time."""
    resource_name: str
    time_slot: str            # "HH:MM" format
    predicted_occupancy_pct: float
    predicted_status: str     # StatusBucket value
    confidence: float         # 0.0 - 1.0
    date: str                 # "YYYY-MM-DD"


# ─── Layer 3 → Layer 4/5: Personalization output ────────────────────────

@dataclass
class PersonalizedRecommendation:
    """Output from the personalization engine for one user."""
    user_id: str
    resource: str
    usual_time: str
    predicted_occupancy_pct: float
    predicted_status: str
    assigned_alternative: str           # suggested time or location
    alternative_type: str               # "time_shift" | "location_shift"
    alternative_predicted_pct: float    # predicted occupancy at alternative
    reason: str                         # human-readable reason
    priority: int = 1                   # 1 = best option

    def to_dict(self) -> dict:
        return asdict(self)


# ─── Layer 4: RAG / LLM context ─────────────────────────────────────────

@dataclass
class LLMContext:
    """Structured context passed to the LLM for grounded responses."""
    user_query: str
    resource_name: Optional[str] = None
    current_forecast: Optional[Dict] = None       # ForecastSlot as dict
    user_recommendation: Optional[Dict] = None    # PersonalizedRecommendation as dict
    similar_past_days: Optional[List[Dict]] = None # Retrieved from RAG
    user_profile: Optional[Dict] = None           # User's usual patterns

    def to_prompt_context(self) -> str:
        """Format as a string block for LLM prompt injection."""
        parts = []
        if self.current_forecast:
            parts.append(f"FORECAST: {json.dumps(self.current_forecast)}")
        if self.user_recommendation:
            parts.append(f"RECOMMENDATION: {json.dumps(self.user_recommendation)}")
        if self.similar_past_days:
            parts.append(f"SIMILAR PAST DAYS: {json.dumps(self.similar_past_days)}")
        if self.user_profile:
            parts.append(f"USER PROFILE: {json.dumps(self.user_profile)}")
        return "\n".join(parts)


# ─── Layer 5: API response models ───────────────────────────────────────

@dataclass
class DailyReportResponse:
    """The 'Your Day' card response for a user."""
    user_id: str
    user_name: str
    date: str
    recommendations: List[Dict]          # List of PersonalizedRecommendation dicts
    llm_summary: str                     # Natural language summary from LLM
    resource_overview: List[Dict]        # Current status of all resources


@dataclass
class AskResponse:
    """Response to a natural language query."""
    query: str
    answer: str
    sources: List[str]                   # Which data sources were used
    resource_context: Optional[Dict] = None


# ─── Database table names (Layer 1) ─────────────────────────────────────

DB_FILE = "campus_twin.db"

TABLE_RESOURCE_LOGS = "resource_logs"
TABLE_USER_CHECKINS = "user_checkins"
TABLE_CROWDSOURCED_REPORTS = "crowdsourced_reports"
TABLE_ALTERNATIVES = "alternatives"
TABLE_FORECASTS = "forecasts"
TABLE_USERS = "users"
TABLE_TIMETABLES = "timetables"
