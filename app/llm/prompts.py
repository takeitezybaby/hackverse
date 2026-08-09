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
    "is insufficient to answer, say so plainly instead of guessing.\n"
    "CRITICAL FORMATTING RULE: NEVER start your response with robotic cliché openings "
    "such as 'Based on the current live state...', 'Based on the data provided...', "
    "or 'According to the forecast...'. Jump directly into a natural, conversational, and direct response."
)


def build_general_query_prompt(
    user_query: str,
    current_live_state: str,
    historical_context: str = "",
) -> str:
    """
    Mode 1 — direct student question, e.g. "When should I go to the cafeteria?",
    "When is the cafeteria most crowded?", "Where should I go now?"
    """
    context_block = historical_context.strip() or "No historical context available."

    return f"""{_GUARDRAIL}

DATA EVIDENCE & REAL-TIME DIGITAL TWIN CONTEXT:
{current_live_state}

HISTORICAL CONTEXT:
{context_block}

STUDENT QUESTION:
{user_query}

RESPONSE INSTRUCTIONS:
1. Speak directly, warmly, and naturally. DO NOT start your response with 'Based on...', 'According to...', 'NO,', or 'YES,'.
2. If asked 'where should I go now' or 'where to study/visit now', recommend the top quiet venues listed in the evidence.
3. If asked 'when is [venue] most crowded' or 'peak hours', explain the exact peak time window(s) and highest occupancy figures given in the evidence.
4. If asked 'when should I go to [venue]' or 'best time', recommend the quietest operating time slots given in the evidence.
5. Keep your response in 2-4 concise, helpful sentences. Use only figures and times explicitly present in the evidence above.

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