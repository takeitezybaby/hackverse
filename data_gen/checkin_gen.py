import json
import csv
import os
import random
from datetime import datetime, timedelta
import config

def get_current_occupancy(running_occupants, check_time):
    # running_occupants is a list of checkout_times
    # return count of checkouts > check_time
    valid = [t for t in running_occupants if t > check_time]
    return len(valid), valid

def main():
    random.seed(config.RANDOM_SEED)
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    users_file = os.path.join(data_dir, 'users.json')
    timetables_file = os.path.join(data_dir, 'timetables.json')
    alternatives_file = os.path.join(data_dir, 'alternatives.json')
    
    if not os.path.exists(users_file) or not os.path.exists(timetables_file):
        print("Error: users.json or timetables.json not found.")
        return
        
    with open(users_file, 'r') as f:
        users = json.load(f)
    with open(timetables_file, 'r', encoding='utf-8') as f:
        timetables = json.load(f)
        
    alternatives = []
    if os.path.exists(alternatives_file):
        with open(alternatives_file, 'r', encoding='utf-8') as f:
            alternatives = json.load(f)
            
    # Build alternatives map: { 'Main Library': ['Science Library', ...], ... }
    alt_map = {}
    for alt in alternatives:
        if alt['alt_type'] == 'location_shift':
            alt_map.setdefault(alt['original_resource'], []).append(alt['alt_resource'])
    
    # 1. Dynamic Anomaly Selection: Pick a course to cancel on the target date
    class_cancel_config = config.ANOMALIES['class_cancellation']
    target_cancel_date = class_cancel_config['target_date']
    day_abbr_cancel = target_cancel_date.strftime('%a') # Mon, Tue, etc.
    
    # Find courses meeting on this day
    eligible_courses = [t for t in timetables if day_abbr_cancel in t['day_of_week']]
    if eligible_courses:
        cancelled_course = random.choice(eligible_courses)
        cancelled_course_id = cancelled_course['course_id']
    else:
        cancelled_course_id = "UNKNOWN"
        
    # Write Ground Truth
    ground_truth = {
        'events': [
            {
                'event_type': 'cultural_fest',
                'start': config.ANOMALIES['fest']['start_date'].isoformat(),
                'end': config.ANOMALIES['fest']['end_date'].isoformat(),
                'affected': ['Student Center', 'Food Court', 'Main Library', 'Science Library']
            },
            {
                'event_type': 'infra_incident',
                'start': config.ANOMALIES['infra_incident']['start_date'].isoformat(),
                'end': config.ANOMALIES['infra_incident']['end_date'].isoformat(),
                'affected_resource': config.ANOMALIES['infra_incident']['resource']
            },
            {
                'event_type': 'class_cancellation',
                'start': target_cancel_date.isoformat(),
                'end': target_cancel_date.isoformat(),
                'affected_course': cancelled_course_id
            }
        ]
    }
    
    gt_path = os.path.join(data_dir, 'events_ground_truth.json')
    with open(gt_path, 'w') as f:
        json.dump(ground_truth, f, indent=4)
    
    # 2. Generate intended visits (Pass 1)
    intended_visits = []
    resources = list(config.RESOURCE_CAPACITIES.keys())
    
    exam_start = config.ANOMALIES['exam_week']['start_date']
    exam_end = config.ANOMALIES['exam_week']['end_date']
    fest_start = config.ANOMALIES['fest']['start_date']
    fest_end = config.ANOMALIES['fest']['end_date']
    infra_res = config.ANOMALIES['infra_incident']['resource']
    infra_date = config.ANOMALIES['infra_incident']['start_date'].date()
    
    for day_offset in range(config.NUM_DAYS):
        current_date = config.START_DATE + timedelta(days=day_offset)
        day_of_week = current_date.strftime('%A')
        day_abbr = current_date.strftime('%a')
        
        is_exam = exam_start <= current_date <= exam_end
        is_fest = fest_start <= current_date <= fest_end
        is_infra = current_date.date() == infra_date
        is_cancel_day = current_date.date() == target_cancel_date.date()
        
        for user in users:
            user_id = user.get('user_id')
            patterns = user.get('usual_patterns', {})
            
            # Unplanned visit
            # Fest anomaly: Spike unplanned visits to Student Center/Food Court
            unplanned_prob = config.UNPLANNED_PROBABILITY
            if is_fest:
                unplanned_prob *= 3
                
            if random.random() < unplanned_prob:
                resource = random.choice(resources)
                if is_fest and random.random() < 0.7:
                    resource = random.choice(['Student Center', 'Food Court'])
                    
                arrival_hour = random.randint(8, 20)
                arrival_min = random.randint(0, 59)
                duration = random.randint(15, 120)
                
                checkin_time = current_date + timedelta(hours=arrival_hour, minutes=arrival_min)
                checkout_time = checkin_time + timedelta(minutes=duration)
                
                intended_visits.append({
                    'user_id': user_id,
                    'resource_name': resource,
                    'checkin_time': checkin_time,
                    'checkout_time': checkout_time,
                    'duration_min': duration,
                    'day_of_week': day_of_week,
                    'is_planned': False,
                    'source': 'unplanned'
                })
                
            # Planned visits
            for pat_key, pattern_info in patterns.items():
                if day_abbr not in pattern_info.get('days', []):
                    continue
                
                resource = pattern_info.get('resource')
                source = pattern_info.get('source', 'routine')
                linked_course = pattern_info.get('linked_course')
                
                # Class cancellation anomaly
                if is_cancel_day and source == 'post_class' and linked_course == cancelled_course_id:
                    continue # Skip this visit because the class didn't happen!
                    
                skip_prob = config.SKIP_PROBABILITY
                if is_fest and ('Library' in resource or 'Lab' in resource):
                    skip_prob = 0.80 # Massive skip rate for academic places during fest
                    
                if random.random() < skip_prob:
                    continue
                    
                time_str = pattern_info.get('usual_time', '12:00')
                base_duration = pattern_info.get('duration_min', 60)
                
                h, m = map(int, time_str.split(':'))
                
                # Jitter
                offset_min = int(random.gauss(0, 10))
                offset_min = max(-30, min(30, offset_min))
                
                total_mins = h * 60 + m + offset_min
                arrival_hour = (total_mins // 60) % 24
                arrival_min = total_mins % 60
                
                dur_offset = random.randint(-10, 20)
                duration = max(5, base_duration + dur_offset)
                
                # Exam anomaly
                if is_exam:
                    if 'Library' in resource:
                        duration = int(duration * 1.3)
                    elif 'Gym' in resource:
                        duration = int(duration * 0.7)
                        
                checkin_time = current_date + timedelta(hours=arrival_hour, minutes=arrival_min)
                checkout_time = checkin_time + timedelta(minutes=duration)
                
                intended_visits.append({
                    'user_id': user_id,
                    'resource_name': resource,
                    'checkin_time': checkin_time,
                    'checkout_time': checkout_time,
                    'duration_min': duration,
                    'day_of_week': day_of_week,
                    'is_planned': True,
                    'source': source
                })
                
    # Sort chronologically
    intended_visits.sort(key=lambda x: x['checkin_time'])
    
    # 3. Simulate Chronologically and apply Capacity Feedback (Pass 2)
    final_checkins = []
    diagnostics = []
    checkin_id = 1
    
    # State: {resource_name: [checkout_time1, checkout_time2, ...]}
    running_occupancy = {res: [] for res in resources}
    
    for visit in intended_visits:
        res = visit['resource_name']
        arr_time = visit['checkin_time']
        is_infra = arr_time.date() == infra_date and res == infra_res
        
        cap = config.RESOURCE_CAPACITIES.get(res, 100)
        
        # Cleanup expired checkouts
        current_occ, valid_checkouts = get_current_occupancy(running_occupancy[res], arr_time)
        running_occupancy[res] = valid_checkouts
        
        occ_pct = (current_occ / cap) * 100
        
        is_blocked = occ_pct >= config.REROUTE_THRESHOLD_PCT or is_infra
        
        if is_blocked:
            # Reroute or Balk
            can_reroute = alt_map.get(res, [])
            if can_reroute and random.random() < 0.60:
                # Reroute
                new_res = random.choice(can_reroute)
                visit['rerouted_from'] = res
                visit['resource_name'] = new_res
                # Need to check capacity of new_res too (simple check)
                new_occ, new_valid = get_current_occupancy(running_occupancy[new_res], arr_time)
                if (new_occ / config.RESOURCE_CAPACITIES.get(new_res, 100)) * 100 >= config.REROUTE_THRESHOLD_PCT:
                    # Balk anyway
                    diagnostics.append({"time": arr_time.isoformat(), "user": visit['user_id'], "action": "balked_cascading", "intended": res, "reroute": new_res})
                    continue
                
                running_occupancy[new_res] = new_valid
                running_occupancy[new_res].append(visit['checkout_time'])
                
                visit['checkin_time'] = visit['checkin_time'].isoformat()
                visit['checkout_time'] = visit['checkout_time'].isoformat()
                visit['checkin_id'] = checkin_id
                final_checkins.append(visit)
                diagnostics.append({"time": visit['checkin_time'], "user": visit['user_id'], "action": "rerouted", "from": res, "to": new_res})
                checkin_id += 1
                
            else:
                # Balk
                diagnostics.append({"time": arr_time.isoformat(), "user": visit['user_id'], "action": "balked", "intended": res})
                continue
                
        else:
            # Accepted
            running_occupancy[res].append(visit['checkout_time'])
            visit['checkin_time'] = visit['checkin_time'].isoformat()
            visit['checkout_time'] = visit['checkout_time'].isoformat()
            visit['checkin_id'] = checkin_id
            final_checkins.append(visit)
            checkin_id += 1
            
    # Write outputs
    json_path = os.path.join(data_dir, 'checkins.json')
    with open(json_path, 'w') as f:
        json.dump(final_checkins, f, indent=2)
        
    diag_path = os.path.join(data_dir, 'checkin_diagnostics.json')
    with open(diag_path, 'w') as f:
        json.dump(diagnostics, f, indent=2)
        
    print(f"Generated {len(final_checkins)} check-in records (Balked/Rerouted: {len(diagnostics)}).")
    print(f"Saved to {json_path} and {diag_path}")

if __name__ == '__main__':
    main()
