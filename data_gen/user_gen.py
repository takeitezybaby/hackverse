import json
import csv
import os
import random
from faker import Faker
import config

def time_add_mins(time_str, add_mins):
    h, m = map(int, time_str.split(':'))
    total = h * 60 + m + add_mins
    return f"{(total // 60) % 24:02d}:{total % 60:02d}"

def generate_users():
    random.seed(config.RANDOM_SEED)
    Faker.seed(config.RANDOM_SEED)
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
        
    # Build a lookup for course details
    course_lookup = {t['course_id']: t for t in timetables}
    unique_course_ids = list(course_lookup.keys())
    
    departments = ['CS', 'EE', 'ME', 'CE', 'Math', 'Physics', 'Chemistry', 'Bio', 'MBA', 'Economics']
    
    # Simple mapping of buildings to likely nearby resources
    building_resource_map = {
        'Main Academic Block': ['Computer Lab A', 'Computer Lab B', 'WiFi Zone - Academic Block'],
        'Science Complex': ['Science Library', 'Computer Lab A'],
        'Engineering Tower': ['Computer Lab B', 'WiFi Zone - Academic Block'],
        'Management Building': ['Student Center', 'Central Cafeteria'],
        'Central Library Building': ['Main Library', 'WiFi Zone - Library']
    }
    
    resources_pool = list(config.RESOURCE_CAPACITIES.keys())
    
    users = []
    
    for i in range(1, config.NUM_USERS + 1):
        user_id = f"u_{i:03d}"
        name = fake.name()
        dept = random.choice(departments)
        year = random.randint(1, 4)
        
        # Assign courses
        num_courses = random.randint(4, 6)
        enrolled_courses = random.sample(unique_course_ids, min(num_courses, len(unique_course_ids)))
        
        usual_patterns = {}
        
        # 1. Generate post_class patterns (causal link)
        for cid in enrolled_courses:
            # 65% chance this course creates a post_class routine
            if random.random() < 0.65:
                course = course_lookup[cid]
                building = course.get('building', 'Main Academic Block')
                possible_resources = building_resource_map.get(building, resources_pool)
                res = random.choice(possible_resources)
                
                # Setup 10-20 mins after class ends
                usual_time = time_add_mins(course['end_time'], random.randint(10, 20))
                duration = random.choice([30, 45, 60, 90])
                
                # Use a composite key so a resource can have multiple patterns (e.g. routine vs post_class)
                pattern_key = f"{res}_post_{cid}"
                usual_patterns[pattern_key] = {
                    "resource": res,
                    "days": course['day_of_week'],
                    "usual_time": usual_time,
                    "duration_min": duration,
                    "source": "post_class",
                    "linked_course": cid
                }
        
        # 2. Generate freeform routine patterns (~35% of total patterns conceptualized)
        num_routine = random.randint(1, 3)
        chosen_resources = random.sample(resources_pool, num_routine)
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
                
            pattern_key = f"{res}_routine_{random.randint(100,999)}"
            usual_patterns[pattern_key] = {
                "resource": res,
                "days": days,
                "usual_time": usual_time,
                "duration_min": duration,
                "source": "routine"
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
                row = u.copy()
                row['enrolled_courses'] = json.dumps(row['enrolled_courses'])
                row['usual_patterns'] = json.dumps(row['usual_patterns'])
                writer.writerow(row)
                
    print(f"Generated {len(users)} student profiles (seed={config.RANDOM_SEED}).")
    print(f"Data saved to {json_path} and {csv_path}")

if __name__ == "__main__":
    generate_users()
