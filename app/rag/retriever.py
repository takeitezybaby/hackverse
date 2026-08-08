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

import json
from pathlib import Path

import numpy as np
import faiss

from .embeddings import GraniteEmbedder, EMBEDDING_DIM
from llm import OllamaLLMClient


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

        # Flat L2 index: exact search, fine at hackathon data scale
        # (hundreds-to-low-thousands of context snippets).
        self.index = faiss.IndexFlatL2(EMBEDDING_DIM)

        # FAISS only stores vectors, not the original text, so we keep a
        # parallel Python list. self.documents[i] corresponds to the
        # vector at row i of self.index.
        self.documents: list[str] = []

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def add_documents(self, texts: list[str]) -> None:
        """
        Embed and index a batch of context snippets (historical occupancy
        summaries, resource notes, campus policies, etc.).
        """
        if not texts:
            return

        vectors = self.embedder.embed_documents(texts)
        vectors_np = np.array(vectors, dtype="float32")

        self.index.add(vectors_np)
        self.documents.extend(texts)

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

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, dir_path: str) -> None:
        """
        Persist the FAISS index + underlying snippet text to disk. Run
        once after a full ingest (see scripts/build_rag_index.py) so a
        freshly started app can load() instead of re-embedding the whole
        corpus — and needing `ollama serve` up — on every launch.
        """
        out_dir = Path(dir_path)
        out_dir.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self.index, str(out_dir / "index.faiss"))

        with open(out_dir / "documents.json", "w", encoding="utf-8") as f:
            json.dump(self.documents, f, ensure_ascii=False, indent=2)

    def load(self, dir_path: str) -> None:
        """
        Load a previously-saved FAISS index + snippet text, replacing
        whatever is currently in memory. self.embedder / self.llm stay
        as set up in __init__ — only the index and documents are
        restored, since query-time embedding still needs the embedder.
        """
        in_dir = Path(dir_path)

        self.index = faiss.read_index(str(in_dir / "index.faiss"))

        with open(in_dir / "documents.json", "r", encoding="utf-8") as f:
            self.documents = json.load(f)