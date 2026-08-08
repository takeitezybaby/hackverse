import json
import csv
import os
import random
from datetime import datetime, timedelta

def generate_timetables():
    departments = ['CS', 'EE', 'ME', 'CE', 'Math', 'Physics', 'Chemistry', 'Bio', 'MBA', 'Economics']
    buildings = {
        'Main Academic Block': 'MAB',
        'Science Complex': 'SC',
        'Engineering Tower': 'ET',
        'Management Building': 'MB',
        'Central Library Building': 'CLB'
    }
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    
    # Generate 35 courses
    courses_base = []
    for i in range(1, 36):
        dept = random.choice(departments)
        course_id = f"{dept}{random.randint(100, 499)}"
        course_name = f"Introduction to {dept} {i}"
        instructor = f"Prof. {chr(random.randint(65, 90))}{chr(random.randint(97, 122))}"
        semester = random.choice(['Fall', 'Spring'])
        section = random.choice(['A', 'B', 'C'])
        
        building = random.choice(list(buildings.keys()))
        b_prefix = buildings[building]
        room = f"{b_prefix}-{random.randint(1, 5)}0{random.randint(1, 9)}"
        
        courses_base.append({
            'course_id': course_id,
            'course_name': course_name,
            'department': dept,
            'instructor': instructor,
            'building': building,
            'room': room,
            'semester': semester,
            'section': section
        })

    timetables = []
    room_schedule = {} # (room, day, time_slot) -> True

    def parse_time(t_str):
        return datetime.strptime(t_str, "%H:%M")

    def format_time(dt):
        return dt.strftime("%H:%M")
        
    start_time_limit = parse_time("08:00")
    end_time_limit = parse_time("17:00")

    for course in courses_base:
        num_days = random.randint(2, 3)
        chosen_days = random.sample(days, num_days)
        duration_hours = random.choice([1, 1.5])
        
        # We need to find non-conflicting time slots for these days
        # For simplicity, assign same time for all days for a course
        for attempt in range(100):
            # Pick a random start time between 8 and 15:30
            start_hour = random.randint(8, 15)
            start_min = random.choice([0, 30])
            start_dt = start_time_limit.replace(hour=start_hour, minute=start_min)
            end_dt = start_dt + timedelta(hours=duration_hours)
            
            if end_dt > end_time_limit:
                continue
                
            start_str = format_time(start_dt)
            end_str = format_time(end_dt)
            
            # Check conflicts
            conflict = False
            for d in chosen_days:
                # Basic overlap check (assuming discrete 30min slots)
                slots_needed = int(duration_hours * 2)
                for slot_idx in range(slots_needed):
                    slot_dt = start_dt + timedelta(minutes=30*slot_idx)
                    slot_key = (course['room'], d, format_time(slot_dt))
                    if slot_key in room_schedule:
                        conflict = True
                        break
                if conflict:
                    break
                    
            if not conflict:
                for d in chosen_days:
                    slots_needed = int(duration_hours * 2)
                    for slot_idx in range(slots_needed):
                        slot_dt = start_dt + timedelta(minutes=30*slot_idx)
                        slot_key = (course['room'], d, format_time(slot_dt))
                        room_schedule[slot_key] = True
                    
                    course_instance = course.copy()
                    course_instance['day_of_week'] = d
                    course_instance['start_time'] = start_str
                    course_instance['end_time'] = end_str
                    timetables.append(course_instance)
                break

    # Save to data directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    data_dir = os.path.join(project_root, 'data')
    
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        
    json_path = os.path.join(data_dir, 'timetables.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(timetables, f, indent=4)
        
    csv_path = os.path.join(data_dir, 'timetables.csv')
    if timetables:
        keys = timetables[0].keys()
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(timetables)
            
    print(f"Generated {len(timetables)} class slots across {len(courses_base)} courses.")
    print(f"Data saved to {json_path} and {csv_path}")

if __name__ == "__main__":
    generate_timetables()
