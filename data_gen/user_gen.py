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

def pick_peak_time(resource_name):
    """Pick a realistic time for a resource based on peak hour definitions."""
    for keyword, hours in config.PEAK_HOURS.items():
        if keyword in resource_name:
            # 75% chance of primary peak, 25% secondary
            if random.random() < 0.75:
                start_h, end_h = random.choice(hours['primary'])
            else:
                start_h, end_h = random.choice(hours['secondary'])
            h = random.randint(start_h, end_h)
            m = random.choice([0, 15, 30, 45])
            return f"{h:02d}:{m:02d}"
    # Fallback
    return f"{random.randint(9, 18):02d}:00"

def pick_duration(resource_name):
    """Pick a realistic visit duration based on resource type."""
    if 'Library' in resource_name:
        return random.choice([60, 90, 120, 150, 180])
    elif 'Gym' in resource_name or 'Sports' in resource_name:
        return random.choice([45, 60, 75, 90])
    elif 'Cafeteria' in resource_name or 'Food' in resource_name:
        return random.choice([25, 30, 40, 45, 60])
    elif 'Lab' in resource_name:
        return random.choice([45, 60, 90, 120])
    elif 'Student' in resource_name:
        return random.choice([30, 45, 60, 90])
    else:
        return random.choice([30, 45, 60])

def weighted_resource_sample(n):
    """Pick n unique resources using popularity weights from config."""
    pool = []
    for res, weight in config.POPULAR_RESOURCES:
        pool.extend([res] * weight)
    chosen = set()
    while len(chosen) < n and pool:
        pick = random.choice(pool)
        chosen.add(pick)
    return list(chosen)

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
    
    # Building -> nearby resources (multiple options, weighted toward popular ones)
    building_resource_map = {
        'Main Academic Block': ['Computer Lab A', 'Computer Lab B', 'Central Cafeteria', 'WiFi Zone - Academic Block'],
        'Science Complex': ['Science Library', 'Computer Lab A', 'Main Library'],
        'Engineering Tower': ['Computer Lab B', 'Computer Lab A', 'WiFi Zone - Academic Block'],
        'Management Building': ['Student Center', 'Central Cafeteria', 'Food Court'],
        'Central Library Building': ['Main Library', 'Science Library', 'WiFi Zone - Library']
    }
    
    users = []
    
    for i in range(1, config.NUM_USERS + 1):
        user_id = f"u_{i:04d}"
        name = fake.name()
        dept = random.choice(departments)
        year = random.randint(1, 4)
        
        # Assign courses (4-6)
        num_courses = random.randint(4, 6)
        enrolled_courses = random.sample(unique_course_ids, min(num_courses, len(unique_course_ids)))
        
        usual_patterns = {}
        
        # 1. Post-class patterns (80% chance per course — high to create class-driven waves)
        for cid in enrolled_courses:
            if random.random() < 0.80:
                course = course_lookup[cid]
                building = course.get('building', 'Main Academic Block')
                possible_resources = building_resource_map.get(building, ['Central Cafeteria', 'Main Library'])
                res = random.choice(possible_resources)
                
                usual_time = time_add_mins(course['end_time'], random.randint(5, 20))
                duration = pick_duration(res)
                
                # Use days from the course schedule
                days = course['day_of_week'] if isinstance(course['day_of_week'], list) else [course['day_of_week']]
                
                pattern_key = f"{res}_post_{cid}"
                usual_patterns[pattern_key] = {
                    "resource": res,
                    "days": days,
                    "usual_time": usual_time,
                    "duration_min": duration,
                    "source": "post_class",
                    "linked_course": cid
                }
        
        # 2. Routine patterns (2-4 per user, using weighted resource selection)
        num_routine = random.randint(2, 4)
        chosen_resources = weighted_resource_sample(num_routine)
        for res in chosen_resources:
            # Weekday-heavy: 3-5 weekdays for most patterns
            num_days = random.randint(3, 5)
            days = random.sample(['Mon', 'Tue', 'Wed', 'Thu', 'Fri'], min(num_days, 5))
            # 20% chance of including a weekend day
            if random.random() < 0.20:
                days.append(random.choice(['Sat', 'Sun']))
            
            usual_time = pick_peak_time(res)
            duration = pick_duration(res)
                
            pattern_key = f"{res}_routine_{random.randint(1000,9999)}"
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

    # Stats
    total_patterns = sum(len(u['usual_patterns']) for u in users)
    post_class_count = sum(1 for u in users for p in u['usual_patterns'].values() if p.get('source') == 'post_class')
    routine_count = total_patterns - post_class_count
    print(f"Generated {len(users)} student profiles (seed={config.RANDOM_SEED}).")
    print(f"  Total patterns: {total_patterns} (post_class: {post_class_count}, routine: {routine_count})")
    print(f"  Avg patterns/user: {total_patterns/len(users):.1f}")
    print(f"Data saved to {json_path} and {csv_path}")

if __name__ == "__main__":
    generate_users()
