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

import ollama

# Override via env var if your pulled tag differs.
EMBEDDING_MODEL_ID = os.getenv("OLLAMA_EMBED_MODEL", "granite-embedding:278m")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# granite-embedding:278m (multilingual) outputs 768-dim vectors.
# Change this AND the FAISS index dim in retriever.py together if you
# switch to a different embedding tag (e.g. granite-embedding:30m is
# English-only and a different dimension).
EMBEDDING_DIM = 768


class GraniteEmbedder:
    """
    Thin wrapper around Ollama's /api/embed endpoint for the local
    Granite embedding model. Produces 768-dim float vectors.
    """

    def __init__(self) -> None:
        self.client = ollama.Client(host=OLLAMA_HOST)
        self.model_id = EMBEDDING_MODEL_ID

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Batch-embed text chunks (historical occupancy notes, policy
        snippets, etc.) for indexing into FAISS.

        Returns list of 768-dim float vectors, same order as input.
        """
        if not texts:
            return []

        response = self.client.embed(model=self.model_id, input=texts)
        return response["embeddings"]

    def embed_query(self, query: str) -> list[float]:
        """
        Embed a single query string for FAISS similarity search.
        """
        response = self.client.embed(model=self.model_id, input=[query])
        return response["embeddings"][0]