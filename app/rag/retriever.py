"""
rag/retriever.py

Layer 4 retrieval engine for the campus digital twin.

Architecture:
  - Single flat FAISS index with metadata sidecar for filter-first retrieval
  - Two embedding sources: daily_snapshots (360 vectors) + crowdsourced_reports
  - Filter by resource_id, weekday, anomaly type BEFORE similarity search
  - Delegates all LLM calls to llm.OllamaLLMClient

Retrieval flow:
  1. Filter metadata index to matching resource_id (+ optional weekday/anomaly)
  2. Build sub-index or mask over filtered vector IDs
  3. Top-k similarity search within filtered subset
  4. Pass retrieved context + numeric forecast data to Granite generation
"""

import numpy as np
try:
    import faiss
except ImportError:
    faiss = None

from .embeddings import GraniteEmbedder, EMBEDDING_DIM

try:
    from app.llm.client import OllamaLLMClient
except Exception:
    try:
        from llm import OllamaLLMClient
    except Exception:
        class DummyLLMClient:
            def answer_query(self, user_query, current_live_state, historical_context=""):
                return f"Answer for query '{user_query}' with live state: {current_live_state}. Context: {historical_context}"
            def explain_report(self, allocation_data, historical_context=""):
                res = allocation_data.get("resource", "Gymnasium")
                orig = allocation_data.get("usual_time", "19:00")
                alt = allocation_data.get("assigned_alternative", "18:30")
                return f"{res} hits peak congestion at {orig} ({allocation_data.get('predicted_occupancy', '94%')} full). Shifting to {alt} avoids the rush."
        OllamaLLMClient = DummyLLMClient

import os
import json
import sqlite3
from typing import Optional, List, Dict, Any


# ------------------------------------------------------------------
# Simple in-memory fallback when FAISS is not installed
# ------------------------------------------------------------------

class SimpleIndex:
    def __init__(self, dim):
        self.dim = dim
        self.vectors = []

    @property
    def ntotal(self):
        return len(self.vectors)

    def add(self, vecs_np):
        for v in vecs_np:
            self.vectors.append(v.copy())

    def search(self, q_vec, k):
        if not self.vectors:
            return np.array([[]]), np.array([[]])
        q = q_vec[0]
        dists = [float(np.linalg.norm(np.array(v) - q)) for v in self.vectors]
        top_k_idx = sorted(range(len(dists)), key=lambda i: dists[i])[:k]
        return np.array([[dists[i] for i in top_k_idx]]), np.array([top_k_idx])


# ------------------------------------------------------------------
# Vector metadata record — stored alongside each embedded document
# ------------------------------------------------------------------

