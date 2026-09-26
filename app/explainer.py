"""
explainer.py - the part of the app that talks to Claude.

main.py (the web server) calls explain_log() with the pasted log text.
This file sends it to Claude and returns a structured answer.
"""

import os

import anthropic
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Settings (read from environment variables, which docker compose loads
# from your .env file). Nothing secret is written in the code itself.
# ---------------------------------------------------------------------------

# Which Claude model to use, e.g. "claude-opus-5". Set in .env.
MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5")

# Refuse logs bigger than this many characters, so one huge paste can't
# cause a slow, expensive request. ~100k characters is roughly 25k tokens.
MAX_LOG_CHARS = 100_000


# ---------------------------------------------------------------------------
# The shape of the answer we want back from Claude.
#
# Pydantic is a library for describing data shapes. We hand this class to
# the Anthropic SDK and it makes Claude's reply follow exactly this shape,
# so we never have to guess how to read the answer.
# ---------------------------------------------------------------------------

class LogExplanation(BaseModel):
    summary: str          # A plain-English description of what happened
    root_cause: str       # The most likely reason it went wrong
    suggested_fix: str    # What to try to fix it
    key_lines: list[str]  # The most important lines copied from the log


# The instructions Claude gets before it sees the log.
SYSTEM_PROMPT = """You help junior DevOps engineers understand logs.

The user will paste a log (application, system, container, CI, etc.).
Explain it clearly, avoiding jargon where you can, and explaining it
where you can't.

- summary: what happened, in 2-4 sentences.
- root_cause: the most likely underlying cause. If the log doesn't contain
  enough information to be sure, say so and name what extra information
  would help.
- suggested_fix: concrete next steps, including commands to run where useful.
- key_lines: the few log lines (copied exactly) that matter most. Use an
  empty list if no line stands out."""


# One shared client for the whole app. It reads ANTHROPIC_API_KEY from the
# environment automatically.
client = anthropic.Anthropic()


class ExplainError(Exception):
    """An error with a message that is safe to show to the user."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code  # The HTTP status code to send back


def explain_log(log_text: str) -> LogExplanation:
    """Send the log to Claude and return its structured explanation."""

    # --- Check the input before spending money on an API call ---
    if not log_text.strip():
        raise ExplainError("Please paste a log first.", status_code=400)

    if len(log_text) > MAX_LOG_CHARS:
        raise ExplainError(
            f"That log is {len(log_text):,} characters. The limit is "
            f"{MAX_LOG_CHARS:,}. Try pasting just the part around the error.",
            status_code=413,  # 413 means "request too large"
        )

    # --- Call Claude ---
    try:
        response = client.beta.messages.parse(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": log_text}],
            # Makes Claude's reply match the LogExplanation shape above.
            output_format=LogExplanation,
            # If Claude's safety checks decline a request (rare for logs),
            # let Anthropic automatically retry it on a suitable backup model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )

    # Each kind of failure gets its own clear message. The most specific
    # error types come first, because Python uses the first one that matches.
    except anthropic.AuthenticationError:
        raise ExplainError(
            "Claude rejected the API key. Check ANTHROPIC_API_KEY in your .env file."
        )
    except anthropic.NotFoundError:
        raise ExplainError(
            f"Model '{MODEL}' was not found. Check CLAUDE_MODEL in your .env file."
        )
    except anthropic.RateLimitError:
        raise ExplainError(
            "Too many requests to Claude right now. Wait a moment and try again.",
            status_code=429,
        )
    except anthropic.APIStatusError as e:
        raise ExplainError(f"Claude API error ({e.status_code}): {e.message}", 502)
    except anthropic.APIConnectionError:
        raise ExplainError(
            "Couldn't reach the Claude API. Check the container's internet connection.",
            status_code=502,
        )

    # --- Check how the reply ended before trusting it ---
    if response.stop_reason == "refusal":
        raise ExplainError("Claude declined to analyse this log.", status_code=422)

    if response.parsed_output is None:
        raise ExplainError("Claude's reply was incomplete. Please try again.", 502)

    return response.parsed_output
