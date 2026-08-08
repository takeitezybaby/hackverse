import json
import os
import pandas as pd
from datetime import datetime
import config

def get_status_bucket(pct):
    if pct < 20: return 'empty'
    if pct < 40: return 'low'
    if pct < 65: return 'moderate'
    if pct < 85: return 'high'
    if pct < 95: return 'full'
    return 'overflow'

def get_anomaly_text_for_day(date_str, resource, ground_truth_events):
    date_dt = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    anomaly_notes = []
    
    # Exam week check
    exam_start = config.ANOMALIES['exam_week']['start_date'].date()
    exam_end = config.ANOMALIES['exam_week']['end_date'].date()
    is_exam_week = exam_start <= date_dt <= exam_end
    if is_exam_week:
        anomaly_notes.append("Exam week.")
        
    for event in ground_truth_events:
        e_start = datetime.fromisoformat(event['start']).date()
        e_end = datetime.fromisoformat(event['end']).date()
        
        if e_start <= date_dt <= e_end:
            e_type = event['event_type']
            
            if e_type == 'cultural_fest':
                if resource in event.get('affected', []):
                    anomaly_notes.append(f"Cultural fest affecting {resource}.")
                else:
                    anomaly_notes.append("Cultural fest on campus.")
                    
            elif e_type == 'infra_incident':
                if event.get('affected_resource') == resource:
                    anomaly_notes.append(f"Resource offline due to infra incident.")
                    
            elif e_type == 'class_cancellation':
                course = event.get('affected_course', 'Unknown')
                anomaly_notes.append(f"Course {course} cancelled this day.")
                
    if anomaly_notes:
        return " Anomalies: " + " ".join(anomaly_notes), is_exam_week
    else:
        return " No major anomalies.", is_exam_week

def create_daily_snapshots():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, 'data')
    snapshots_dir = os.path.join(data_dir, 'snapshots')
    
    logs_file = os.path.join(data_dir, 'resource_logs.json')
    checkins_file = os.path.join(data_dir, 'checkins.json')
    gt_file = os.path.join(data_dir, 'events_ground_truth.json')
    
    try:
        with open(logs_file, 'r') as f:
            logs = json.load(f)
        with open(checkins_file, 'r') as f:
            checkins = json.load(f)
    except FileNotFoundError:
        print("Error: Could not find resource_logs.json or checkins.json")
        return
        
    ground_truth_events = []
    if os.path.exists(gt_file):
        with open(gt_file, 'r') as f:
            gt_data = json.load(f)
            ground_truth_events = gt_data.get('events', [])
            
    df_logs = pd.DataFrame(logs)
    if df_logs.empty:
        print("Error: logs are empty")
        return
        
    # Standardize timestamps
    df_logs['timestamp'] = pd.to_datetime(df_logs['timestamp'].str.replace('Z', ''))
    df_logs['date'] = df_logs['timestamp'].dt.date.astype(str)
    df_logs['hour'] = df_logs['timestamp'].dt.hour
    
    df_checkins = pd.DataFrame(checkins)
    if not df_checkins.empty:
        df_checkins['checkin_time'] = pd.to_datetime(df_checkins['checkin_time'].str.replace('Z', ''))
        df_checkins['date'] = df_checkins['checkin_time'].dt.date.astype(str)
        df_checkins['hour'] = df_checkins['checkin_time'].dt.hour
    
    all_snapshots = []
    resources = df_logs['resource_name'].unique()
    dates = df_logs['date'].unique()
    
    for resource in resources:
        resource_slug = resource.lower().replace(' ', '_')
        res_dir = os.path.join(snapshots_dir, resource_slug)
        os.makedirs(res_dir, exist_ok=True)
        
        res_logs = df_logs[df_logs['resource_name'] == resource]
        res_checkins = df_checkins[df_checkins['resource_name'] == resource] if not df_checkins.empty else pd.DataFrame()
            
        for d_idx, date in enumerate(sorted(dates), start=1):
            day_logs = res_logs[res_logs['date'] == date]
            day_logs = day_logs[(day_logs['hour'] >= 6) & (day_logs['hour'] <= 23)]
            if day_logs.empty:
                continue
                
            day_checkins = res_checkins[res_checkins['date'] == date] if not res_checkins.empty else pd.DataFrame()
                
            dt = datetime.strptime(date, '%Y-%m-%d')
            day_of_week = dt.strftime('%A')
            
            anomaly_text, is_exam_week = get_anomaly_text_for_day(date, resource, ground_truth_events)
            
            avg_occupancy = float(day_logs['occupancy_pct'].mean())
            peak_row = day_logs.loc[day_logs['occupancy_pct'].idxmax()]
            peak_occupancy = float(peak_row['occupancy_pct'])
            peak_time = peak_row['timestamp'].strftime('%H:%M')
            
            min_row = day_logs.loc[day_logs['occupancy_pct'].idxmin()]
            min_occupancy = float(min_row['occupancy_pct'])
            min_time = min_row['timestamp'].strftime('%H:%M')
            
            hours_above_80 = float((day_logs['occupancy_pct'] > 80).sum() * 0.25)
            hours_above_60 = float((day_logs['occupancy_pct'] > 60).sum() * 0.25)
            
            hourly_profile = []
            status_counts = {'empty': 0, 'low': 0, 'moderate': 0, 'high': 0, 'full': 0, 'overflow': 0}
            
            for hour in range(6, 24):
                h_logs = day_logs[day_logs['hour'] == hour]
                if not h_logs.empty:
                    h_avg = float(h_logs['occupancy_pct'].mean())
                    status = get_status_bucket(h_avg)
                    status_counts[status] += 1
                    hourly_profile.append({"hour": f"{hour:02d}:00", "avg_pct": round(h_avg, 1), "status": status})
                    
            dominant_status = max(status_counts, key=status_counts.get) if any(status_counts.values()) else 'empty'
            
            if not day_checkins.empty:
                total_checkins = len(day_checkins)
                unique_users = day_checkins['user_id'].nunique() if 'user_id' in day_checkins.columns else 0
                avg_duration = float(day_checkins['duration_min'].mean()) if 'duration_min' in day_checkins.columns else 0
                peak_checkin_hour = f"{int(day_checkins['hour'].mode().iloc[0]):02d}:00" if not day_checkins['hour'].mode().empty else "N/A"
            else:
                total_checkins = 0; unique_users = 0; avg_duration = 0.0; peak_checkin_hour = "N/A"
                
            checkin_stats = {
                "total_checkins": total_checkins,
                "unique_users": unique_users,
                "avg_duration_min": round(avg_duration, 1),
                "peak_checkin_hour": peak_checkin_hour
            }
            
            embed_text = f"{resource} {day_of_week} {date}: Average occupancy {avg_occupancy:.1f}%, peaked at {peak_occupancy:.1f}% at {peak_time}. High occupancy (>80%) for {hours_above_80:.1f} hours. {total_checkins} check-ins from {unique_users} unique users, average visit duration {avg_duration:.0f} minutes. Peak check-in hour {peak_checkin_hour}. Dominant status: {dominant_status}.{anomaly_text}"
            
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
            
            day_file = os.path.join(res_dir, f"day_{d_idx:02d}_{day_of_week.lower()}.json")
            with open(day_file, 'w') as f:
                json.dump(snapshot, f, indent=2)
                
    combined_file = os.path.join(snapshots_dir, 'all_snapshots.json')
    with open(combined_file, 'w') as f:
        json.dump(all_snapshots, f, indent=2)
        
    print(f"Total snapshots generated: {len(all_snapshots)}")

if __name__ == "__main__":
    create_daily_snapshots()
