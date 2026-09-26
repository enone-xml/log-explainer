# Log Explainer

Paste a log into a web page and Claude explains it: a summary, the likely
root cause, a suggested fix, and the key log lines.

Built with Python, FastAPI, a single HTML page, the Anthropic Python SDK,
and Docker.

## How it works

```
Browser (index.html)  --POST /explain-->  FastAPI (main.py)
                                              |
                                        explainer.py  --->  Claude API
```

1. The page sends your pasted log to the backend.
2. The backend sends it to Claude and asks for an answer in a fixed shape
   (summary, root_cause, suggested_fix, key_lines).
3. The page shows the four parts.

## Project layout

| Path | What it is |
|---|---|
| `app/main.py` | Web server: serves the page and the `/explain` endpoint |
| `app/explainer.py` | Talks to Claude: prompt, answer shape, error handling |
| `app/static/index.html` | The web page (HTML + CSS + a little JavaScript) |
| `requirements.txt` | Python libraries to install |
| `Dockerfile` | How to build the container image |
| `docker-compose.yml` | How to run the container |
| `.env.example` | Template for your settings (copy to `.env`) |

## Setup

**You need:** Docker with the Compose plugin, and an Anthropic API key
(get one at https://console.anthropic.com/settings/keys).

1. Create your settings file from the template:

   ```bash
   cp .env.example .env
   ```

2. Open `.env` and replace `sk-ant-your-key-here` with your real API key.
   Optionally, change `CLAUDE_MODEL`.

3. Build and start the app:

   ```bash
   docker compose up --build
   ```

4. Open http://localhost:8000, paste a log, and click **Explain**.

To stop it, press `Ctrl+C`, or run `docker compose down` if you started it
with `-d` (detached/background mode).

## Settings (`.env`)

| Variable | Meaning |
|---|---|
| `ANTHROPIC_API_KEY` | Your secret API key. Never commit it. |
| `CLAUDE_MODEL` | Which Claude model to use. `claude-opus-5` (default) gives the best answers; `claude-sonnet-5` is cheaper and faster. |

After changing `.env`, restart the app with `docker compose up` for the
change to take effect.

## Keeping the key safe

- `.env` is listed in `.gitignore`, so git won't commit it.
- `.env` is listed in `.dockerignore`, so it isn't copied into the image.
  docker compose passes the values in as environment variables when the
  container starts.
- Check with `git status`: `.env` should never show up there.

## Troubleshooting

| Message on the page | What to do |
|---|---|
| "Claude rejected the API key" | Fix `ANTHROPIC_API_KEY` in `.env`, then restart. |
| "Model '...' was not found" | Fix `CLAUDE_MODEL` in `.env`, then restart. |
| "That log is N characters" | The log is over 100,000 characters. Paste just the part around the error. |
| "Couldn't reach the Claude API" | The container has no internet access. Check your network or proxy. |
| Page doesn't load | Is the container running? Check `docker compose ps` and `docker compose logs`. |

The app also has a health check at http://localhost:8000/health.

## Notes

- Logs you paste are sent to Anthropic's API. Remove passwords, tokens
  and personal data from a log before pasting it.
- If Claude's safety checks decline a request (rare for logs), the app asks
  Anthropic to retry it automatically on a backup model (the `fallbacks`
  setting in `explainer.py`).
