"""
setup.py — One-time data setup for Campus Digital Twin.

Run this once after cloning (before starting the app):
    python setup.py

What it does (in order):
  1. Generate all JSON data files        (data_gen/generate_all.py)
  2. Generate crowdsourced reports       (data_gen/crowdsourced_reports_gen.py)
  3. Initialise the SQLite DB schema     (app/db/database.py)
  4. Seed the DB from generated JSON     (app/db/seed.py)
  5. Cache Layer-2 forecasts into DB     (app/twin/forecast.py)
  6. Build the FAISS RAG index           (app/scripts/build_rag_index.py)

Safe to re-run — each step clears its own previous state before writing.
Requires: pip install -r requirements.txt
Requires: ollama serve  +  ollama pull granite-embedding:278m
          (needed only for step 6; steps 1-5 work offline)
"""

import sys
import os
import time

# Ensure project root is on path
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

# ── Colour helpers (degrade gracefully on Windows without ANSI) ──────────
def _c(code, text):
    try:
        return f"\033[{code}m{text}\033[0m"
    except Exception:
        return text

OK   = lambda t: _c("92", f"[OK]  {t}")
ERR  = lambda t: _c("91", f"[ERR] {t}")
HDR  = lambda t: _c("96", f"\n{'='*54}\n  {t}\n{'='*54}")
WARN = lambda t: _c("93", f"[WARN] {t}")

def step(n, total, label, fn):
    print(HDR(f"Step {n}/{total}: {label}"))
    t0 = time.time()
    try:
        fn()
        print(OK(f"Done in {time.time()-t0:.1f}s"))
    except SystemExit as e:
        print(ERR(f"Step exited with code {e.code}"))
        sys.exit(e.code)
    except Exception as e:
        print(ERR(str(e)))
        import traceback; traceback.print_exc()
        sys.exit(1)

# ────────────────────────────────────────────────────────────────────────
# Step 1 — Generate all JSON data files
# ────────────────────────────────────────────────────────────────────────
def run_data_generators():
    import subprocess
    gen_dir = os.path.join(ROOT, "data_gen")
    scripts = [
        ("Timetable Generator",        "timetable_gen.py"),
        ("User Generator",             "user_gen.py"),
        ("Alternatives Generator",     "alternatives_gen.py"),
        ("Check-in Generator",         "checkin_gen.py"),
        ("Occupancy from Checkins",    "occupancy_from_checkins.py"),
        ("Daily Snapshots Generator",  "daily_snapshots_gen.py"),
    ]
    for name, filename in scripts:
        print(f"  -> {name} ...", end=" ", flush=True)
        t = time.time()
        r = subprocess.run(
            [sys.executable, os.path.join(gen_dir, filename)],
            cwd=gen_dir,
            capture_output=True, text=True
        )
        if r.returncode != 0:
            print()
            print(ERR(f"{name} failed"))
            print(r.stderr[-800:] if r.stderr else "(no stderr)")
            sys.exit(1)
        print(f"done ({time.time()-t:.1f}s)")

# ────────────────────────────────────────────────────────────────────────
# Step 2 — Generate crowdsourced reports JSON + insert into DB
# ────────────────────────────────────────────────────────────────────────
def run_reports_gen():
    import subprocess
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "data_gen", "crowdsourced_reports_gen.py")],
        cwd=os.path.join(ROOT, "data_gen"),
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(r.stderr[-800:])
        sys.exit(1)
    print(f"  {r.stdout.strip()}")

# ────────────────────────────────────────────────────────────────────────
# Step 3 — Initialise SQLite schema
# ────────────────────────────────────────────────────────────────────────
def init_schema():
    from app.db.database import init_db
    init_db()
    print("  Schema created / verified.")

# ────────────────────────────────────────────────────────────────────────
# Step 4 — Seed DB from JSON files
# ────────────────────────────────────────────────────────────────────────
def seed_database():
    import sqlite3
    from app.db.database import DB_PATH
    from app.db.seed import seed_db

    # Clear existing rows so re-runs don't duplicate data
    conn = sqlite3.connect(DB_PATH)
    for table in ("user_checkins", "users", "timetables", "resource_logs"):
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()

    seed_db()

# ────────────────────────────────────────────────────────────────────────
# Step 5 — Cache Layer-2 forecasts into the DB
# ────────────────────────────────────────────────────────────────────────
def cache_forecasts():
    from app.twin.forecast import cache_forecasts_to_db
    cache_forecasts_to_db()   # caches all 30 days x 12 resources x 72 slots

# ────────────────────────────────────────────────────────────────────────
# Step 6 — Build FAISS RAG index
# ────────────────────────────────────────────────────────────────────────
def build_rag():
    data_dir = os.path.join(ROOT, "data")
    # Remove stale index files so seed_from_snapshots does a full rebuild
    for fname in ("faiss_index.bin", "faiss_documents.json", "faiss_metadata.json"):
        p = os.path.join(data_dir, fname)
        if os.path.exists(p):
            os.remove(p)

    from app.rag.retriever import CampusRAG
    rag = CampusRAG()
    n = rag.seed_from_snapshots()
    if n == 0:
        raise RuntimeError("FAISS index built 0 vectors — something went wrong.")
    print(f"  FAISS index built: {n} vectors")


# ────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(_c("95", "\n  Campus Digital Twin — First-Time Setup\n"))

    STEPS = [
        ("Generate JSON data files",        run_data_generators),
        ("Generate crowdsourced reports",   run_reports_gen),
        ("Initialise SQLite schema",        init_schema),
        ("Seed database from JSON",         seed_database),
        ("Cache Layer-2 forecasts to DB",   cache_forecasts),
        ("Build FAISS RAG index",           build_rag),
    ]

    for i, (label, fn) in enumerate(STEPS, 1):
        step(i, len(STEPS), label, fn)

    print(_c("92", f"\n  Setup complete! You can now run: run_demo_mode.bat\n"))
