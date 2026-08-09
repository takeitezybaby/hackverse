"""
llm/prompts.py

All prompt construction lives here — client.py never builds prompt
strings inline, retriever.py never builds them at all. Single place to
tune wording, guardrail language, and formatting.

Every prompt embeds the same hard rule: the model explains and formats
data it is given, it never invents or recalculates numbers, times, or
probabilities. That data always comes from Layer 2 (forecast) or
Layer 3 (allocation) upstream — never from the LLM itself.
"""

# Shared guardrail block, reused verbatim in both prompt modes so the
# instruction never drifts out of sync between them.
_GUARDRAIL = (
    "You are a Campus Digital Twin Copilot assistant. Your ONLY job is to "
    "explain and format decisions and data that are given to you below. "
    "You must NEVER invent, estimate, guess, or recalculate any number, "
    "percentage, occupancy figure, capacity value, or time slot that is "
    "not explicitly present in the data given to you. If the given data "
    "is insufficient to answer, say so plainly instead of guessing."
)


def build_general_query_prompt(
    user_query: str,
    current_live_state: str,
    historical_context: str = "",
) -> str:
    """
    Mode 1 — direct student question, e.g. "Should I go to the gym now
    or at 6 PM?" or "What time should I go to the gym?"

    current_live_state: ground-truth string from Layer 2/3 (occupancy,
        forecast, capacity — whatever the upstream engine decided).
    historical_context: optional retrieved FAISS snippets, color only,
        never treated as more authoritative than current_live_state.
    """
    context_block = historical_context.strip() or "No historical context available."

    return f"""{_GUARDRAIL}

CURRENT LIVE STATE & FORECAST DATA (ground truth):
{current_live_state}

HISTORICAL CONTEXT (retrieved, for extra color only — live state & forecast data always wins):
{context_block}

STUDENT QUESTION:
{user_query}

RESPONSE INSTRUCTIONS:
1. If the question is an open-ended recommendation query (e.g., "what time should I go?", "when is the best time?"), answer directly with the recommended upcoming time slot(s) and venue options. Do NOT start your answer with "NO," or "YES,".
2. If the question is a direct yes/no decision query (e.g., "should I go right now?"), state clearly whether now is a good time based on current occupancy.
3. Keep the response in 2-4 concise, friendly, helpful sentences. Use only the exact figures and time slots provided above.

ANSWER:"""


def build_personalized_report_prompt(
    allocation_data: dict,
    historical_context: str = "",
) -> str:
    """
    Mode 2 — turns one Layer 3 allocation payload into a short "Your Day"
    dashboard card explanation.

    Expected keys in allocation_data (all upstream-computed, never
    recalculated here): user_id, resource, usual_time,
    predicted_occupancy, assigned_alternative, reason.
    Missing keys fall back to safe placeholder text rather than raising,
    since this runs against live dashboard data at demo time.
    """
    user_id = allocation_data.get("user_id", "unknown")
    resource = allocation_data.get("resource", "the resource")
    usual_time = allocation_data.get("usual_time", "your usual time")
    predicted_occupancy = allocation_data.get("predicted_occupancy", "N/A")
    assigned_alternative = allocation_data.get("assigned_alternative", "no change")
    reason = allocation_data.get("reason", "no reason provided")

    context_block = historical_context.strip() or "No historical context available."

    return f"""{_GUARDRAIL}

ALLOCATION DATA (from the load-balancing engine, ground truth):
- User: {user_id}
- Resource: {resource}
- Usual time: {usual_time}
- Predicted occupancy at usual time: {predicted_occupancy}
- Assigned alternative: {assigned_alternative}
- Reason for reassignment: {reason}

HISTORICAL CONTEXT (retrieved, for extra color only):
{context_block}

Write 2-3 short sentences for the student's daily card. Be warm and
direct. Mention the resource, why their usual time is a problem (if it
is), and what the alternative is. If assigned_alternative equals their
usual time or indicates "no change", congratulate them that no change is
needed instead of describing a swap.

CARD TEXT:"""