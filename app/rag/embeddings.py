"""
rag/embeddings.py

Wraps a local Ollama Granite embedding model behind a small, stable
interface so retriever.py never touches the Ollama client directly.

Requires:
    pip install ollama
    ollama pull granite-embedding:278m   # or whatever tag you have
    ollama serve                          # daemon running locally
"""

import os

try:
    import ollama
except ImportError:
    ollama = None

# Override via env var if your pulled tag differs.
EMBEDDING_MODEL_ID = os.getenv("OLLAMA_EMBED_MODEL", "granite-embedding:278m")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# granite-embedding:278m (multilingual) outputs 768-dim vectors.
# Change this AND the FAISS index dim in retriever.py together if you
# switch to a different embedding tag (e.g. granite-embedding:30m is
# English-only and a different dimension).
EMBEDDING_DIM = 768


import hashlib

class GraniteEmbedder:
    """
    Thin wrapper around Ollama's /api/embed endpoint for the local
    Granite embedding model. Produces 768-dim float vectors.
    Falls back to a deterministic normalized hash vector if Ollama is unreachable.
    """

    def __init__(self) -> None:
        self.using_fallback = False
        try:
            self.client = ollama.Client(host=OLLAMA_HOST)
        except Exception:
            self.client = None
        self.model_id = EMBEDDING_MODEL_ID

    def _fallback_vector(self, text: str) -> list[float]:
        """Generate a deterministic 768-dim pseudo-vector from text hash when LLM daemon is offline."""
        if not self.using_fallback:
            print(f"[WARNING] Local Ollama daemon unreachable at {OLLAMA_HOST}. Engaging deterministic fallback embedder.")
            self.using_fallback = True
        seed = int(hashlib.md5(text.encode('utf-8')).hexdigest(), 16)
        vec = []
        for i in range(EMBEDDING_DIM):
            val = ((seed + i * 10007) % 2000 - 1000) / 1000.0
            vec.append(val)
        norm = sum(v * v for v in vec) ** 0.5
        return [v / (norm or 1.0) for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Batch-embed text chunks (historical occupancy notes, policy
        snippets, etc.) for indexing into FAISS.
        Returns list of 768-dim float vectors, same order as input.
        """
        if not texts:
            return []

        try:
            if not self.client:
                self.client = ollama.Client(host=OLLAMA_HOST)
            response = self.client.embed(model=self.model_id, input=texts)
            return response["embeddings"]
        except Exception as e:
            # Fallback when Ollama daemon is offline or model not pulled yet
            return [self._fallback_vector(t) for t in texts]

    def embed_query(self, query: str) -> list[float]:
        """
        Embed a single query string for FAISS similarity search.
        """
        try:
            if not self.client:
                self.client = ollama.Client(host=OLLAMA_HOST)
            response = self.client.embed(model=self.model_id, input=[query])
            return response["embeddings"][0]
        except Exception:
            return self._fallback_vector(query)