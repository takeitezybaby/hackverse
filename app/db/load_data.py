import sqlite3
import csv
from pathlib import Path
from .database import DB_PATH

def load_generated_data():
    csv_path = Path(__file__).parent.parent.parent / "data" / "resource_logs.csv"
    if not csv_path.exists():
        print("Error: resource_logs.csv not found.")
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM resources")
        cursor.execute("DELETE FROM readings")
        
        unique_resources = {}
        readings_data = []
        
        id_map = {}
        next_id = 1
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                raw_id = row['resource_id']
                
                if raw_id not in id_map:
                    id_map[raw_id] = next_id
                    unique_resources[next_id] = (
                        next_id, 
                        row['resource_name'], 
                        "Campus Facility", 
                        int(float(row['max_capacity']))
                    )
                    next_id += 1
                
                res_id = id_map[raw_id]
                
                readings_data.append((
                    res_id,
                    int(float(row['current_occupancy'])),
                    row['timestamp']
                ))
        
        cursor.executemany(
            "INSERT INTO resources (id, name, category, capacity) VALUES (?, ?, ?, ?)",
            list(unique_resources.values())
        )
        
        cursor.executemany(
            "INSERT INTO readings (resource_id, occupancy, timestamp) VALUES (?, ?, ?)",
            readings_data
        )
        
        print(f"Success: Loaded {len(unique_resources)} resources and {len(readings_data)} readings.")
        
    except Exception as e:
        print(f"Error loading data: {e}")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    load_generated_data()