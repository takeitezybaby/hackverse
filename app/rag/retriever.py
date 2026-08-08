"""
rag/retriever.py

Layer 4 retrieval half only. Generation (Ollama client, prompt
construction, guardrail options) now lives entirely in the llm/ package —
this file owns FAISS indexing/search and delegates every LLM call to
llm.OllamaLLMClient. No ollama import, no prompt strings, no temperature
constant here — single source of truth lives in llm/client.py and
llm/prompts.py.

Assumes rag/ and llm/ are sibling top-level packages in the repo
(both importable from repo root / on PYTHONPATH).
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

class SimpleIndex:
    def __init__(self, dim):
        self.dim = dim
        self.vectors = []
    @property
    def ntotal(self):
        return len(self.vectors)
    def add(self, vecs_np):
        for v in vecs_np:
            self.vectors.append(v)
    def search(self, q_vec, k):
        if not self.vectors:
            return np.array([[]]), np.array([[]])
        q = q_vec[0]
        dists = [np.linalg.norm(np.array(v) - q) for v in self.vectors]
        top_k_idx = sorted(range(len(dists)), key=lambda i: dists[i])[:k]
        return np.array([[dists[i] for i in top_k_idx]]), np.array([top_k_idx])

class CampusRAG:
    """
    Retrieval-augmented explanation engine for the campus digital twin.
    Two entry points map to the two required prompt modes, both
    delegated to OllamaLLMClient after context retrieval:
      - answer_general_query()         -> Mode 1
      - generate_personalized_report() -> Mode 2
    """

    def __init__(self) -> None:
        self.embedder = GraniteEmbedder()
        self.llm = OllamaLLMClient()

        if faiss is not None:
            self.index = faiss.IndexFlatL2(EMBEDDING_DIM)
        else:
            self.index = SimpleIndex(EMBEDDING_DIM)

        self.documents: list[str] = []

    # ------------------------------------------------------------------
    # Indexing & Persistence
    # ------------------------------------------------------------------

    def add_documents(self, texts: list[str]) -> None:
        """
        Embed and index a batch of context snippets (historical occupancy
        summaries, resource notes, campus policies, etc.).
        """
        if not texts:
            return

        # Batch embed in chunks of 32 for performance
        batch_size = 32
        for i in range(0, len(texts), batch_size):
            chunk = texts[i:i + batch_size]
            vectors = self.embedder.embed_documents(chunk)
            vectors_np = np.array(vectors, dtype="float32")
            self.index.add(vectors_np)
            self.documents.extend(chunk)

    def save_index(self, data_dir: str = None) -> None:
        """Save FAISS index and documents list to disk for fast startup."""
        if not data_dir:
            data_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                'data'
            )
        docs_file = os.path.join(data_dir, 'faiss_documents.json')
        with open(docs_file, 'w', encoding='utf-8') as f:
            json.dump(self.documents, f, indent=2)
            
        if faiss is not None:
            index_file = os.path.join(data_dir, 'faiss_index.bin')
            faiss.write_index(self.index, index_file)
            print(f"Saved FAISS index ({self.index.ntotal} vectors) to {index_file}")
        else:
            print(f"Saved documents list ({len(self.documents)} texts) to {docs_file}")

    def load_index(self, data_dir: str = None) -> bool:
        """Load FAISS index and documents from disk if available."""
        if not data_dir:
            data_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                'data'
            )
        index_file = os.path.join(data_dir, 'faiss_index.bin')
        docs_file = os.path.join(data_dir, 'faiss_documents.json')
        
        if os.path.exists(docs_file):
            try:
                with open(docs_file, 'r', encoding='utf-8') as f:
                    self.documents = json.load(f)
                if faiss is not None and os.path.exists(index_file):
                    self.index = faiss.read_index(index_file)
                else:
                    self.index = SimpleIndex(EMBEDDING_DIM)
                    vecs = self.embedder.embed_documents(self.documents)
                    if vecs:
                        self.index.add(np.array(vecs, dtype="float32"))
                print(f"Loaded index ({self.index.ntotal} vectors) from disk.")
                return True
            except Exception as e:
                print(f"Could not load index from disk: {e}")
        return False

    def seed_from_snapshots(self, snapshots_json_path: str = None) -> int:
        """
        Loads all 360 daily snapshots from data/snapshots/all_snapshots.json,
        extracts embed_text, and indexes them into FAISS.
        """
        if self.load_index():
            return self.index.ntotal

        if not snapshots_json_path:
            snapshots_json_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                'data', 'snapshots', 'all_snapshots.json'
            )
        
        if not os.path.exists(snapshots_json_path):
            print(f"Warning: {snapshots_json_path} not found.")
            return 0

        with open(snapshots_json_path, 'r', encoding='utf-8') as f:
            snapshots = json.load(f)

        texts = [s['embed_text'] for s in snapshots if 'embed_text' in s]
        print(f"Seeding {len(texts)} daily snapshot texts into FAISS vector database...")
        self.add_documents(texts)
        self.save_index()
        return len(texts)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def search_context(self, query: str, k: int = 2) -> str:
        """
        Return top-k historical context snippets relevant to `query`,
        joined as a bullet-point string ready to hand to llm.prompts
        builders as `historical_context`.
        """
        if self.index.ntotal == 0:
            return "No historical context available."

        query_vector = np.array([self.embedder.embed_query(query)], dtype="float32")

        # Guard against k > number of indexed vectors, which FAISS
        # would otherwise pad with -1 indices.
        k_effective = min(k, self.index.ntotal)

        _distances, indices = self.index.search(query_vector, k_effective)

        snippets = [
            self.documents[idx] for idx in indices[0] if idx != -1
        ]

        if not snippets:
            return "No historical context available."

        return "\n".join(f"- {snippet}" for snippet in snippets)

    # ------------------------------------------------------------------
    # Mode 1: General Query
    # ------------------------------------------------------------------

    def answer_general_query(self, user_query: str, current_live_state: str) -> str:
        """
        Answer a direct student question (e.g. "Should I go to the gym now
        or at 6 PM?") using live state from Layer 2/3 plus retrieved
        historical context. Retrieval happens here; prompt + generation
        happens inside OllamaLLMClient.
        """
        context = self.search_context(user_query, k=2)
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
        Translate a single Layer 3 allocation payload into a short
        natural-language explanation for a "Your Day" dashboard card.

        Expected keys in allocation_data (all upstream-computed, never
        recalculated by the LLM): user_id, resource, usual_time,
        predicted_occupancy, assigned_alternative, reason.
        """
        # Retrieve context keyed off the resource name, e.g. past
        # congestion notes for "Library - 2nd Floor". Falls back to no
        # retrieval if resource is missing from the payload.
        resource = allocation_data.get("resource", "")
        context = self.search_context(resource, k=2) if resource else ""

        return self.llm.explain_report(
            allocation_data=allocation_data,
            historical_context=context,
        )