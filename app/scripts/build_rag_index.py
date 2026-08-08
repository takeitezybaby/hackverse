"""
scripts/build_rag_index.py

One-time (re-run any time the DB changes) ingestion script: reads
campus_twin.db, aggregates raw time-series/event rows into a few hundred
natural-language context snippets, embeds them via CampusRAG (Ollama
Granite embedding model), and persists the FAISS index + snippet text to
disk so the app can load() it at startup instead of re-embedding.

Why aggregate instead of embedding every raw row:
  - user_checkins (80k+ rows) and resource_logs (34k+ rows) are
    structured time-series, not "documents" — embedding every row gives
    FAISS a haystack of near-duplicate 15-min readings, hurts retrieval
    quality, and burns hours of local Ollama embed calls for no benefit.
  - The guardrail design (llm/prompts.py _GUARDRAIL) already forbids the
    LLM from treating retrieved historical_context as anything but
    color — it needs qualitative pattern summaries ("Gymnasium peaks
    Friday mornings"), not raw numbers Layer 2/3 already compute
    authoritatively.

Produces three kinds of snippets from campus_twin.db:
  1. Occupancy pattern per resource per day-of-week (resource_logs)
  2. Reroute / overflow pairs (user_checkins.rerouted_from)
  3. Exam-period demand spikes (forecasts where cause='exam_period')

Usage:
    python scripts/build_rag_index.py --db campus_twin.db --out rag_index/

Requires `ollama serve` running locally with the embedding model pulled
(see rag/embeddings.py for the model tag / env var).
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# Allow running as `python scripts/build_rag_index.py` from repo root
# without needing the package installed.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag import CampusRAG

DAY_NAMES = {
    "0": "Sunday", "1": "Monday", "2": "Tuesday", "3": "Wednesday",
    "4": "Thursday", "5": "Friday", "6": "Saturday",
}


def build_occupancy_pattern_snippets(conn: sqlite3.Connection) -> list[str]:
    """
    Per resource, per day-of-week: peak hour, quiet hour, average load.
    Up to (resource count x 7) snippets — 84 on the reference dataset.
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT resource_name, strftime('%w', timestamp) AS dow,
               strftime('%H', timestamp) AS hr, AVG(occupancy_pct) AS avg_pct
        FROM resource_logs
        GROUP BY resource_name, dow, hr
    """)
    rows = cur.fetchall()

    # Bucket rows -> {(resource, dow): [(hour_str, avg_pct), ...]}
    buckets: dict[tuple[str, str], list[tuple[str, float]]] = {}
    for resource, dow, hr, avg_pct in rows:
        buckets.setdefault((resource, dow), []).append((hr, avg_pct))

    snippets = []
    for (resource, dow), hour_rows in buckets.items():
        if not hour_rows:
            continue

        day_name = DAY_NAMES.get(dow, dow)
        peak_hr, peak_pct = max(hour_rows, key=lambda x: x[1])
        quiet_hr, quiet_pct = min(hour_rows, key=lambda x: x[1])
        day_avg = sum(p for _, p in hour_rows) / len(hour_rows)

        snippets.append(
            f"On {day_name}s, {resource} averages {day_avg:.0f}% occupancy "
            f"across the day. It typically peaks around {peak_hr}:00 at "
            f"{peak_pct:.0f}% capacity, and is quietest around {quiet_hr}:00 "
            f"at {quiet_pct:.0f}%."
        )
    return snippets


def build_reroute_snippets(conn: sqlite3.Connection) -> list[str]:
    """
    Which resource pairs see the most reroutes, e.g. overflow from
    Computer Lab A to Computer Lab B. One snippet per (from, to) pair
    with at least 5 occurrences, to skip noise from one-off reroutes.
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT rerouted_from, resource_name, COUNT(*) AS cnt
        FROM user_checkins
        WHERE rerouted_from IS NOT NULL
        GROUP BY rerouted_from, resource_name
        HAVING cnt >= 5
        ORDER BY cnt DESC
    """)
    rows = cur.fetchall()

    snippets = []
    for from_resource, to_resource, count in rows:
        snippets.append(
            f"{count} students were rerouted from {from_resource} to "
            f"{to_resource} over the semester when {from_resource} was "
            f"over capacity — a common overflow pattern worth mentioning "
            f"when suggesting alternatives."
        )
    return snippets


def build_exam_period_snippets(conn: sqlite3.Connection) -> list[str]:
    """
    Resources with elevated demand during exam periods, per the
    forecasts.cause field. One snippet per resource/date combination.
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT resource_name, date, AVG(predicted_demand_pct), AVG(predicted_occupancy_pct)
        FROM forecasts
        WHERE cause = 'exam_period'
        GROUP BY resource_name, date
    """)
    rows = cur.fetchall()

    snippets = []
    for resource, date, avg_demand, avg_occ in rows:
        snippets.append(
            f"During the exam period on {date}, {resource} saw predicted "
            f"demand rise to an average of {avg_demand:.0f}% (occupancy "
            f"around {avg_occ:.0f}%) — noticeably higher than a typical "
            f"day, driven by exam-related traffic."
        )
    return snippets


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aggregate campus_twin.db into RAG snippets and build the FAISS index."
    )
    parser.add_argument("--db", default="campus_twin.db", help="Path to the SQLite DB")
    parser.add_argument(
        "--out", default="rag_index",
        help="Directory to persist the FAISS index + snippets to (CampusRAG.save/load)",
    )
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)

    print("Aggregating occupancy patterns...")
    occupancy_snippets = build_occupancy_pattern_snippets(conn)
    print(f"  -> {len(occupancy_snippets)} snippets")

    print("Aggregating reroute patterns...")
    reroute_snippets = build_reroute_snippets(conn)
    print(f"  -> {len(reroute_snippets)} snippets")

    print("Aggregating exam-period patterns...")
    exam_snippets = build_exam_period_snippets(conn)
    print(f"  -> {len(exam_snippets)} snippets")

    conn.close()

    all_snippets = occupancy_snippets + reroute_snippets + exam_snippets
    print(f"\nTotal snippets to embed: {len(all_snippets)}")

    if not all_snippets:
        print("No snippets generated — check the DB has data. Aborting.")
        return

    print("Embedding + indexing via CampusRAG (calls local Ollama embed model)...")
    rag = CampusRAG()
    rag.add_documents(all_snippets)
    print(f"Indexed {rag.index.ntotal} vectors.")

    rag.save(args.out)
    print(f"Saved FAISS index + snippets to {args.out}/")
    print("\nLoad it in the app with:")
    print("    rag = CampusRAG()")
    print(f"    rag.load({args.out!r})")


if __name__ == "__main__":
    main()