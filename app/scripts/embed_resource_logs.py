"""
scripts/embed_resource_logs.py

Embeds resource_logs.csv row-by-row using the same GraniteEmbedder /
CampusRAG pipeline as the rest of the RAG layer (rag/embeddings.py,
rag/retriever.py), and persists the resulting FAISS index to disk via
CampusRAG.save().

Heads up before running: this is raw per-row embedding, not the
aggregated pattern-snippet approach in scripts/build_rag_index.py.
34,560 rows means 34,560 near-duplicate 15-min occupancy readings going
into FAISS — fine as a checkpoint / deliverable proving the pipeline
runs end-to-end on the raw dataset, but for actual runtime retrieval
quality the aggregated snippets will serve much better results. Kept
completely separate — writes to its own --out directory, never touches
the aggregated index from build_rag_index.py.

Usage:
    python scripts/embed_resource_logs.py \\
        --csv resource_logs.csv \\
        --out rag_index_raw_logs/ \\
        --batch-size 200

Requires `ollama serve` running locally with the embedding model pulled
(see rag/embeddings.py for the model tag / OLLAMA_EMBED_MODEL env var).
"""

import argparse
import csv
import sys
import time
from pathlib import Path

# Allow running as `python scripts/embed_resource_logs.py` from repo root
# without needing the package installed.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag import CampusRAG


def row_to_text(row: dict) -> str:
    """
    Turn one resource_logs.csv row into a single embeddable sentence.
    Field names match the CSV header exactly:
    resource_id, resource_name, timestamp, current_occupancy,
    max_capacity, occupancy_pct, status_bucket.
    """
    return (
        f"{row['resource_name']} ({row['resource_id']}) at {row['timestamp']}: "
        f"{row['current_occupancy']}/{row['max_capacity']} occupied "
        f"({row['occupancy_pct']}% capacity, status: {row['status_bucket']})."
    )


def load_rows(csv_path: str) -> list[str]:
    """Read the CSV and convert every row to its embeddable text form."""
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [row_to_text(row) for row in reader]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Embed resource_logs.csv into FAISS via the RAG pipeline."
    )
    parser.add_argument("--csv", default="resource_logs.csv", help="Path to resource_logs.csv")
    parser.add_argument(
        "--out", default="rag_index_raw_logs",
        help="Directory to persist the FAISS index + row text to (kept separate from the aggregated index)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=200,
        help="Rows per embed() call — keeps individual requests to Ollama a manageable size",
    )
    args = parser.parse_args()

    print(f"Reading {args.csv}...")
    texts = load_rows(args.csv)
    print(f"  -> {len(texts)} rows loaded")

    if not texts:
        print("No rows found — aborting.")
        return

    print("Initializing CampusRAG (GraniteEmbedder + FAISS index)...")
    rag = CampusRAG()

    total_batches = (len(texts) + args.batch_size - 1) // args.batch_size
    start = time.time()

    for i in range(0, len(texts), args.batch_size):
        batch = texts[i : i + args.batch_size]
        batch_num = i // args.batch_size + 1

        rag.add_documents(batch)

        elapsed = time.time() - start
        print(
            f"  batch {batch_num}/{total_batches} embedded  "
            f"({rag.index.ntotal}/{len(texts)} rows, {elapsed:.0f}s elapsed)"
        )

    print(f"\nIndexed {rag.index.ntotal} vectors in {time.time() - start:.0f}s.")

    rag.save(args.out)
    print(f"Saved FAISS index + row text to {args.out}/")
    print("\nLoad it later with:")
    print("    rag = CampusRAG()")
    print(f"    rag.load({args.out!r})")


if __name__ == "__main__":
    main()