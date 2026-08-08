import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path
from .database import DB_PATH

def seed_db():
    if not DB_PATH.exists():
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    resources = [
        ("Main Library", "Study", 500),
        ("Campus Gym", "Fitness", 100),
        ("Cafeteria", "Dining", 300)
    ]
    cursor.executemany('INSERT INTO resources (name, category, capacity) VALUES (?, ?, ?)', resources)
    
    now = datetime.now()
    readings = []
    for resource_id in range(1, len(resources) + 1):
        capacity = resources[resource_id - 1][2]
        for i in range(24):
            timestamp = now - timedelta(hours=23 - i)
            occupancy = random.randint(0, capacity)
            readings.append((resource_id, occupancy, timestamp.strftime('%Y-%m-%d %H:%M:%S')))
            
    cursor.executemany('INSERT INTO readings (resource_id, occupancy, timestamp) VALUES (?, ?, ?)', readings)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    seed_db()
