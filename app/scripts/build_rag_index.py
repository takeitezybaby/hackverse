"""
build_rag_index.py — Standalone script to rebuild the FAISS RAG index from scratch.

Usage:
    python -m app.scripts.build_rag_index

What it does:
  1. Deletes stale cached index files (faiss_index.bin, faiss_documents.json, faiss_metadata.json)
  2. Loads daily snapshots from data/snapshots/all_snapshots.json
  3. Loads crowdsourced reports from data/crowdsourced_reports.json (or SQLite fallback)
  4. Embeds all texts using GraniteEmbedder (or fallback)
  5. Saves fresh FAISS index + metadata sidecar to data/
"""

import os
import sys

# Ensure project root is on path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.rag.retriever import CampusRAG


def main():
    data_dir = os.path.join(project_root, "data")

    # Step 1: Delete stale cached files to force full rebuild
    stale_files = ["faiss_index.bin", "faiss_documents.json", "faiss_metadata.json"]
    for f in stale_files:
        path = os.path.join(data_dir, f)
        if os.path.exists(path):
            os.remove(path)
            print(f"  Deleted stale: {f}")

    # Step 2: Build fresh index
    print("\n=== Building RAG Index ===")
    rag = CampusRAG()
    total = rag.seed_from_snapshots()

    # Step 3: Verification
    print(f"\n=== Index Built: {total} vectors ===")
    print(f"  Snapshots:  {sum(1 for m in rag.metadata if m.source_type == 'daily_snapshot')}")
    print(f"  Reports:    {sum(1 for m in rag.metadata if m.source_type == 'crowdsourced_report')}")

    # Show resource distribution
    from collections import Counter
    resource_counts = Counter(m.resource_id for m in rag.metadata)
    print(f"\n  Resource distribution:")
    for resource, count in resource_counts.most_common():
        print(f"    {resource}: {count} vectors")

    # Quick search test
    print(f"\n=== Quick Search Test ===")
    result = rag.search_context("gym is crowded in the evening", k=3, resource_name="Gymnasium")
    print(f"  Query: 'gym is crowded in the evening' (filtered to Gymnasium)")
    for line in result.split("\n"):
        print(f"    {line}")

    result2 = rag.search_context("library packed no seats", k=3, resource_name="Main Library")
    print(f"\n  Query: 'library packed no seats' (filtered to Main Library)")
    for line in result2.split("\n"):
        print(f"    {line}")


if __name__ == "__main__":
    main()
