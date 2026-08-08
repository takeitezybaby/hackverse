import sqlite3
import json
from pathlib import Path
from .database import DB_PATH

DATA_DIR = Path(__file__).parent.parent.parent / "data"

def load_json(filename):
    path = DATA_DIR / filename
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def seed_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for c in load_json('checkins.json'):
        cursor.execute('''INSERT INTO user_checkins (user_id, resource_name, checkin_time, checkout_time, duration_min, day_of_week, is_planned, source, rerouted_from) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                       (c.get('user_id'), c.get('resource_name'), c.get('checkin_time'), c.get('checkout_time'), c.get('duration_min'), c.get('day_of_week'), c.get('is_planned'), c.get('source'), c.get('rerouted_from')))

    for u in load_json('users.json'):
        cursor.execute('''INSERT INTO users (user_id, name, department, year, enrolled_courses, usual_patterns) VALUES (?, ?, ?, ?, ?, ?)''', 
                       (u.get('user_id'), u.get('name'), u.get('department'), u.get('year'), json.dumps(u.get('enrolled_courses', [])), json.dumps(u.get('usual_patterns', {}))))

    for t in load_json('timetables.json'):
        cursor.execute('''INSERT INTO timetables (course_id, course_name, department, room, building, day_of_week, start_time, end_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                       (t.get('course_id'), t.get('course_name'), t.get('department'), t.get('room'), t.get('building'), t.get('day_of_week'), t.get('start_time'), t.get('end_time')))

    for r in load_json('resource_logs.json'):
        cursor.execute('''INSERT INTO resource_logs (resource_name, timestamp, current_occupancy, max_capacity, occupancy_pct, status_bucket) VALUES (?, ?, ?, ?, ?, ?)''', 
                       (r.get('resource_name'), r.get('timestamp'), r.get('current_occupancy'), r.get('max_capacity'), r.get('occupancy_pct'), r.get('status_bucket')))

    conn.commit()
    conn.close()
    print("Database seeded successfully.")

if __name__ == "__main__":
    seed_db()