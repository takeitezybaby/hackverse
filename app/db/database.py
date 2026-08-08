import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "campus_twin.db"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS user_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, resource_name TEXT,
            checkin_time TEXT, checkout_time TEXT, duration_min INTEGER, day_of_week TEXT,
            is_planned BOOLEAN, source TEXT, rerouted_from TEXT
        );
        CREATE TABLE IF NOT EXISTS timetables (
            course_id TEXT, course_name TEXT, department TEXT, room TEXT,
            building TEXT, day_of_week TEXT, start_time TEXT, end_time TEXT
        );
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY, name TEXT, department TEXT, year INTEGER,
            enrolled_courses TEXT, usual_patterns TEXT
        );
        CREATE TABLE IF NOT EXISTS resource_logs (
            resource_name TEXT, timestamp TEXT, current_occupancy INTEGER,
            max_capacity INTEGER, occupancy_pct REAL, status_bucket TEXT
        );
        CREATE TABLE IF NOT EXISTS crowdsourced_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, resource_name TEXT,
            report_type TEXT, timestamp TEXT, comment TEXT
        );
        CREATE TABLE IF NOT EXISTS anomalies (
            id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT, start TEXT,
            end TEXT, affected_resource TEXT, affected_course TEXT
        );
    ''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()