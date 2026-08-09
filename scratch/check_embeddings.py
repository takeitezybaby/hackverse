"""
End-to-end diagnostic for embeddings + retrieval.

Tests:
  1. Embedder: Ollama or fallback? Correct dim? Distinct vectors for distinct text?
  2. Snapshot embed_text: sample content quality
  3. Index build: vector count matches corpus size; metadata alignment
  4. Retrieval: filter correctness (resource, day_of_week, source_type)
  5. Semantic ranking: relevant result scores higher than irrelevant
  6. vector_id offset bug check (snapshot vs report IDs)
"""

import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"

def check(label, cond, detail=""):
    status = PASS if cond else FAIL
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{status}] {label}{suffix}")
    return cond

# ── 1. Embedder diagnostics ──────────────────────────────────────────────
print("\n=== 1. Embedder ===")
from app.rag.embeddings import GraniteEmbedder, EMBEDDING_DIM

emb = GraniteEmbedder()
t1 = "Science Library is overcrowded on Tuesday evenings"
t2 = "Gymnasium has free slots on Sunday morning"
t3 = "Science Library is overcrowded on Tuesday evenings"   # same as t1

vecs = emb.embed_documents([t1, t2, t3])

check("Returns 3 vectors for 3 inputs", len(vecs) == 3, f"got {len(vecs)}")
check(f"Each vector is {EMBEDDING_DIM}-dim", all(len(v) == EMBEDDING_DIM for v in vecs),
      f"dims={[len(v) for v in vecs]}")
check("Not using fallback (Ollama live)", not emb.using_fallback,
      "hash-based fallback active — retrieval quality will be degraded")

# Identical text → identical vector
dot_same = sum(a*b for a,b in zip(vecs[0], vecs[2]))
norm0 = math.sqrt(sum(x*x for x in vecs[0]))
norm2 = math.sqrt(sum(x*x for x in vecs[2]))
cos_same = dot_same / (norm0 * norm2) if norm0 and norm2 else 0

# Different text → different vector (cosine < 0.99)
dot_diff = sum(a*b for a,b in zip(vecs[0], vecs[1]))
norm1 = math.sqrt(sum(x*x for x in vecs[1]))
cos_diff = dot_diff / (norm0 * norm1) if norm0 and norm1 else 0

check("Identical texts produce identical vectors", cos_same > 0.9999, f"cos={cos_same:.6f}")
check("Different texts produce different vectors", cos_diff < 0.99, f"cos={cos_diff:.4f}")
check("Vectors are unit-normalised (L2 ~= 1.0)", abs(norm0 - 1.0) < 0.01, f"L2={norm0:.4f}")

# ── 2. Snapshot embed_text quality ──────────────────────────────────────
print("\n=== 2. Snapshot embed_text content ===")
with open("data/snapshots/all_snapshots.json") as f:
    snaps = json.load(f)

print(f"  Total snapshots: {len(snaps)}")
missing_embed = [s for s in snaps if not s.get("embed_text")]
check("All snapshots have embed_text", len(missing_embed) == 0, f"{len(missing_embed)} missing")

zero_demand = [s for s in snaps if s["peak_demand_pct"] == 0.0 and s["summary"]["peak_occupancy_pct"] > 0]
check("No snapshot has 0% true demand with nonzero observed", len(zero_demand) == 0, f"{len(zero_demand)} broken")

# Check embed_text actually contains both observed and true-demand
malformed = [s for s in snaps if "(observed)" not in s.get("embed_text","") or "(true demand)" not in s.get("embed_text","")]
check("embed_text contains observed & true demand labels", len(malformed) == 0, f"{len(malformed)} malformed")

# Sample 3 embed_texts
print("\n  Sample embed_texts:")
import random; random.seed(7)
for s in random.sample(snaps, 3):
    print(f"    [{s['resource_slug']} {s['date']} {s['day_of_week']}]")
    print(f"     {s['embed_text']}")

# ── 3. Index build ───────────────────────────────────────────────────────
print("\n=== 3. Index build ===")
# Delete stale cache to force a fresh build so we test the actual pipeline
import os
for f in ["faiss_index.bin","faiss_documents.json","faiss_metadata.json"]:
    p = os.path.join("data", f)
    if os.path.exists(p):
        os.remove(p)
        print(f"  Removed stale cache: {f}")

from app.rag.retriever import CampusRAG
rag = CampusRAG()
total = rag.seed_from_snapshots()

