import os
import json
import csv
import math
import numpy as np
from datetime import datetime, timedelta

def get_status_bucket(pct):
    if pct < 20: return 'empty'
    elif pct < 40: return 'low'
    elif pct < 65: return 'moderate'
    elif pct < 85: return 'high'
    elif pct <= 95: return 'full'
    else: return 'overflow'

def get_base_pattern(hour, minute, resource_type):
    time_float = hour + minute / 60.0
    
    if resource_type == 'library':
        if 0 <= time_float < 8: return 0.05
        elif 8 <= time_float < 10: return 0.2 + 0.1 * (time_float - 8)
        elif 10 <= time_float < 12: return 0.4 + 0.3 * (time_float - 10) / 2
        elif 12 <= time_float < 14: return 0.5
        elif 14 <= time_float < 17: return 0.6 + 0.2 * (time_float - 14) / 3
        elif 17 <= time_float < 19: return 0.6
        elif 19 <= time_float < 21: return 0.7 + 0.1 * (time_float - 19) / 2
        elif 21 <= time_float < 24: return max(0.05, 0.8 - 0.25 * (time_float - 21))
        
    elif resource_type == 'cafeteria':
        if 0 <= time_float < 7: return 0.0
        elif 7 <= time_float < 11: return 0.1
        elif 11 <= time_float < 11.5: return 0.3
        elif 11.5 <= time_float < 14: return 0.7 + 0.2 * math.sin(math.pi * (time_float - 11.5) / 2.5)
        elif 14 <= time_float < 18: return 0.15
        elif 18 <= time_float < 20: return 0.6 + 0.2 * math.sin(math.pi * (time_float - 18) / 2.0)
        elif 20 <= time_float < 24: return 0.05
        
    elif resource_type == 'gym':
        if 0 <= time_float < 6: return 0.0
        elif 6 <= time_float < 9: return 0.5 + 0.3 * math.sin(math.pi * (time_float - 6) / 3.0)
        elif 9 <= time_float < 16: return 0.2
        elif 16 <= time_float < 21: return 0.6 + 0.3 * math.sin(math.pi * (time_float - 16) / 5.0)
        elif 21 <= time_float < 24: return 0.1
        
    elif resource_type == 'lab':
        if 0 <= time_float < 8: return 0.05
        elif 8 <= time_float < 14: return 0.4
        elif 14 <= time_float < 18: return 0.7 + 0.1 * math.sin(math.pi * (time_float - 14) / 4.0)
        elif 18 <= time_float < 22: return 0.3
        elif 22 <= time_float < 24: return 0.1
        
    elif resource_type == 'student_center':
        if 0 <= time_float < 9: return 0.05
        elif 9 <= time_float < 16: return 0.4
        elif 16 <= time_float < 22: return 0.7
        elif 22 <= time_float < 24: return 0.2
        
    return 0.1

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    resources = [
        {'id': 'RES001', 'name': 'Main Library', 'capacity': 300, 'type': 'library'},
        {'id': 'RES002', 'name': 'Science Library', 'capacity': 120, 'type': 'library'},
        {'id': 'RES003', 'name': 'Central Cafeteria', 'capacity': 250, 'type': 'cafeteria'},
        {'id': 'RES004', 'name': 'Food Court', 'capacity': 200, 'type': 'cafeteria'},
        {'id': 'RES005', 'name': 'Gymnasium', 'capacity': 80, 'type': 'gym'},
        {'id': 'RES006', 'name': 'Indoor Sports Complex', 'capacity': 100, 'type': 'gym'},
        {'id': 'RES007', 'name': 'Student Center', 'capacity': 150, 'type': 'student_center'},
        {'id': 'RES008', 'name': 'Computer Lab A', 'capacity': 60, 'type': 'lab'},
        {'id': 'RES009', 'name': 'Computer Lab B', 'capacity': 60, 'type': 'lab'},
        {'id': 'RES010', 'name': 'WiFi Zone - Academic Block', 'capacity': 500, 'type': 'lab'},
        {'id': 'RES011', 'name': 'WiFi Zone - Library', 'capacity': 200, 'type': 'library'},
        {'id': 'RES012', 'name': 'WiFi Zone - Cafeteria', 'capacity': 300, 'type': 'cafeteria'}
    ]
    
    start_date = datetime(2023, 9, 1)
    days = 30
    intervals_per_day = 96
    
    data = []
    
    for day in range(days):
        current_date = start_date + timedelta(days=day)
        weekday = current_date.weekday()
        
        is_weekend = weekday >= 5
        day_multiplier = 1.0
        if weekday == 5:
            day_multiplier = 0.6
        elif weekday == 6:
            day_multiplier = 0.3
            
        is_exam_week = day >= 24
        
        for r in resources:
            exam_mult = 1.0
            if is_exam_week:
                if r['type'] == 'library': exam_mult = 1.4
                elif r['type'] == 'lab': exam_mult = 1.3
                elif r['type'] == 'gym': exam_mult = 0.8
                elif r['type'] == 'cafeteria': exam_mult = 1.15
                
            for interval in range(intervals_per_day):
                hour = interval // 4
                minute = (interval % 4) * 15
                
                timestamp = current_date.replace(hour=hour, minute=minute).isoformat()
                
                base_occ = get_base_pattern(hour, minute, r['type'])
                
                occ = base_occ * day_multiplier * exam_mult
                
                # Add noise
                noise = np.random.normal(0, 0.07)
                occ = occ + noise
                
                # Ensure within bounds (0 to 1.1)
                occ = max(0.0, min(1.1, occ))
                
                current_occ = int(round(occ * r['capacity']))
                occ_pct = round((current_occ / r['capacity']) * 100, 1)
                
                status_bucket = get_status_bucket(occ_pct)
                
                data.append({
                    'resource_id': r['id'],
                    'resource_name': r['name'],
                    'timestamp': timestamp,
                    'current_occupancy': current_occ,
                    'max_capacity': r['capacity'],
                    'occupancy_pct': occ_pct,
                    'status_bucket': status_bucket
                })
                
    json_path = os.path.join(data_dir, 'resource_logs.json')
    csv_path = os.path.join(data_dir, 'resource_logs.csv')
    
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2)
        
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
    print(f"Generated {len(data)} resource logs.")
    print(f"Date range: {start_date.date()} to {(start_date + timedelta(days=days-1)).date()}")
    
    peak_occ = {}
    for d in data:
        r_name = d['resource_name']
        if r_name not in peak_occ or d['current_occupancy'] > peak_occ[r_name]:
            peak_occ[r_name] = d['current_occupancy']
            
    print("\nPeak Occupancy per resource:")
    for r_name, peak in peak_occ.items():
        print(f"  {r_name}: {peak}")

if __name__ == '__main__':
    main()
