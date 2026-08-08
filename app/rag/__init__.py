"""
rag package — Layer 4 (Reasoning & Explanation) of the Campus Digital
Twin Copilot. Exposes GraniteEmbedder and CampusRAG as the public API;
internal module layout can change without breaking callers.
"""

from .embeddings import GraniteEmbedder
from .retriever import CampusRAG

__all__ = ["GraniteEmbedder", "CampusRAG"]