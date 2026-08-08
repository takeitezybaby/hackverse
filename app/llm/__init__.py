"""
llm package — local Ollama LLM communication + prompt engineering,
kept separate from RAG retrieval logic (see rag/ package).
"""

from .client import OllamaLLMClient
from .prompts import build_general_query_prompt, build_personalized_report_prompt

__all__ = [
    "OllamaLLMClient",
    "build_general_query_prompt",
    "build_personalized_report_prompt",
]