with open("data/crowdsourced_reports.json") as f:
    reports = json.load(f)
reports_with_comment = sum(1 for r in reports if r.get("comment","").strip())
expected = len(snaps) + reports_with_comment

check(f"Index vector count ({total}) == corpus size ({expected})", total == expected,
      f"delta={total - expected}")
check("Metadata length == index size", len(rag.metadata) == total,
      f"meta={len(rag.metadata)} idx={total}")
check("Documents list length == index size", len(rag.documents) == total,
      f"docs={len(rag.documents)}")

# Check vector_id field in metadata is contiguous 0..N-1
ids = [m.vector_id for m in rag.metadata]
check("vector_id values are contiguous 0..N-1", ids == list(range(total)),
      f"first mismatch at {next((i for i,v in enumerate(ids) if v!=i), 'none')}")

# Check source_type breakdown
n_snaps  = sum(1 for m in rag.metadata if m.source_type == "daily_snapshot")
n_reports = sum(1 for m in rag.metadata if m.source_type == "crowdsourced_report")
check(f"Snapshot vectors ({n_snaps}) == {len(snaps)}", n_snaps == len(snaps))
check(f"Report vectors ({n_reports}) == {reports_with_comment}", n_reports == reports_with_comment)

# ── 4. Filter correctness ────────────────────────────────────────────────
print("\n=== 4. Metadata filter correctness ===")

# resource filter
gym_ids = rag._filter_indices(resource_ids=["gymnasium"])
gym_metas = [rag.metadata[i] for i in gym_ids]
check("All gymnasium-filtered records have resource_id=gymnasium",
      all(m.resource_id == "gymnasium" for m in gym_metas),
      f"count={len(gym_ids)}")

# day_of_week filter
tue_ids = rag._filter_indices(resource_ids=["gymnasium"], day_of_week="Tuesday")
tue_metas = [rag.metadata[i] for i in tue_ids]
check("Day-of-week filter returns only Tuesdays",
      all(m.day_of_week == "Tuesday" for m in tue_metas),
      f"count={len(tue_ids)}")

# source_type filter
report_ids = rag._filter_indices(source_type="crowdsourced_report")
check("source_type filter returns only reports",
      all(rag.metadata[i].source_type == "crowdsourced_report" for i in report_ids),
      f"count={len(report_ids)}")

# empty filter = all
all_ids = rag._filter_indices()
check("Empty filter returns all vectors", len(all_ids) == total, f"got {len(all_ids)}")

# ── 5. Semantic ranking ──────────────────────────────────────────────────
print("\n=== 5. Semantic retrieval quality ===")

# Query about gym crowding → top results should be gymnasium, not library
result_gym = rag.search_context("gym is packed and crowded evening", k=5, resource_name="Gymnasium")
snippets_gym = [l.lstrip("- ") for l in result_gym.split("\n") if l.strip()]
check("Gymnasium query returns results", len(snippets_gym) > 0, f"got {len(snippets_gym)}")
check("Gymnasium query results mention gymnasium",
      all("gymnasium" in s.lower() or "gym" in s.lower() for s in snippets_gym),
      f"offending: {[s[:60] for s in snippets_gym if 'gym' not in s.lower()]}")

# Query about library → results should be library, not gym
result_lib = rag.search_context("library seats all taken no space", k=5, resource_name="Main Library")
snippets_lib = [l.lstrip("- ") for l in result_lib.split("\n") if l.strip()]
check("Library query returns results", len(snippets_lib) > 0)
check("Library query results mention library",
      all("library" in s.lower() for s in snippets_lib),
      f"offending: {[s[:60] for s in snippets_lib if 'library' not in s.lower()]}")

# Global query (no resource filter) — should still return relevant results
result_global = rag.search_context("overcrowded during exam week", k=5)
snippets_global = [l.lstrip("- ") for l in result_global.split("\n") if l.strip()]
check("Global query (no filter) returns results", len(snippets_global) > 0)
has_exam = any("exam" in s.lower() for s in snippets_global)
check("Global exam-week query surfaces exam-related snippets", has_exam,
      f"snippets: {[s[:70] for s in snippets_global]}")

# Day-of-week filter in search_context path
result_tue = rag.search_context("cafeteria busy", k=5, resource_name="Central Cafeteria", day_of_week="Tuesday")
snippets_tue = [l.lstrip("- ") for l in result_tue.split("\n") if l.strip()]
check("Day-of-week filtered search returns results", len(snippets_tue) > 0)

print("\n=== Done ===")
