import sqlite3
import json
import os
from typing import Dict, Any, Optional
from app.db.database import DB_PATH

_USERS_CACHE: Optional[Dict[str, Dict[str, Any]]] = None

def load_all_users_json() -> Dict[str, Dict[str, Any]]:
    global _USERS_CACHE
    if _USERS_CACHE is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        json_path = os.path.join(base_dir, 'data', 'users.json')
        _USERS_CACHE = {}
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    users_list = json.load(f)
                    for u in users_list:
                        _USERS_CACHE[u['user_id']] = u
            except Exception as e:
                print(f"Warning: Could not load users.json: {e}")
    return _USERS_CACHE


def get_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Retrieves student profile (name, department, year, enrolled courses, usual patterns)
    from SQLite DB or fallback users.json.
    """
    # 1. Try SQLite DB
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                patterns = json.loads(row['usual_patterns']) if isinstance(row['usual_patterns'], str) else row['usual_patterns']
                courses = json.loads(row['enrolled_courses']) if isinstance(row['enrolled_courses'], str) else row['enrolled_courses']
                return {
                    "user_id": row['user_id'],
                    "name": row['name'],
                    "department": row['department'],
                    "year": row['year'],
                    "enrolled_courses": courses,
                    "usual_patterns": patterns
                }
        except Exception as e:
            print(f"Notice: DB query for user {user_id} fallback to JSON: {e}")

    # 2. Fallback to JSON cache
    users_dict = load_all_users_json()
    if user_id in users_dict:
        return users_dict[user_id]

    # 3. Default fallback for unknown IDs
    return {
        "user_id": user_id,
        "name": f"Student {user_id}",
        "department": "CS",
        "year": 4,
        "enrolled_courses": ["CS325", "AI401"],
        "usual_patterns": {
            "Gymnasium_routine": {
                "resource": "Gymnasium",
                "days": ["Tue", "Thu"],
                "usual_time": "19:00",
                "duration_min": 60,
                "source": "routine"
            },
            "Main Library_routine": {
                "resource": "Main Library",
                "days": ["Mon", "Wed"],
                "usual_time": "15:00",
                "duration_min": 120,
                "source": "routine"
            }
        }
    }