class VectorMeta:
    """Lightweight metadata sidecar for each vector in the FAISS index."""
    __slots__ = ("vector_id", "source_type", "resource_id", "date",
                 "day_of_week", "cause", "embed_text")

    def __init__(self, vector_id: int, source_type: str, resource_id: str,
                 date: str, day_of_week: str = "", cause: str = None,
                 embed_text: str = ""):
        self.vector_id = vector_id
        self.source_type = source_type          # "daily_snapshot" | "crowdsourced_report"
        self.resource_id = resource_id           # e.g. "gymnasium", "main_library"
        self.date = date                         # "2023-09-11"
        self.day_of_week = day_of_week           # "Tuesday"
        self.cause = cause                       # anomaly label or None
        self.embed_text = embed_text             # the raw text that was embedded

    def to_dict(self) -> dict:
        return {
            "vector_id": self.vector_id,
            "source_type": self.source_type,
            "resource_id": self.resource_id,
            "date": self.date,
            "day_of_week": self.day_of_week,
            "cause": self.cause,
            "embed_text": self.embed_text,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "VectorMeta":
        return cls(**d)


# ------------------------------------------------------------------
# Resource name normaliser — maps display names to slug IDs
# ------------------------------------------------------------------

def _slug(name: str) -> str:
    """Convert a display resource name to a lowercase slug for filtering.
    Must match the convention in daily_snapshots_gen.py: lower().replace(' ', '_')
    """
    return name.lower().replace(" ", "_")


# ==================================================================
# CampusRAG — metadata-aware retrieval engine
# ==================================================================

class CampusRAG:
    """
    Retrieval-augmented explanation engine for the campus digital twin.

    Corpus:
      1. Daily resource snapshots (360 vectors) — situational summaries
         with occupancy pattern, cause label, and Layer 3 allocation outcome.
      2. Crowdsourced reports — genuine student-submitted free text.

    Retrieval strategy:
      Filter first (resource_id, optional weekday/anomaly), search second.
      Never search globally then filter — avoids cross-resource noise.

    Two generation modes (both delegated to OllamaLLMClient):
      - answer_general_query()         → Mode 1 (interactive Q&A)
      - generate_personalized_report() → Mode 2 (Your Day card)
    """

    def __init__(self) -> None:
        self.embedder = GraniteEmbedder()
        self.llm = OllamaLLMClient()

        if faiss is not None:
            self.index = faiss.IndexFlatL2(EMBEDDING_DIM)
        else:
            self.index = SimpleIndex(EMBEDDING_DIM)

        # Parallel arrays — self.metadata[i] describes self.index vector i
        self.metadata: List[VectorMeta] = []
        # Legacy compat — plain text list used by save/load
        self.documents: List[str] = []

    # ------------------------------------------------------------------
    # Data directory helper
    # ------------------------------------------------------------------

    def _data_dir(self) -> str:
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data"
        )

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def _add_vectors(self, texts: List[str], metas: List[VectorMeta]) -> None:
        """Embed texts and add to FAISS index with paired metadata."""
        if not texts:
            return
        batch_size = 32
        for i in range(0, len(texts), batch_size):
            chunk_texts = texts[i:i + batch_size]
            chunk_metas = metas[i:i + batch_size]
            vectors = self.embedder.embed_documents(chunk_texts)
            vectors_np = np.array(vectors, dtype="float32")
            self.index.add(vectors_np)
            self.metadata.extend(chunk_metas)
            self.documents.extend(chunk_texts)

    def add_documents(self, texts: List[str]) -> None:
        """
        Legacy API — embed and index plain texts without metadata.
        Used for backward-compat; prefer _add_vectors with metadata.
        """
        if not texts:
            return
        metas = []
        base_id = len(self.metadata)
        for i, t in enumerate(texts):
            metas.append(VectorMeta(
                vector_id=base_id + i,
                source_type="daily_snapshot",
                resource_id="unknown",
                date="",
                embed_text=t,
            ))
        self._add_vectors(texts, metas)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_index(self, data_dir: str = None) -> None:
        """Save FAISS index, documents, and metadata to disk."""
        data_dir = data_dir or self._data_dir()

        # Save documents list
        docs_file = os.path.join(data_dir, "faiss_documents.json")
        with open(docs_file, "w", encoding="utf-8") as f:
            json.dump(self.documents, f, indent=2)

        # Save metadata sidecar
        meta_file = os.path.join(data_dir, "faiss_metadata.json")
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump([m.to_dict() for m in self.metadata], f, indent=2)

        # Save FAISS binary index
        if faiss is not None:
            index_file = os.path.join(data_dir, "faiss_index.bin")
            faiss.write_index(self.index, index_file)
            print(f"Saved FAISS index ({self.index.ntotal} vectors) + metadata to {data_dir}")
        else:
            print(f"Saved {len(self.documents)} documents + metadata to {data_dir}")

    def load_index(self, data_dir: str = None) -> bool:
        """Load FAISS index, documents, and metadata from disk."""
        data_dir = data_dir or self._data_dir()
        index_file = os.path.join(data_dir, "faiss_index.bin")
        docs_file = os.path.join(data_dir, "faiss_documents.json")
        meta_file = os.path.join(data_dir, "faiss_metadata.json")

        if not os.path.exists(docs_file):
            return False

        try:
            with open(docs_file, "r", encoding="utf-8") as f:
                self.documents = json.load(f)

            # Load metadata if available
            if os.path.exists(meta_file):
                with open(meta_file, "r", encoding="utf-8") as f:
                    self.metadata = [VectorMeta.from_dict(d) for d in json.load(f)]
            else:
                # Backward compat: create stub metadata
                self.metadata = [
                    VectorMeta(vector_id=i, source_type="daily_snapshot",
                               resource_id="unknown", date="", embed_text=doc)
                    for i, doc in enumerate(self.documents)
                ]

            # Load FAISS index
            if faiss is not None and os.path.exists(index_file):
                self.index = faiss.read_index(index_file)
            else:
                self.index = SimpleIndex(EMBEDDING_DIM)
                if self.documents:
                    vecs = self.embedder.embed_documents(self.documents)
                    if vecs:
                        self.index.add(np.array(vecs, dtype="float32"))

            print(f"Loaded index ({self.index.ntotal} vectors, {len(self.metadata)} metadata records) from disk.")
            return True
        except Exception as e:
            print(f"Could not load index from disk: {e}")
            return False

    # ------------------------------------------------------------------
    # Seeding — builds the full corpus
    # ------------------------------------------------------------------

    def seed_from_snapshots(self, snapshots_json_path: str = None) -> int:
        """
        Build the full RAG corpus from two sources:
          1. Daily snapshots (data/snapshots/all_snapshots.json)
          2. Crowdsourced reports (data/campus_twin.db or data/crowdsourced_reports.json)

        Loads from disk cache if available.
        """
        if self.load_index():
            return self.index.ntotal

        data_dir = self._data_dir()

        # --- Source 1: Daily snapshots ---
        if not snapshots_json_path:
            snapshots_json_path = os.path.join(data_dir, "snapshots", "all_snapshots.json")

        snapshot_texts = []
        snapshot_metas = []

        if os.path.exists(snapshots_json_path):
            with open(snapshots_json_path, "r", encoding="utf-8") as f:
                snapshots = json.load(f)

            for i, s in enumerate(snapshots):
                if "embed_text" not in s:
                    continue
                text = s["embed_text"]
                resource_slug = s.get("resource_slug", _slug(s.get("resource", "unknown")))
                cause = s.get("cause", None)
                # If cause is in anomaly_text, extract from there
                if cause is None:
                    anomaly_text = text.split(".")[-1].strip() if text else ""
                    if "Anomal" in anomaly_text or "Exam" in anomaly_text or "fest" in anomaly_text:
                        cause = anomaly_text

                meta = VectorMeta(
                    vector_id=i,
                    source_type="daily_snapshot",
                    resource_id=resource_slug,
                    date=s.get("date", ""),
                    day_of_week=s.get("day_of_week", ""),
                    cause=cause,
                    embed_text=text,
                )
                snapshot_texts.append(text)
                snapshot_metas.append(meta)

            print(f"Seeding {len(snapshot_texts)} daily snapshot texts into FAISS...")
        else:
            print(f"Warning: {snapshots_json_path} not found.")

        # --- Source 2: Crowdsourced reports ---
        report_texts = []
        report_metas = []

        # Try JSON file first
        reports_json_path = os.path.join(data_dir, "crowdsourced_reports.json")
        reports = []

        if os.path.exists(reports_json_path):
            with open(reports_json_path, "r", encoding="utf-8") as f:
                reports = json.load(f)
        else:
            # Fallback to SQLite
            db_path = os.path.join(data_dir, "campus_twin.db")
            if os.path.exists(db_path):
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.execute(
                        "SELECT resource_name, timestamp, comment FROM crowdsourced_reports "
                        "WHERE comment IS NOT NULL AND comment != ''"
                    )
                    for row in cursor.fetchall():
                        reports.append({
                            "resource_name": row[0],
                            "timestamp": row[1],
                            "comment": row[2],
                        })
                    conn.close()
                except Exception as e:
                    print(f"Could not load crowdsourced reports from DB: {e}")

        base_id = len(snapshot_texts)
        for j, report in enumerate(reports):
            comment = report.get("comment", "").strip()
            if not comment:
                continue

            resource_name = report.get("resource_name", "unknown")
            timestamp = report.get("timestamp", "")
            date_str = timestamp[:10] if len(timestamp) >= 10 else ""

            # Parse day of week from timestamp
            dow = ""
            try:
                from datetime import datetime
                dow = datetime.strptime(date_str, "%Y-%m-%d").strftime("%A")
            except Exception:
                pass

            # Build embed text: prefix with resource and date for context
            embed_text = f"{resource_name} {dow} {date_str} — Student report: {comment}"

            meta = VectorMeta(
                vector_id=base_id + j,
                source_type="crowdsourced_report",
                resource_id=_slug(resource_name),
                date=date_str,
                day_of_week=dow,
                cause=None,
                embed_text=embed_text,
            )
            report_texts.append(embed_text)
            report_metas.append(meta)

        if report_texts:
            print(f"Seeding {len(report_texts)} crowdsourced report texts into FAISS...")

        # --- Combine and index ---
        all_texts = snapshot_texts + report_texts
        all_metas = snapshot_metas + report_metas

        if all_texts:
            self._add_vectors(all_texts, all_metas)
            self.save_index()
            print(f"Total corpus: {len(all_texts)} vectors "
                  f"({len(snapshot_texts)} snapshots + {len(report_texts)} reports)")

        return self.index.ntotal

    # ------------------------------------------------------------------
    # Filter-first retrieval
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Filter-first retrieval
    # ------------------------------------------------------------------

    def _filter_indices(self, resource_ids: List[str] = None,
                        day_of_week: str = None,
                        anomaly_type: str = None,
                        source_type: str = None) -> List[int]:
        """
        Return vector indices matching the given metadata filters.
        All filters are optional; None means 'match anything'.
        resource_ids can be a list of resource slugs (e.g. ['main_library', 'gymnasium']).
        """
        matching = []
        res_set = set(resource_ids) if resource_ids else None
        for i, m in enumerate(self.metadata):
            if res_set and m.resource_id not in res_set:
                continue
            if day_of_week and m.day_of_week.lower() != day_of_week.lower():
                continue
            if anomaly_type and (m.cause is None or anomaly_type.lower() not in m.cause.lower()):
                continue
            if source_type and m.source_type != source_type:
                continue
            matching.append(i)
        return matching

    def search_context(self, query: str, k: int = 5,
                       resource_name: str = None,
                       resource_names: List[str] = None,
                       day_of_week: str = None,
                       anomaly_type: str = None) -> str:
        """
        Filter-first, search-second retrieval.

        Given a query, filter to matching resource(s)/weekday/anomaly,
        then run FAISS similarity search within the filtered subset.
        Fallback hierarchy:
          1. Exact filter (resources + day_of_week + anomaly)
          2. Resource filter only (if day_of_week yields 0 results)
          3. Global search across all 480 vectors (if 0 resources named or 0 results)
        """
        if self.index.ntotal == 0:
            return "No historical context available."

        # Compute query embedding
        query_vector = np.array([self.embedder.embed_query(query)], dtype="float32")

        # Collect target resource slugs
        slugs = []
        if resource_names:
            slugs.extend([_slug(r) for r in resource_names if r])
        elif resource_name:
            slugs.append(_slug(resource_name))

        # Attempt 1: Filter with all criteria (resource + day_of_week + anomaly)
        filtered_ids = self._filter_indices(
            resource_ids=slugs if slugs else None,
            day_of_week=day_of_week,
            anomaly_type=anomaly_type,
        )

        # Attempt 2: If day_of_week filter produced 0 vectors, relax day_of_week filter
        if not filtered_ids and day_of_week and slugs:
            filtered_ids = self._filter_indices(
                resource_ids=slugs,
                anomaly_type=anomaly_type,
            )

        # Attempt 3: If no resources named or 0 results, fall back to global search
        if not filtered_ids:
            filtered_ids = list(range(self.index.ntotal))

        # Perform search over filtered_ids subset
        top_ids = []
        if isinstance(self.index, SimpleIndex):
            q = query_vector[0]
            dists = []
            for global_idx in filtered_ids:
                if global_idx < len(self.index.vectors):
                    v = self.index.vectors[global_idx]
                    d = float(np.linalg.norm(np.array(v) - q))
                    dists.append((d, global_idx))
            dists.sort(key=lambda x: x[0])
            top_ids = [gid for _, gid in dists[:k]]
        elif faiss is not None and len(filtered_ids) < self.index.ntotal:
            sub_index = faiss.IndexFlatL2(EMBEDDING_DIM)
            filtered_vectors = np.zeros((len(filtered_ids), EMBEDDING_DIM), dtype="float32")
            for local_i, global_i in enumerate(filtered_ids):
                filtered_vectors[local_i] = self.index.reconstruct(global_i)
            sub_index.add(filtered_vectors)

            k_effective = min(k, sub_index.ntotal)
            _distances, local_indices = sub_index.search(query_vector, k_effective)
            top_ids = [filtered_ids[local_idx] for local_idx in local_indices[0] if local_idx != -1]
        else:
            k_effective = min(k, self.index.ntotal)
            _distances, indices = self.index.search(query_vector, k_effective)
            top_ids = [idx for idx in indices[0] if idx != -1]

        snippets = []
        for global_idx in top_ids:
            if global_idx < len(self.metadata):
                snippets.append(self.metadata[global_idx].embed_text)
            elif global_idx < len(self.documents):
                snippets.append(self.documents[global_idx])

        if not snippets:
            return "No historical context available."

        return "\n".join(f"- {snippet}" for snippet in snippets[:k])

    # ------------------------------------------------------------------
    # Query parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_resources_from_query(query: str) -> List[str]:
        """
        Identify ALL campus resources mentioned in the user's query.
        Handles multi-resource queries (e.g. 'library or gym').
        Returns list of canonical resource names.
        """
        query_lower = query.lower()
        resource_keywords = {
            "main library": "Main Library",
            "science library": "Science Library",
            "central cafeteria": "Central Cafeteria",
            "cafeteria": "Central Cafeteria",
            "food court": "Food Court",
            "gymnasium": "Gymnasium",
            "gym": "Gymnasium",
            "indoor sports": "Indoor Sports Complex",
            "sports complex": "Indoor Sports Complex",
            "student center": "Student Center",
            "computer lab a": "Computer Lab A",
            "comp lab a": "Computer Lab A",
            "computer lab b": "Computer Lab B",
            "comp lab b": "Computer Lab B",
            "wifi zone academic": "WiFi Zone - Academic Block",
            "wifi academic": "WiFi Zone - Academic Block",
            "wifi zone library": "WiFi Zone - Library",
            "wifi library": "WiFi Zone - Library",
            "wifi zone cafeteria": "WiFi Zone - Cafeteria",
            "wifi cafeteria": "WiFi Zone - Cafeteria",
            "library": "Main Library",
        }
        found = []
        # Sort keywords by length descending to match longer specific names first
        for keyword in sorted(resource_keywords.keys(), key=len, reverse=True):
            if keyword in query_lower:
                canonical = resource_keywords[keyword]
                if canonical not in found:
                    found.append(canonical)
                # Remove matched keyword snippet to avoid overlapping sub-matches
                query_lower = query_lower.replace(keyword, "")
        return found

    @staticmethod
    def _extract_day_of_week_from_query(query: str) -> Optional[str]:
        """
        Extract explicit day of week from query text if present.
        Returns capitalized day name (e.g. 'Tuesday') or None.
        """
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        query_lower = query.lower()
        for d in days:
            if d in query_lower:
                return d.capitalize()
        return None

    # ------------------------------------------------------------------
    # Mode 1: General Query
    # ------------------------------------------------------------------

    def answer_general_query(self, user_query: str, current_live_state: str) -> str:
        """
        Answer a direct student question using live state + retrieved
        historical context. Automatically extracts resource(s) and weekday.
        """
        resources = self._extract_resources_from_query(user_query)
        day_of_week = self._extract_day_of_week_from_query(user_query)
        context = self.search_context(
            user_query, k=5,
            resource_names=resources if resources else None,
            day_of_week=day_of_week,
        )
        return self.llm.answer_query(
            user_query=user_query,
            current_live_state=current_live_state,
            historical_context=context,
        )

    # ------------------------------------------------------------------
    # Mode 2: Personalized Daily Report
    # ------------------------------------------------------------------

    def generate_personalized_report(self, allocation_data: dict) -> str:
        """
        Translate a Layer 3 allocation payload into a natural-language
        explanation for a 'Your Day' dashboard card.
        """
        resource = allocation_data.get("resource", "")
        context = self.search_context(
            resource, k=5,
            resource_name=resource,
        ) if resource else ""

        return self.llm.explain_report(
            allocation_data=allocation_data,
            historical_context=context,
        )

    # ------------------------------------------------------------------
    # Unified answer endpoint (used by API routes)
    # ------------------------------------------------------------------

    def answer_question(self, user_query: str,
                        current_live_state: str = "Gymnasium: 89.5% (full)") -> dict:
        """
        Answer a query and return structured dict with fallback status.
        Used by POST /api/ask.
        """
        ans = self.answer_general_query(user_query, current_live_state)
        is_fb = getattr(self.embedder, "using_fallback", False)
        return {
            "answer": ans,
            "engine": "Rule-Based Fallback Engine" if is_fb else "Granite 3.1 (Ollama Local)",
            "is_fallback": is_fb,
            "fallback_warning": (
                "Local Ollama daemon unreachable on port 11434. Running on fallback mode."
                if is_fb else None
            ),
        }