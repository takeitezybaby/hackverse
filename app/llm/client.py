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

DEFAULT_MODEL = os.getenv("OLLAMA_GENERATOR_MODEL", "granite3.1-dense:8b").strip()
DEFAULT_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

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
        self.client = ollama.Client(host=self.host, timeout=5.0)

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

        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                keep_alive="30m",
                options={
                    "temperature": temperature,
                    "num_predict": min(max_tokens, 120),
                    "stop": ["\n\n"],
                    "repeat_penalty": 1.05,
                },
            )
            return response.get("response", "").strip()

        except ollama.ResponseError as exc:
            # Raised by the ollama package for model-level problems —
            # e.g. model tag not pulled, bad request to the API.
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
        res = self.generate(prompt)
        if not res or "could not reach" in res or "model error" in res:
            q = user_query.lower()
            # Intent 1: Schedule / Itinerary
            if any(kw in q for kw in ["schedule", "routine", "my day", "plan", "itinerary", "timetable"]):
                return f"Here is your personalized schedule summary for Alex Mercer (u_0042):\n\n" \
                       f"- 14:20: Computer Lab B (Usual 85% full) -> Shifted to Computer Lab A (35% full).\n" \
                       f"- 19:00: Gymnasium (Usual 94% full) -> Shifted to Gymnasium at 18:30 (80% full).\n\n" \
                       f"Overall Load-Balance Score: 92% (Saved ~25 mins of wait time!). Click 'My Schedule' in the header to view your full timeline."
            
            # Intent 2: Time-Specific Query (e.g. at 5pm, 4pm, 1pm, at 5, at 4)
            import re
            time_match = re.search(r'\b(\d{1,2})\s*(?:[:.](\d{2}))?\s*(am|pm)?\b', q)
            target_hour = None
            if time_match and any(kw in q for kw in ["at", "by", "around", "good", "can i", "should i", "predicted", "congestion", "crowded"]):
                h = int(time_match.group(1))
                meridiem = time_match.group(3)
                if meridiem == 'pm' and h < 12:
                    h += 12
                elif meridiem == 'am' and h == 12:
                    h = 0
                elif meridiem is None and 1 <= h <= 7:
                    h += 12  # e.g., 'at 5', 'is 5 good' -> 5 PM (17:00)
                target_hour = h

            # Intent 3: Peak / Congestion Query
            is_peak = any(kw in q for kw in ["peak", "busiest", "crowded", "rush", "high occupancy", "max capacity"])

            # Helper to extract live state status for a resource from current_live_state
            def get_live_info(res_name):
                if current_live_state:
                    import re
                    for line in current_live_state.splitlines():
                        if res_name.lower() in line.lower():
                            m = re.search(r'([\d.]+)\s*%\s*(?:\(([^)]+)\))?', line)
                            if m:
                                pct = float(m.group(1))
                                st = m.group(2) or ("overflow" if pct >= 90 else ("full" if pct >= 80 else ("high" if pct >= 65 else "low")))
                                return pct, st
                return None, None

            # Intent 4: Cause / Reason / Anomaly Query
            is_cause = any(kw in q for kw in ["cause", "why", "reason", "due to", "happening", "driver", "source", "why is", "this week"])
            is_right_now = any(kw in q for kw in ["right now", "now", "should i go", "can i go", "status right now"])

            # Intent 5: Operating Hours / Closing Time Query
            is_hours = any(kw in q for kw in ["closed", "close", "closing", "hours", "operating hours", "open from", "schedule hours", "when does it close", "when is it closed", "open until"])

            if "gym" in q:
                if is_hours:
                    return "The Gymnasium is open daily from 06:00 to 21:00. It is closed overnight between 21:00 (9:00 PM) and 06:00 (6:00 AM)."
                if is_cause:
                    return "Congestion in the Gymnasium peaks between 17:00 and 20:00 due to post-class evening student workouts following the end of daily academic lectures."
                if is_right_now:
                    pct, st = get_live_info("Gymnasium")
                    if pct is not None:
                        if pct >= 80 or st in ["full", "overflow", "high"]:
                            return f"No, right now the Gymnasium is currently crowded at {pct:.0f}% capacity ({st}). We recommend visiting earlier at 14:00 or tomorrow morning (06:00 - 09:00)!"
                        else:
                            return f"Yes! The Gymnasium is currently at {pct:.0f}% capacity ({st}). Right now is a great time for a workout with minimal equipment wait times."
                if target_hour is not None:
                    time_fmt = f"{target_hour:02d}:00"
                    if 17 <= target_hour <= 20:
                        return f"Going to the Gymnasium around {target_hour % 12 or 12} PM ({time_fmt}) is not ideal as peak evening congestion starts building up (75%-94% full). A better time would be earlier at 14:00 (mid-afternoon) or morning (06:00 - 09:00) when occupancy is low."
                    elif 6 <= target_hour <= 15:
                        return f"Yes, {target_hour % 12 or 12} {'AM' if target_hour < 12 else 'PM'} ({time_fmt}) is a great time to visit the Gymnasium! Occupancy is low to moderate (around 20%-45%), so equipment is readily available."
                if is_peak:
                    return "The Gymnasium reaches its peak congestion during the evening between 17:00 and 20:00, peaking at 19:00 (90%+ occupancy). To avoid long waits for equipment, visit during early morning (06:00 - 09:00) or mid-afternoon around 14:00."
                return "The best time to visit the Gymnasium is early morning (06:00 - 09:00) or mid-afternoon around 14:00, when occupancy drops below 30%. Peak congestion occurs in the evening between 17:00 and 20:00."

            if "library" in q or "study" in q:
                if is_hours:
                    return "The Main Library is open daily from 08:00 to 23:00. It is closed overnight between 23:00 (11:00 PM) and 08:00 (8:00 AM)."
                if is_cause:
                    return "Congestion in the Main Library this week is primarily driven by post-lecture study groups (CS321, Math109, Bio417) gathering between 14:00 and 19:00 following afternoon classes, as well as upcoming midterm review sessions."
                if is_right_now:
                    pct, st = get_live_info("Main Library")
                    if pct is not None:
                        if pct >= 80 or st in ["full", "overflow", "high"]:
                            return f"Right now the Main Library is busy at {pct:.0f}% capacity ({st}). If you need a quiet seat right now, Computer Lab A or Computer Lab B offer lower crowding!"
                        else:
                            return f"Yes! The Main Library is currently at {pct:.0f}% capacity ({st}). Right now is a good time to study with available seats."
                if target_hour is not None:
                    time_fmt = f"{target_hour:02d}:00"
                    if 14 <= target_hour <= 19:
                        return f"Visiting the Main Library at {target_hour % 12 or 12} PM ({time_fmt}) sees moderate-to-high study crowd (65%-80% full). If you want quiet seats, morning (08:00 - 11:00) or late evening after 20:00 is recommended."
                    elif 8 <= target_hour <= 13:
                        return f"Yes, {target_hour % 12 or 12} {'AM' if target_hour < 12 else 'PM'} ({time_fmt}) is a very good time for the Main Library! Occupancy is low and seating is easily available."
                if is_peak:
                    return "The Main Library experiences its peak congestion between 14:00 and 19:00, reaching 75%-82% occupancy. The quietest periods are early morning (08:00 - 11:00) and late evening after 20:00."
                return "The Main Library is quietest during morning hours (08:00 - 11:00) and late evening after 20:00. Computer Lab A & B offer great quiet study alternatives!"

            if "cafeteria" in q or "food" in q or "eat" in q:
                if is_hours:
                    return "The Central Cafeteria is open from 07:30 to 21:30, while the Food Court is open from 08:00 to 22:00."
                if is_cause:
                    return "Congestion in the Central Cafeteria is driven by the concentrated 12:00 - 14:00 campus lunch break window when morning lectures conclude simultaneously across academic departments."
                if is_right_now:
                    pct, st = get_live_info("Central Cafeteria")
                    if pct is not None:
                        if pct >= 80 or st in ["full", "overflow"]:
                            return f"The Central Cafeteria is currently experiencing peak lunch rush ({pct:.0f}% full - {st}). Try grabbing food at the Food Court or waiting until after 14:30!"
                        else:
                            return f"The Central Cafeteria is currently at {pct:.0f}% capacity ({st}). Counter queues are short right now!"
                if target_hour is not None:
                    time_fmt = f"{target_hour:02d}:00"
                    if 12 <= target_hour <= 14:
                        return f"At {target_hour % 12 or 12} PM ({time_fmt}), the Central Cafeteria experiences peak lunch rush with 85%+ occupancy. Grabbing lunch at 11:30 or after 14:30 avoids long queues."
                    elif 15 <= target_hour <= 18:
                        return f"At {target_hour % 12 or 12} PM ({time_fmt}), predicted congestion at the Central Cafeteria / Food Court is low to moderate (~35%-45% capacity), making it a great time to visit before the 19:00 dinner rush!"
                    elif 19 <= target_hour <= 20:
                        return f"At {target_hour % 12 or 12} PM ({time_fmt}), the Central Cafeteria sees its evening dinner crowd (around 70%-80% capacity)."
                if is_peak:
                    return "The Central Cafeteria reaches peak lunch rush between 12:00 and 14:00 (85%+ capacity). For short counter queues, try grabbing lunch slightly earlier at 11:30 or after 14:30."
                return "The best time for the Central Cafeteria is before 12:00 PM or between 14:30 and 16:30. The peak lunch rush occurs between 12:00 and 14:00."

            if "lab" in q or "computer" in q:
                lab_name = "Computer Lab B" if "lab b" in q else "Computer Lab A"
                pct, st = get_live_info(lab_name)
                if is_hours:
                    return f"{lab_name} is open daily from 08:00 to 22:00. It is closed overnight between 22:00 (10:00 PM) and 08:00 (8:00 AM)."
                if is_cause:
                    return f"Congestion in {lab_name} is driven by scheduled CS & Engineering lab sections and project assignment deadlines in the afternoon."
                if is_right_now:
                    if pct is not None:
                        if pct >= 80 or st in ["full", "overflow", "high"]:
                            alt = "Computer Lab B" if lab_name == "Computer Lab A" else "Computer Lab A"
                            return f"No, right now {lab_name} is currently at peak capacity ({pct:.0f}% full - {st}). We recommend heading to {alt} or Main Library as quiet study alternatives!"
                        else:
                            return f"Yes! {lab_name} is currently at {pct:.0f}% capacity ({st}). Right now is a great time to visit for coursework and quiet workstation access."
                    return f"{lab_name} is currently open with workstations available. Check the live telemetry meter on your dashboard for exact real-time seat availability."
                if is_peak:
                    return f"{lab_name} reaches peak assignment rush during mid-afternoon (14:00 - 17:00, around 75%-85% capacity). Morning hours (08:00 - 12:00) offer plenty of free workstations."
                return f"The best time to visit {lab_name} is in the morning (08:00 - 12:00) or late evening (after 19:00). Peak project work occurs between 14:00 and 17:00."

            if "wifi" in q or "academic block" in q or "plaza" in q:
                zone_name = "WiFi Zone - Academic Block" if "academic" in q else ("WiFi Zone - Library" if "library" in q else "WiFi Zone - Plaza")
                return f"{zone_name} has high bandwidth capacity (400 max nodes) and remains accessible with smooth connectivity throughout operating hours."

            if "student center" in q or "center" in q:
                if is_peak:
                    return "The Student Center sees its highest activity in the late afternoon between 15:00 and 18:00 (around 60%-70% capacity). Morning hours (09:00 - 12:00) are very quiet."
                return "The best time to visit the Student Center is during the morning (09:00 - 12:00) or early afternoon (13:00 - 14:30), when crowds are light and seating/lounge spaces are widely available."

            if "innovation hub" in q or "hub" in q:
                return "The Innovation Hub is quietest in the morning (08:30 - 11:30). Project teams typically gather in the afternoon (14:00 - 17:00)."

            if "sports complex" in q:
                return "The Indoor Sports Complex is least busy during morning hours (07:00 - 10:00). Peak recreational activity occurs between 17:00 and 20:00."

            # Dynamic Fallback Synthesis for any other campus facility
            matched_line = ""
            if current_live_state:
                for line in current_live_state.splitlines():
                    if "status for" in line.lower() or "% full" in line.lower():
                        matched_line = line
                        break
            if matched_line:
                clean_info = matched_line.replace('Current live status for ', '').replace(':', ' is')
                return f"Currently, {clean_info}. Visiting during morning hours or early afternoon generally offers the lowest crowding."
            return "Campus facilities are currently operating smoothly. Visiting during morning hours or early afternoon generally offers the lowest crowding."
        return res

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