import os
import json
import sqlite3
import random
from datetime import datetime, timedelta

def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def generate_reports():
    random.seed(42)
    
    resources = [
        'Main Library', 'Science Library', 'Central Cafeteria', 'Food Court', 
        'Gymnasium', 'Indoor Sports Complex', 'Student Center', 'Computer Lab A', 
        'Computer Lab B', 'WiFi Zone - Academic Block', 'WiFi Zone - Library', 
        'WiFi Zone - Cafeteria'
    ]
    
    report_types = ['crowding', 'issue', 'recommendation', 'feedback', 'availability']
    
    # Templates for natural language comments
    comments = {
        'crowding': [
            "{resource} is packed, no seats anywhere",
            "queue is insane at {resource}, been waiting 20 mins",
            "super crowded in {resource} right now",
            "{resource} is empty, great time to come",
            "way too many ppl at {resource}",
            "can't find a spot in {resource} rn",
            "actually found a seat in {resource} today lol",
            "{resource} is completely full"
        ],
        'issue': [
            "AC is broken in {resource}, literally sweating",
            "{resource} has 3 broken machines today",
            "system is down at {resource}",
            "wifi keeps dropping near {resource}",
            "spilled drink in {resource} needs cleaning",
            "doors are locked at {resource}??",
            "{resource} is super noisy today, can't focus",
            "power out in {resource}"
        ],
        'recommendation': [
            "{resource} is super quiet, perfect for studying",
            "def avoid {resource} around this time",
            "come to {resource} before 12 if u want a spot",
            "highly recommend checking out {resource} today",
            "best time to hit {resource} is morning",
            "bring a jacket to {resource} it's freezing",
            "grab food before heading to {resource}"
        ],
        'feedback': [
            "food court ran out of veg options by 1pm",
            "staff at {resource} is super helpful",
            "{resource} needs more charging ports",
            "why is {resource} closed so early on weekends?",
            "love the new setup in {resource}",
            "{resource} is kinda messy today tbh",
            "wish {resource} had better lighting"
        ],
        'availability': [
            "all treadmills taken at {resource}",
            "plenty of space at {resource}",
            "{resource} is closing in 10 mins",
            "finally got a spot in {resource}",
            "no computers free in {resource}",
            "{resource} is completely empty",
            "only a few seats left in {resource}"
        ]
    }
    
    exam_week_comments = [
        "{resource} is impossible to get a seat in during exams",
        "ppl saving seats in {resource} for hours...",
        "{resource} is dead silent, everyone cramming",
        "no room in {resource}, going back to dorm"
    ]
    
    fest_comments = [
        "{resource} is so loud with the fest prep",
        "club event in {resource}, super crowded",
        "can't even walk through {resource} today",
        "great vibe at {resource} for the fest!"
    ]
    
    infra_incident_comments = [
        "network switch down in {resource}",
        "all machines offline in {resource} wtf",
        "{resource} completely useless today no internet",
        "can't log in to any pc in {resource}"
    ]

    num_reports = random.randint(80, 120)
    reports = []
    
    for _ in range(num_reports):
        # Peak hours (11-14, 16-20) are more likely
        if random.random() < 0.7:
            hour = random.choice(list(range(11, 15)) + list(range(16, 21)))
        else:
            hour = random.choice(list(range(8, 11)) + list(range(21, 23)))
            
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        day = random.randint(1, 30)
        
        timestamp = datetime(2023, 9, day, hour, minute, second)
        user_id = f"u_{random.randint(1, 1500):04d}"
        
        # Determine anomaly
        is_exam_week = 25 <= day <= 30
        is_fest = 15 <= day <= 16
        is_infra_incident = day == 10
        
        resource = random.choice(resources)
        report_type = random.choice(report_types)
        comment_template = random.choice(comments[report_type])
        
        # Override for anomalies
        if is_exam_week and random.random() < 0.6:
            resource = random.choice(['Main Library', 'Science Library'])
            report_type = 'crowding'
            comment_template = random.choice(exam_week_comments + comments['crowding'])
        elif is_fest and random.random() < 0.6:
            resource = random.choice(['Student Center', 'Gymnasium'])
            report_type = 'crowding'
            comment_template = random.choice(fest_comments)
        elif is_infra_incident and random.random() < 0.6:
            resource = 'Computer Lab A'
            report_type = 'issue'
            comment_template = random.choice(infra_incident_comments)
            
        comment = comment_template.replace('{resource}', resource)
        # Add some typos/informality sometimes
        if random.random() < 0.2:
            comment = comment.lower()
        if random.random() < 0.1:
            comment = comment.replace("the", "teh").replace("is", "is ")
            
        reports.append({
            "user_id": user_id,
            "resource_name": resource,
            "report_type": report_type,
            "timestamp": timestamp,
            "comment": comment
        })
        
    # Sort by timestamp
    reports.sort(key=lambda x: x["timestamp"])
    
    # Assign IDs and format timestamp
    formatted_reports = []
    for i, r in enumerate(reports, 1):
        formatted_reports.append({
            "report_id": i,
            "user_id": r["user_id"],
            "resource_name": r["resource_name"],
            "report_type": r["report_type"],
            "timestamp": r["timestamp"].isoformat(),
            "comment": r["comment"]
        })
        
    return formatted_reports

def main():
    root = get_project_root()
    data_dir = os.path.join(root, 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    db_path = os.path.join(data_dir, 'campus_twin.db')
    json_path = os.path.join(data_dir, 'crowdsourced_reports.json')
    
    reports = generate_reports()
    
    # Write JSON
    with open(json_path, 'w') as f:
        json.dump(reports, f, indent=2)
        
    # SQLite
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS crowdsourced_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        resource_name TEXT,
        report_type TEXT,
        timestamp TEXT,
        comment TEXT
    )
    ''')
    
    c.execute('DELETE FROM crowdsourced_reports')
    
    for r in reports:
        c.execute('''
        INSERT INTO crowdsourced_reports (user_id, resource_name, report_type, timestamp, comment)
        VALUES (?, ?, ?, ?, ?)
        ''', (r['user_id'], r['resource_name'], r['report_type'], r['timestamp'], r['comment']))
        
    conn.commit()
    conn.close()
    
    print(f"Generated {len(reports)} crowdsourced reports.")
    print(f"Saved to {json_path}")
    print(f"Inserted into SQLite {db_path}")

if __name__ == '__main__':
    main()
