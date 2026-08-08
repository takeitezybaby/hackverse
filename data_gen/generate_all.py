import subprocess
import sys
import os
import time

def run_script(name, path):
    print(f"\n{'='*50}")
    print(f"Running: {name}")
    print(f"{'='*50}")
    start = time.time()
    result = subprocess.run([sys.executable, path], capture_output=False)
    elapsed = time.time() - start
    if result.returncode != 0:
        print(f"ERROR: {name} failed with code {result.returncode}")
        sys.exit(1)
    print(f"[OK] {name} completed in {elapsed:.1f}s")

def main():
    gen_dir = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(gen_dir)
    
    scripts = [
        ('Timetable Generator', os.path.join(gen_dir, 'timetable_gen.py')),
        ('User Generator', os.path.join(gen_dir, 'user_gen.py')),
        ('Alternatives Generator', os.path.join(gen_dir, 'alternatives_gen.py')),
        ('Check-in Generator', os.path.join(gen_dir, 'checkin_gen.py')),
        ('Occupancy from Checkins', os.path.join(gen_dir, 'occupancy_from_checkins.py')),
        ('Daily Snapshots Generator', os.path.join(gen_dir, 'daily_snapshots_gen.py')),
    ]
    
    print("Campus Digital Twin — Data Generation Pipeline")
    print(f"Project root: {root}")
    
    total_start = time.time()
    for name, path in scripts:
        run_script(name, path)
    
    total_elapsed = time.time() - total_start
    print(f"\n{'='*50}")
    print(f"All generators completed in {total_elapsed:.1f}s")
    print(f"{'='*50}")

if __name__ == '__main__':
    main()