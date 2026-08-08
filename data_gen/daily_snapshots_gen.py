import json
import os
import pandas as pd
from datetime import datetime

def get_status_bucket(pct):
    if pct < 20:
        return 'empty'
    elif pct < 40:
        return 'low'
    elif pct < 65:
        return 'moderate'
    elif pct < 85:
        return 'high'
    elif pct < 95:
        return 'full'
    else:
        return 'overflow'

def create_daily_snapshots():
    # Set paths
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, 'data')
    snapshots_dir = os.path.join(data_dir, 'snapshots')
    
    logs_file = os.path.join(data_dir, 'resource_logs.json')
    checkins_file = os.path.join(data_dir, 'checkins.json')
    
    # Load data
    try:
        with open(logs_file, 'r') as f:
            logs = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find {logs_file}")
        return
        
    try:
        with open(checkins_file, 'r') as f:
            checkins = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find {checkins_file}")
        return
        
    df_logs = pd.DataFrame(logs)
    df_logs['timestamp'] = pd.to_datetime(df_logs['timestamp'])
    df_logs['date'] = df_logs['timestamp'].dt.date.astype(str)
    df_logs['hour'] = df_logs['timestamp'].dt.hour
    
    df_checkins = pd.DataFrame(checkins)
    if not df_checkins.empty:
        df_checkins['checkin_time'] = pd.to_datetime(df_checkins['checkin_time'])
        df_checkins['date'] = df_checkins['checkin_time'].dt.date.astype(str)
        df_checkins['hour'] = df_checkins['checkin_time'].dt.hour
    
    all_snapshots = []
    
    # Process each resource and date
    resources = df_logs['resource_name'].unique()
    dates = df_logs['date'].unique()
    
    for resource in resources:
        resource_slug = resource.lower().replace(' ', '_')
        res_dir = os.path.join(snapshots_dir, resource_slug)
        os.makedirs(res_dir, exist_ok=True)
        
        res_logs = df_logs[df_logs['resource_name'] == resource]
        if not df_checkins.empty:
            res_checkins = df_checkins[df_checkins['resource_name'] == resource]
        else:
            res_checkins = pd.DataFrame()
            
        for d_idx, date in enumerate(sorted(dates), start=1):
            day_logs = res_logs[res_logs['date'] == date]
            if day_logs.empty:
                continue
                
            day_logs = day_logs[(day_logs['hour'] >= 6) & (day_logs['hour'] <= 23)]
            if day_logs.empty:
                continue
                
            if not res_checkins.empty:
                day_checkins = res_checkins[res_checkins['date'] == date]
            else:
                day_checkins = pd.DataFrame()
                
            # Date info
            dt = datetime.strptime(date, '%Y-%m-%d')
            day_of_week = dt.strftime('%A')
            is_exam_week = ('2023-09-25' <= date <= '2023-09-30')
            
            # Summary stats
            avg_occupancy = float(day_logs['occupancy_pct'].mean())
            peak_row = day_logs.loc[day_logs['occupancy_pct'].idxmax()]
            peak_occupancy = float(peak_row['occupancy_pct'])
            peak_time = peak_row['timestamp'].strftime('%H:%M')
            
            min_row = day_logs.loc[day_logs['occupancy_pct'].idxmin()]
            min_occupancy = float(min_row['occupancy_pct'])
            min_time = min_row['timestamp'].strftime('%H:%M')
            
            # Calculate hours above thresholds based on 15 min intervals (each is 0.25 hours)
            hours_above_80 = float((day_logs['occupancy_pct'] > 80).sum() * 0.25)
            hours_above_60 = float((day_logs['occupancy_pct'] > 60).sum() * 0.25)
            
            # Hourly profile
            hourly_profile = []
            status_counts = {'empty': 0, 'low': 0, 'moderate': 0, 'high': 0, 'full': 0, 'overflow': 0}
            
            for hour in range(6, 24):
                h_logs = day_logs[day_logs['hour'] == hour]
                if not h_logs.empty:
                    h_avg = float(h_logs['occupancy_pct'].mean())
                    status = get_status_bucket(h_avg)
                    status_counts[status] += 1
                    hourly_profile.append({
                        "hour": f"{hour:02d}:00",
                        "avg_pct": round(h_avg, 1),
                        "status": status
                    })
                    
            dominant_status = max(status_counts, key=status_counts.get) if any(status_counts.values()) else 'empty'
            
            # Checkin stats
            if not day_checkins.empty:
                total_checkins = len(day_checkins)
                unique_users = day_checkins['user_id'].nunique() if 'user_id' in day_checkins.columns else 0
                avg_duration = float(day_checkins['duration_min'].mean()) if 'duration_min' in day_checkins.columns else 0
                peak_checkin_hour = f"{int(day_checkins['hour'].mode().iloc[0]):02d}:00" if not day_checkins.empty and not day_checkins['hour'].mode().empty else "N/A"
            else:
                total_checkins = 0
                unique_users = 0
                avg_duration = 0.0
                peak_checkin_hour = "N/A"
                
            checkin_stats = {
                "total_checkins": total_checkins,
                "unique_users": unique_users,
                "avg_duration_min": round(avg_duration, 1),
                "peak_checkin_hour": peak_checkin_hour
            }
            
            exam_text = " Exam week." if is_exam_week else " Not exam week."
            embed_text = f"{resource} {day_of_week} {date}: Average occupancy {avg_occupancy:.1f}%, peaked at {peak_occupancy:.1f}% at {peak_time}. High occupancy (>80%) for {hours_above_80:.1f} hours. {total_checkins} check-ins from {unique_users} unique users, average visit duration {avg_duration:.0f} minutes. Peak check-in hour {peak_checkin_hour}. Dominant status: {dominant_status}.{exam_text}"
            
            snapshot = {
                "resource": resource,
                "resource_slug": resource_slug,
                "date": date,
                "day_of_week": day_of_week,
                "day_index": d_idx,
                "is_exam_week": is_exam_week,
                "summary": {
                    "avg_occupancy_pct": round(avg_occupancy, 1),
                    "peak_occupancy_pct": round(peak_occupancy, 1),
                    "peak_time": peak_time,
                    "min_occupancy_pct": round(min_occupancy, 1),
                    "min_time": min_time,
                    "hours_above_80_pct": round(hours_above_80, 1),
                    "hours_above_60_pct": round(hours_above_60, 1),
                    "dominant_status": dominant_status
                },
                "hourly_profile": hourly_profile,
                "checkin_stats": checkin_stats,
                "embed_text": embed_text
            }
            
            all_snapshots.append(snapshot)
            
            # Save day file
            day_file = os.path.join(res_dir, f"day_{d_idx:02d}_{day_of_week.lower()}.json")
            with open(day_file, 'w') as f:
                json.dump(snapshot, f, indent=2)
                
    # Save combined file
    combined_file = os.path.join(snapshots_dir, 'all_snapshots.json')
    with open(combined_file, 'w') as f:
        json.dump(all_snapshots, f, indent=2)
        
    print(f"Total snapshots generated: {len(all_snapshots)}")
    for resource in resources:
        count = sum(1 for s in all_snapshots if s['resource'] == resource)
        print(f"  - {resource}: {count}")

if __name__ == "__main__":
    create_daily_snapshots()
