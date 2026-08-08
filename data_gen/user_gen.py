import json
import csv
import os
import random
from faker import Faker

def generate_users():
    fake = Faker()
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    data_dir = os.path.join(project_root, 'data')
    
    timetable_path = os.path.join(data_dir, 'timetables.json')
    if not os.path.exists(timetable_path):
        print("Error: timetables.json not found. Run timetable_gen.py first.")
        return
        
    with open(timetable_path, 'r', encoding='utf-8') as f:
        timetables = json.load(f)
        
    unique_course_ids = list(set([t['course_id'] for t in timetables]))
    
    departments = ['CS', 'EE', 'ME', 'CE', 'Math', 'Physics', 'Chemistry', 'Bio', 'MBA', 'Economics']
    resources_pool = [
        'Main Library', 'Science Library', 'Central Cafeteria', 'Food Court', 
        'Gymnasium', 'Indoor Sports Complex', 'Student Center', 'Computer Lab A', 'Computer Lab B'
    ]
    
    users = []
    
    for i in range(1, 201):
        user_id = f"u_{i:03d}"
        name = fake.name()
        dept = random.choice(departments)
        year = random.randint(1, 4)
        
        # Assign courses
        num_courses = random.randint(4, 6)
        enrolled_courses = random.sample(unique_course_ids, min(num_courses, len(unique_course_ids)))
        
        # Generate patterns
        num_resources = random.randint(2, 5)
        chosen_resources = random.sample(resources_pool, num_resources)
        
        usual_patterns = {}
        for res in chosen_resources:
            days = random.sample(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], random.randint(2, 5))
            
            if 'Library' in res:
                usual_time = f"{random.randint(16, 21):02d}:00"
                duration = random.choice([60, 90, 120, 180])
            elif 'Gym' in res or 'Sports' in res:
                usual_time = random.choice([f"{random.randint(6, 8):02d}:00", f"{random.randint(17, 20):02d}:00"])
                duration = random.choice([45, 60, 90])
            elif 'Cafeteria' in res or 'Food' in res:
                usual_time = random.choice(["08:30", "12:30", "19:00"])
                duration = random.choice([30, 45, 60])
            else:
                usual_time = f"{random.randint(9, 16):02d}:00"
                duration = random.choice([45, 60, 90])
                
            usual_patterns[res] = {
                "days": days,
                "usual_time": usual_time,
                "duration_min": duration
            }
            
        users.append({
            'user_id': user_id,
            'name': name,
            'department': dept,
            'year': year,
            'enrolled_courses': enrolled_courses,
            'usual_patterns': usual_patterns
        })
        
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        
    json_path = os.path.join(data_dir, 'users.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4)
        
    csv_path = os.path.join(data_dir, 'users.csv')
    if users:
        keys = ['user_id', 'name', 'department', 'year', 'enrolled_courses', 'usual_patterns']
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for u in users:
                # Serialize complex types for CSV
                row = u.copy()
                row['enrolled_courses'] = json.dumps(row['enrolled_courses'])
                row['usual_patterns'] = json.dumps(row['usual_patterns'])
                writer.writerow(row)
                
    print(f"Generated {len(users)} student profiles.")
    print(f"Data saved to {json_path} and {csv_path}")

if __name__ == "__main__":
    generate_users()
