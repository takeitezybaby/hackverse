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
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")

# granite-embedding:278m outputs 768-dim vectors.
EMBEDDING_DIM = 768

import hashlib
import json
import urllib.request
import time

class GraniteEmbedder:
    """
    Wrapper around Ollama's /api/embed endpoint for local Granite embeddings.
    - Uses 127.0.0.1 to avoid Windows IPv6 localhost resolution delays.
    - Uses 35s timeout to allow cold model loading into VRAM on first call.
    - Uses urllib.request as a robust fallback if the python 'ollama' package is missing.
    - Falls back to deterministic hash vectors only if Ollama server is offline.
    """

    def __init__(self) -> None:
        self.using_fallback = False
        self.host = OLLAMA_HOST
        self.model_id = EMBEDDING_MODEL_ID
        self.client = None

        if ollama is not None:
            try:
                self.client = ollama.Client(host=self.host, timeout=35.0)
            except Exception:
                self.client = None

    def _fallback_vector(self, text: str, reason: str = "") -> list[float]:
        """Generate a deterministic 768-dim pseudo-vector from text hash when LLM daemon is offline."""
        if not self.using_fallback:
            diag_reason = f" ({reason})" if reason else ""
            print(f"[WARNING] Local Ollama daemon unreachable at {self.host}{diag_reason}. Engaging deterministic fallback embedder.")
            self.using_fallback = True
        seed = int(hashlib.md5(text.encode('utf-8')).hexdigest(), 16)
        vec = []
        for i in range(EMBEDDING_DIM):
            val = ((seed + i * 10007) % 2000 - 1000) / 1000.0
            vec.append(val)
        norm = sum(v * v for v in vec) ** 0.5
        return [v / (norm or 1.0) for v in vec]

    def _embed_urllib(self, texts: list[str], num_gpu: int = -1) -> list[list[float]]:
        """Direct REST call to Ollama /api/embed using standard library urllib."""
        url = f"{self.host}/api/embed"
        payload = json.dumps({
            "model": self.model_id,
            "input": texts,
            "options": {"num_gpu": num_gpu},
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        # 35 second timeout for first-call cold model load
        with urllib.request.urlopen(req, timeout=35.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["embeddings"]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Batch-embed text chunks for indexing into FAISS.
        GPU-first: requests num_gpu=-1 (use all available GPUs).
        Falls back to CPU (num_gpu=0) on CUDA/runner errors, then to
        deterministic hash vectors only if Ollama daemon is unreachable.
        """
        if not texts:
            return []

        # Attempt 1: GPU via official ollama client
        if self.client:
            try:
                response = self.client.embed(
                    model=self.model_id,
                    input=texts,
                    options={"num_gpu": -1},
                )
                return response["embeddings"]
            except Exception as e1:
                # CUDA/runner crash → retry with CPU before giving up
                if "cuda" in str(e1).lower() or "runner" in str(e1).lower() or "500" in str(e1):
                    try:
                        response = self.client.embed(
                            model=self.model_id,
                            input=texts,
                            options={"num_gpu": 0},
                        )
                        return response["embeddings"]
                    except Exception:
                        pass
                # Client failed entirely → try urllib
                try:
                    return self._embed_urllib(texts, num_gpu=-1)
                except Exception as e_gpu:
                    # urllib GPU attempt failed → try CPU via urllib
                    try:
                        return self._embed_urllib(texts, num_gpu=0)
                    except Exception as e2:
                        return [self._fallback_vector(t, reason=f"{type(e2).__name__}: {e2}") for t in texts]

        # Attempt 2: No ollama client installed — direct urllib, GPU first
        try:
            return self._embed_urllib(texts, num_gpu=-1)
        except Exception as e_gpu:
            # GPU failed → retry CPU
            try:
                return self._embed_urllib(texts, num_gpu=0)
            except Exception as e:
                return [self._fallback_vector(t, reason=f"{type(e).__name__}: {e}") for t in texts]

    def embed_query(self, query: str) -> list[float]:
        """
        Embed a single query string for FAISS similarity search.
        """
        res = self.embed_documents([query])
        return res[0] if res else self._fallback_vector(query)