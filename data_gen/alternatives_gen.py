import json
import csv
import os

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    alternatives = [
        {'alt_id': 1, 'original_resource': 'Main Library', 'alt_type': 'time_shift', 'alt_resource': 'Main Library', 'original_peak_time': '17:00', 'suggested_time': '17:00→15:30', 'capacity_relief': 'moderate', 'priority': 2},
        {'alt_id': 2, 'original_resource': 'Main Library', 'alt_type': 'time_shift', 'alt_resource': 'Main Library', 'original_peak_time': '17:00', 'suggested_time': '17:00→20:00', 'capacity_relief': 'high', 'priority': 3},
        {'alt_id': 3, 'original_resource': 'Main Library', 'alt_type': 'location_shift', 'alt_resource': 'Science Library', 'original_peak_time': '17:00', 'suggested_time': 'same', 'capacity_relief': 'high', 'priority': 1},
        
        {'alt_id': 4, 'original_resource': 'Gymnasium', 'alt_type': 'time_shift', 'alt_resource': 'Gymnasium', 'original_peak_time': '19:00', 'suggested_time': '19:00→18:00', 'capacity_relief': 'moderate', 'priority': 2},
        {'alt_id': 5, 'original_resource': 'Gymnasium', 'alt_type': 'time_shift', 'alt_resource': 'Gymnasium', 'original_peak_time': '19:00', 'suggested_time': '19:00→06:30', 'capacity_relief': 'high', 'priority': 3},
        {'alt_id': 6, 'original_resource': 'Gymnasium', 'alt_type': 'location_shift', 'alt_resource': 'Indoor Sports Complex', 'original_peak_time': '19:00', 'suggested_time': 'same', 'capacity_relief': 'high', 'priority': 1},
        
        {'alt_id': 7, 'original_resource': 'Central Cafeteria', 'alt_type': 'time_shift', 'alt_resource': 'Central Cafeteria', 'original_peak_time': '12:30', 'suggested_time': '12:30→11:30', 'capacity_relief': 'moderate', 'priority': 2},
        {'alt_id': 8, 'original_resource': 'Central Cafeteria', 'alt_type': 'time_shift', 'alt_resource': 'Central Cafeteria', 'original_peak_time': '12:30', 'suggested_time': '12:30→13:30', 'capacity_relief': 'moderate', 'priority': 3},
        {'alt_id': 9, 'original_resource': 'Central Cafeteria', 'alt_type': 'location_shift', 'alt_resource': 'Food Court', 'original_peak_time': '12:30', 'suggested_time': 'same', 'capacity_relief': 'high', 'priority': 1},
        
        {'alt_id': 10, 'original_resource': 'Computer Lab A', 'alt_type': 'location_shift', 'alt_resource': 'Computer Lab B', 'original_peak_time': '15:00', 'suggested_time': 'same', 'capacity_relief': 'high', 'priority': 1},
        {'alt_id': 11, 'original_resource': 'Computer Lab A', 'alt_type': 'time_shift', 'alt_resource': 'Computer Lab A', 'original_peak_time': '15:00', 'suggested_time': '15:00→09:00', 'capacity_relief': 'high', 'priority': 2},
        
        {'alt_id': 12, 'original_resource': 'Student Center', 'alt_type': 'time_shift', 'alt_resource': 'Student Center', 'original_peak_time': '13:00', 'suggested_time': '13:00→10:00', 'capacity_relief': 'moderate', 'priority': 2},
        {'alt_id': 13, 'original_resource': 'Student Center', 'alt_type': 'location_shift', 'alt_resource': 'WiFi Zone North', 'original_peak_time': '13:00', 'suggested_time': 'same', 'capacity_relief': 'high', 'priority': 1},
        
        {'alt_id': 14, 'original_resource': 'WiFi Zone North', 'alt_type': 'location_shift', 'alt_resource': 'WiFi Zone South', 'original_peak_time': '14:00', 'suggested_time': 'same', 'capacity_relief': 'moderate', 'priority': 1},
    ]
    
    json_path = os.path.join(data_dir, 'alternatives.json')
    csv_path = os.path.join(data_dir, 'alternatives.csv')
    
    with open(json_path, 'w') as f:
        json.dump(alternatives, f, indent=2)
        
    if alternatives:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=alternatives[0].keys())
            writer.writeheader()
            writer.writerows(alternatives)
            
    print(f"Generated {len(alternatives)} alternatives.")
    print(f"Saved to {json_path} and {csv_path}")

if __name__ == '__main__':
    main()
