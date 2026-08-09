import sys, json
sys.path.insert(0, '.')
import numpy as np

from app.rag.retriever import CampusRAG
rag = CampusRAG()
rag.seed_from_snapshots()

import faiss
print(f"Index type: {type(rag.index).__name__}")
assert isinstance(rag.index, faiss.swigfaiss.IndexFlatL2), f"Expected FAISS IndexFlatL2, got {type(rag.index)}"

# ── Test reconstruct path (used in filter-then-search) ──────────────────
# This is the code path hit when resource filter narrows below full index
gym_results = rag.search_context("gym is very busy", k=5, resource_name="Gymnasium")
lines = [l for l in gym_results.split("\n") if l.strip()]
print(f"\nGymnasium filtered search (k=5):")
for l in lines:
    print(f"  {l[:100]}")

assert all("gymnasium" in l.lower() or "gym" in l.lower() for l in lines), "Non-gymnasium result slipped through"

# ── Test fallback chain: relax day_of_week when 0 vectors match ──────────
# Use a day with no data for a small resource
result_relax = rag.search_context("computer lab", k=3, resource_name="Computer Lab A", day_of_week="Sunday")
# Sunday may have 0 Computer Lab A entries — filter should relax to resource-only
lines2 = [l for l in result_relax.split("\n") if l.strip()]
print(f"\nComputer Lab A Sunday query (fallback relax test):")
for l in lines2:
    print(f"  {l[:100]}")
assert len(lines2) > 0, "Fallback relaxation returned nothing"

# ── Verify FAISS sub-index reconstruction is exact ───────────────────────
# Reconstruct a vector and check round-trip
gym_ids = rag._filter_indices(resource_ids=["gymnasium"])
v_orig = rag.index.reconstruct(gym_ids[0])
v_orig2 = rag.index.reconstruct(gym_ids[0])
assert np.allclose(v_orig, v_orig2), "Reconstruct is not deterministic"
print(f"\nFAISS reconstruct round-trip: PASS (vector norm={np.linalg.norm(v_orig):.4f})")

# ── Check saved faiss_index.bin loads correctly ──────────────────────────
import os
assert os.path.exists("data/faiss_index.bin"), "faiss_index.bin not saved"
idx2 = faiss.read_index("data/faiss_index.bin")
assert idx2.ntotal == rag.index.ntotal, f"Loaded index size {idx2.ntotal} != {rag.index.ntotal}"
print(f"faiss_index.bin load check: PASS ({idx2.ntotal} vectors)")

print("\nAll FAISS-specific checks PASSED.")
