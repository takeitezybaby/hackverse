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
    "You are a Campus Digital Twin Copilot — a helpful assistant for "
    "students navigating campus congestion. "
    "Use ONLY the data provided below. Never invent, estimate, or "
    "recalculate any number, percentage, time, or capacity figure that "
    "is not explicitly stated. If the data is insufficient, say so."
)


# Occupancy thresholds used in the recommendation rule below.
# Mirrors get_status_bucket() in daily_snapshots_gen.py exactly.
_OCCUPANCY_GUIDE = (
    "Occupancy guide: <40% = empty/low (great time to go), "
    "40-64% = moderate (comfortable), "
    "65-84% = high (busy but usable), "
    "85-94% = full (avoid if possible), "
    "95%+ = overflow (do not go now)."
)


def build_general_query_prompt(
    user_query: str,
    current_live_state: str,
    historical_context: str = "",
) -> str:
    """
    Mode 1 — direct student question, e.g. "Should I go to the gym now?"
    or "At what time should I go to the library?"

    current_live_state: pre-filtered string from Layer 2 — includes live
        occupancy AND, for timing queries, the quietest forecast slots today.
    historical_context: top-k FAISS snippets for extra colour only.
    """
    context_block = historical_context.strip() or "No additional context."

    return f"""{_GUARDRAIL}

{_OCCUPANCY_GUIDE}

LIVE OCCUPANCY DATA (ground truth, right now):
{current_live_state}

HISTORICAL PATTERNS (background context only — live data takes priority):
{context_block}

STUDENT QUESTION: {user_query}

Reply in 2-3 short, friendly sentences.
- Use the occupancy guide above to decide YES (go now) or NO (wait/avoid).
  YES only if current occupancy is below 65%. NO if 65% or above.
- State the exact current occupancy percentage and status label.
- If NO, cite the specific quieter time slot(s) from LIVE OCCUPANCY DATA
  (labelled "Quieter slots today"). Never invent times not listed above.
- Do not mention dates, snapshot names, or allocation plan IDs.

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


# Schedule-intent keywords — queries about the user's personal day/congestion plan.
# Deliberately excludes generic timing words like "when should i" / "when can i"
# because those are venue-specific timing queries handled by Mode 1 + forecast slots.
_SCHEDULE_KEYWORDS = (
    "my schedule", "my day", "check my schedule", "check my day",
    "my routine", "my plan", "my visits", "my usual", "my congestion",
    "congestion in my", "find congestion", "my timetable",
)

def is_schedule_query(query: str) -> bool:
    """Return True when the query is asking about the user's personal schedule."""
    q = query.lower()
    return any(kw in q for kw in _SCHEDULE_KEYWORDS)


def build_schedule_query_prompt(
    user_query: str,
    schedule: list,
    live_state: str,
) -> str:
    """
    Mode 3 — user asking about their own schedule and when congestion hits.

    schedule: list of schedule entries from generate_user_recommendations,
              each has habit (resource, time, predicted occupancy) and
              recommendation (alternative resource/time if congested).
    live_state: compact current occupancy for all resources.
    """
    if not schedule:
        return f"{_GUARDRAIL}\n\nNo schedule data available for this user.\n\nSTUDENT QUESTION: {user_query}\n\nANSWER:"

    lines = []
    for entry in schedule:
        habit = entry.get("habit", {})
        rec   = entry.get("recommendation", {})
        res   = habit.get("activity", habit.get("location", "Unknown"))
        time  = habit.get("time", "?")
        occ   = habit.get("usualOccupancy", "?")
        congested = habit.get("isCongested", False)

        if congested:
            alt_res  = rec.get("location", res)
            alt_time = rec.get("time", time)
            alt_occ  = rec.get("predictedOccupancy", "?")
            lines.append(
                f"  - {time}: {res} → predicted {occ}% (CONGESTED)"
                f" — suggested swap: {alt_res} at {alt_time} ({alt_occ}% predicted)"
            )
        else:
            lines.append(f"  - {time}: {res} → predicted {occ}% (OK)")

    schedule_block = "\n".join(lines)

    return f"""{_GUARDRAIL}

STUDENT'S PLANNED DAY (from the personalisation engine):
{schedule_block}

CURRENT LIVE OCCUPANCY (for context):
{live_state}

STUDENT QUESTION: {user_query}

Reply in 3-5 short, friendly sentences.
- List which of their usual stops will be congested and at what time.
- For each congested stop, state the suggested alternative from the schedule above.
- End with a one-line summary of when their day looks clear vs busy.
- Do not invent any numbers — use only the figures above.

ANSWER:"""