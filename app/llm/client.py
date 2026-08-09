"""
llm/client.py

OllamaLLMClient — the ONLY place in the codebase that talks to Ollama.
retriever.py (RAG layer) should call this instead of importing `ollama`
directly, so transport concerns (host, connection errors, retries) stay
out of retrieval logic.
"""

import logging
import os

import ollama

logger = logging.getLogger(__name__)

from .prompts import build_general_query_prompt, build_personalized_report_prompt

DEFAULT_MODEL = os.getenv("OLLAMA_GENERATOR_MODEL", "granite3.1-dense:8b")
DEFAULT_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")

# Centralized so nothing downstream can silently raise temperature and
# start hallucinating numbers that contradict Layer 2/3.
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_TOKENS = 300

# Friendly fallback strings returned instead of raising — a demo
# dashboard should degrade gracefully, not crash, if Ollama hiccups.
_MODEL_ERROR_MSG = (
    "Sorry, the explanation engine hit a model error. Check that the "
    "model tag is pulled (`ollama pull {model}`) and try again."
)
_CONNECTION_ERROR_MSG = (
    "Sorry, could not reach the local LLM. Is `ollama serve` running "
    "on {host}?"
)
_EMPTY_PROMPT_MSG = "Sorry, no prompt was provided to explain."


class OllamaLLMClient:
    """
    Thin, guarded wrapper around ollama.Client. Owns:
      - the actual generate() call + its options (temperature, tokens, stop)
      - error handling for a down/misconfigured Ollama daemon
      - high-level helpers (answer_query / explain_report) that stitch
        together prompts.py builders + generate()
    """

    def __init__(self, host: str | None = None, model: str | None = None) -> None:
        self.host = host or DEFAULT_HOST
        self.model = model or DEFAULT_MODEL
        self.client = ollama.Client(host=self.host)

    # ------------------------------------------------------------------
    # Low-level generation
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> str:
        """
        Single choke point for every Ollama generate() call in the
        codebase. Keeps guardrail options (low temp, stop sequence) in
        one place and never lets a transport failure crash the caller —
        callers get a readable fallback string instead of an exception,
        since this typically feeds straight into a UI card.
        """
        if not prompt or not prompt.strip():
            logger.warning("OllamaLLMClient.generate called with empty prompt")
            return _EMPTY_PROMPT_MSG

        base_options = {
            "temperature": temperature,
            "num_predict": max_tokens,
            "stop": ["\n\n"],
            "repeat_penalty": 1.05,
            "num_gpu": -1,   # GPU-first: use all available GPUs
        }

        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options=base_options,
            )
            return response.get("response", "").strip()

        except ollama.ResponseError as exc:
            # CUDA OOM / runner crash — retry once with CPU-only (num_gpu=0).
            # This happens when other models have exhausted VRAM; the model
            # still works correctly on CPU at the cost of ~3-5s extra latency.
            if "cuda" in str(exc).lower() or "runner" in str(exc).lower() or "500" in str(exc):
                logger.warning("Ollama CUDA error, retrying with CPU (num_gpu=0): %s", exc)
                try:
                    response = self.client.generate(
                        model=self.model,
                        prompt=prompt,
                        options={**base_options, "num_gpu": 0},
                    )
                    return response.get("response", "").strip()
                except Exception as cpu_exc:
                    logger.error("CPU fallback also failed (model=%s): %s", self.model, cpu_exc)
                    return _MODEL_ERROR_MSG.format(model=self.model)
            logger.error("Ollama model error (model=%s): %s", self.model, exc)
            return _MODEL_ERROR_MSG.format(model=self.model)

        except Exception as exc:
            # Covers connection-level failures (daemon down, wrong host,
            # DNS, timeout) — these surface as httpx/requests connection
            # errors depending on ollama package version, so we catch
            # broadly here rather than pinning to one exception class.
            logger.error("Ollama connection error (host=%s): %s", self.host, exc)
            return _CONNECTION_ERROR_MSG.format(host=self.host)

    # ------------------------------------------------------------------
    # High-level helpers — wrap prompts.py builders + generate()
    # ------------------------------------------------------------------

    def answer_query(
        self,
        user_query: str,
        current_live_state: str,
        historical_context: str = "",
    ) -> str:
        """
        Mode 1: direct student question answered against live state +
        optional retrieved historical context.
        """
        prompt = build_general_query_prompt(
            user_query=user_query,
            current_live_state=current_live_state,
            historical_context=historical_context,
        )
        return self.generate(prompt)

    def explain_report(
        self,
        allocation_data: dict,
        historical_context: str = "",
    ) -> str:
        """
        Mode 2: turn one Layer 3 allocation payload into "Your Day" card
        text.
        """
        prompt = build_personalized_report_prompt(
            allocation_data=allocation_data,
            historical_context=historical_context,
        )
        return self.generate(prompt)