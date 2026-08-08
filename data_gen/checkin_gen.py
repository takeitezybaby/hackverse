import json
import csv
import os
import random
from datetime import datetime, timedelta

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    users_file = os.path.join(data_dir, 'users.json')
    if not os.path.exists(users_file):
        print(f"Error: {users_file} not found. Please run the user generator first.")
        return
        
    with open(users_file, 'r') as f:
        users = json.load(f)
        
    start_date = datetime(2023, 9, 1, 0, 0, 0)
    checkins = []
    checkin_id = 1
    
    resources = [
        'Main Library', 'Gymnasium', 'Central Cafeteria', 
        'Computer Lab A', 'Student Center', 'Science Library', 
        'Indoor Sports Complex', 'Food Court', 'Computer Lab B', 
        'WiFi Zone North', 'WiFi Zone South'
    ]
    
    # Generate 30 days of data
    for day_offset in range(30):
        current_date = start_date + timedelta(days=day_offset)
        day_of_week = current_date.strftime('%A')
        is_exam_week = 25 <= day_offset <= 30
        
        for user in users:
            user_id = user.get('user_id', user.get('id', 'unknown'))
            patterns = user.get('usual_patterns', [])
            
            # Unplanned visit (10% chance)
            if random.random() < 0.10:
                resource = random.choice(resources)
                arrival_hour = random.randint(8, 20)
                arrival_min = random.randint(0, 59)
                duration = random.randint(15, 120)
                
                checkin_time = current_date + timedelta(hours=arrival_hour, minutes=arrival_min)
                checkout_time = checkin_time + timedelta(minutes=duration)
                
                checkins.append({
                    'checkin_id': checkin_id,
                    'user_id': user_id,
                    'resource_name': resource,
                    'checkin_time': checkin_time.isoformat(),
                    'checkout_time': checkout_time.isoformat(),
                    'duration_min': duration,
                    'day_of_week': day_of_week,
                    'is_planned': False
                })
                checkin_id += 1
                
            # Planned visits based on patterns
            # patterns is a dict: {"Resource Name": {"days": ["Mon","Wed"], "usual_time": "17:00", "duration_min": 120}}
            day_abbr_map = {'Monday': 'Mon', 'Tuesday': 'Tue', 'Wednesday': 'Wed',
                            'Thursday': 'Thu', 'Friday': 'Fri', 'Saturday': 'Sat', 'Sunday': 'Sun'}
            current_day_abbr = day_abbr_map.get(day_of_week, day_of_week[:3])
            
            pattern_items = patterns.items() if isinstance(patterns, dict) else []
            for resource, pattern_info in pattern_items:
                pat_days = pattern_info.get('days', [])
                if current_day_abbr not in pat_days:
                    continue
                    
                # 20% chance of skipping
                if random.random() < 0.20:
                    continue 
                        
                time_str = pattern_info.get('usual_time', '12:00')
                base_duration = pattern_info.get('duration_min', 60)
                    
                try:
                    h, m = map(int, time_str.split(':'))
                except ValueError:
                    h, m = 12, 0
                    
                # Arrival time = usual_time +/- random offset (0-30 min, normally distributed)
                # Gaussian with mean 0, std 10, capped between -30 and 30
                offset_min = int(random.gauss(0, 10))
                offset_min = max(-30, min(30, offset_min))
                
                total_mins = h * 60 + m + offset_min
                arrival_hour = (total_mins // 60) % 24
                arrival_min = total_mins % 60
                
                # Duration offset (0-20 min)
                dur_offset = random.randint(-10, 20)
                duration = max(5, base_duration + dur_offset)
                
                if is_exam_week:
                    if 'Library' in resource:
                        duration = int(duration * 1.3)
                    elif 'Gym' in resource:
                        duration = int(duration * 0.7)
                        
                checkin_time = current_date + timedelta(hours=arrival_hour, minutes=arrival_min)
                checkout_time = checkin_time + timedelta(minutes=duration)
                
                checkins.append({
                    'checkin_id': checkin_id,
                    'user_id': user_id,
                    'resource_name': resource,
                    'checkin_time': checkin_time.isoformat(),
                    'checkout_time': checkout_time.isoformat(),
                    'duration_min': duration,
                    'day_of_week': day_of_week,
                    'is_planned': True
                })
                checkin_id += 1
                    
            # Exam week extra unplanned library visits for 25% of students
            if is_exam_week and random.random() < 0.25:
                resource = 'Main Library' if random.random() > 0.5 else 'Science Library'
                arrival_hour = random.randint(18, 22)
                arrival_min = random.randint(0, 59)
                duration = random.randint(60, 180)
                
                checkin_time = current_date + timedelta(hours=arrival_hour, minutes=arrival_min)
                checkout_time = checkin_time + timedelta(minutes=duration)
                
                checkins.append({
                    'checkin_id': checkin_id,
                    'user_id': user_id,
                    'resource_name': resource,
                    'checkin_time': checkin_time.isoformat(),
                    'checkout_time': checkout_time.isoformat(),
                    'duration_min': duration,
                    'day_of_week': day_of_week,
                    'is_planned': False
                })
                checkin_id += 1
                
    # Sort all check-ins by timestamp
    checkins.sort(key=lambda x: x['checkin_time'])
    
    json_path = os.path.join(data_dir, 'checkins.json')
    csv_path = os.path.join(data_dir, 'checkins.csv')
    
    with open(json_path, 'w') as f:
        json.dump(checkins, f, indent=2)
        
    if checkins:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=checkins[0].keys())
            writer.writeheader()
            writer.writerows(checkins)
            
    print(f"Generated {len(checkins)} check-in records.")
    print(f"Saved to {json_path} and {csv_path}")

if __name__ == '__main__':
    main()
