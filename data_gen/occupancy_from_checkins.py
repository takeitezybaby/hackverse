import json
import csv
import os
from datetime import datetime, timedelta
import config

def get_status_bucket(pct):
    if pct < 20: return 'empty'
    if pct < 40: return 'low'
    if pct < 65: return 'moderate'
    if pct < 85: return 'high'
    if pct < 95: return 'full'
    return 'overflow'

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    
    checkins_file = os.path.join(data_dir, 'checkins.json')
    if not os.path.exists(checkins_file):
        print("Error: checkins.json not found.")
        return
        
    with open(checkins_file, 'r') as f:
        checkins = json.load(f)
        
    # Convert string times to datetime objects
    for c in checkins:
        c['in_dt'] = datetime.fromisoformat(c['checkin_time'])
        c['out_dt'] = datetime.fromisoformat(c['checkout_time'])
        
    resources = list(config.RESOURCE_CAPACITIES.keys())
    
    # We want 15-min buckets across the whole 30 days
    # (96 buckets per day)
    # Generate the timeline
    buckets = []
    current = config.START_DATE
    end_date = config.START_DATE + timedelta(days=config.NUM_DAYS)
    
    while current < end_date:
        buckets.append(current)
        current += timedelta(minutes=15)
        
    logs = []
    
    # Process per resource (more efficient)
    for res in resources:
        res_checkins = [c for c in checkins if c['resource_name'] == res]
        # Sort checkins for two-pointer or just iterate
        # Given small size (~thousands), filtering per bucket is okay, but let's do an active window
        
        cap = config.RESOURCE_CAPACITIES[res]
        
        active_checkins = []
        checkin_idx = 0
        res_checkins.sort(key=lambda x: x['in_dt'])
        
        for bucket_time in buckets:
            bucket_end = bucket_time + timedelta(minutes=15)
            
            # Add newly arriving checkins
            while checkin_idx < len(res_checkins) and res_checkins[checkin_idx]['in_dt'] <= bucket_time:
                active_checkins.append(res_checkins[checkin_idx])
                checkin_idx += 1
                
            # Remove departed checkins
            # Keep checkins where out_dt > bucket_time
            active_checkins = [c for c in active_checkins if c['out_dt'] > bucket_time]
            
            current_occupancy = len(active_checkins)
            occ_pct = (current_occupancy / cap) * 100 if cap > 0 else 0
            status = get_status_bucket(occ_pct)
            
            logs.append({
                'resource_name': res,
                'timestamp': bucket_time.isoformat() + "Z", # Adding Z for ISO compliance as original
                'current_occupancy': current_occupancy,
                'max_capacity': cap,
                'occupancy_pct': round(occ_pct, 1),
                'status_bucket': status
            })
            
    # Save resource_logs.json
    out_json = os.path.join(data_dir, 'resource_logs.json')
    with open(out_json, 'w') as f:
        json.dump(logs, f, indent=2)
        
    print(f"Generated {len(logs)} 15-min interval logs directly from checkin events.")
    print(f"Saved to {out_json}")

if __name__ == '__main__':
    main()
