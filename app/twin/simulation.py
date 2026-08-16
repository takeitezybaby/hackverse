"""
Live Simulation Engine for Campus Digital Twin.
Runs a background worker thread that simulates real-time student check-ins and check-outs,
persisting live telemetry into campus_twin.db for dynamic frontend rendering.
"""

import threading
import time
import random
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any

from app.contracts import RESOURCES, DB_FILE, TABLE_USER_CHECKINS
from data_gen.config import OPERATING_HOURS

class LiveSimulationEngine:
    def __init__(self):
        self._running = False
        self._thread = None
        self.simulated_time = datetime(2023, 9, 12, 12, 0, 0)  # Start at 12:00 PM peak
        self.tick_interval_seconds = 3.0  # Real-world interval per sim tick
        self.sim_minutes_per_tick = 5    # Sim time advances 5 mins per tick
        self.total_checkins_generated = 0

    def get_db_path(self) -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_dir, 'data', DB_FILE)

    def generate_tick_checkins(self):
        """Simulate random student activity across open venues for the current simulated time."""
        current_time_str = self.simulated_time.strftime('%H:%M')
        day_of_week = self.simulated_time.strftime('%A')
        db_path = self.get_db_path()

        if not os.path.exists(db_path):
            return

        checkins_to_insert = []
        user_pool = [f"u_{random.randint(1, 1400):04d}" for _ in range(20)]

        for res_name, op in OPERATING_HOURS.items():
            # Check operating hours
            if not (op['open'] <= current_time_str <= op['close']):
                continue

            # Probability of student check-in based on venue type
            is_peak = ("12:00" <= current_time_str <= "14:00") or ("17:00" <= current_time_str <= "20:00")
            prob = 0.6 if is_peak else 0.3

            if random.random() < prob:
                u_id = random.choice(user_pool)
                duration = random.choice([30, 45, 60, 90])
                in_time = self.simulated_time
                out_time = in_time + timedelta(minutes=duration)
                
                checkins_to_insert.append((
                    u_id, res_name, in_time.isoformat(), out_time.isoformat(),
                    duration, day_of_week, 1, 'live_simulation', None
                ))

        if checkins_to_insert:
            try:
                conn = sqlite3.connect(db_path, timeout=20.0)
                cursor = conn.cursor()
                cursor.executemany(f"""
                    INSERT INTO {TABLE_USER_CHECKINS} (
                        user_id, resource_name, checkin_time, checkout_time,
                        duration_min, day_of_week, is_planned, source, rerouted_from
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, checkins_to_insert)
                conn.commit()
                conn.close()
                self.total_checkins_generated += len(checkins_to_insert)
            except Exception as e:
                print(f"[SIMULATION WARNING] Error writing tick check-ins: {e}")

    def _run_loop(self):
        print(f"[LIVE SIMULATION] Background simulation engine started (Simulated Clock: {self.simulated_time.strftime('%Y-%m-%d %H:%M:%S')})")
        while self._running:
            try:
                self.generate_tick_checkins()
                self.simulated_time += timedelta(minutes=self.sim_minutes_per_tick)
                # Loop simulation back to daytime 08:00 AM if it passes 10:00 PM
                if self.simulated_time.hour >= 22:
                    self.simulated_time = self.simulated_time.replace(hour=8, minute=0, second=0)
            except Exception as e:
                print(f"[LIVE SIMULATION ERROR] {e}")
            time.sleep(self.tick_interval_seconds)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "simulated_time": self.simulated_time.strftime("%Y-%m-%d %H:%M:%S"),
            "tick_interval_seconds": self.tick_interval_seconds,
            "sim_minutes_per_tick": self.sim_minutes_per_tick,
            "total_checkins_generated": self.total_checkins_generated
        }

# Singleton instance
sim_engine = LiveSimulationEngine()
