"""
main.py - the web server.

It does two things:
  1. GET  /         -> sends the web page (static/index.html) to your browser
  2. POST /explain  -> receives a log from the page, asks Claude, returns JSON
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.explainer import ExplainError, LogExplanation, explain_log

app = FastAPI(title="Log Explainer")

# The folder that holds index.html, found relative to this file.
STATIC_DIR = Path(__file__).parent / "static"


class ExplainRequest(BaseModel):
    """What the page sends us: {"log": "...the pasted text..."}"""

    log: str


@app.get("/")
def home():
    """Serve the single HTML page."""
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/explain", response_model=LogExplanation)
def explain(request: ExplainRequest):
    """Explain a log. Returns summary, root_cause, suggested_fix, key_lines."""
    try:
        return explain_log(request.log)
    except ExplainError as e:
        # Send a friendly error the page can display, with a proper HTTP code.
        return JSONResponse(status_code=e.status_code, content={"error": e.message})


@app.get("/health")
def health():
    """A tiny endpoint that says "I'm alive". Handy for monitoring later."""
    return {"status": "ok"}
