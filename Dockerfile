# Dockerfile - the recipe for building the app's container image.

# Start from a small official image that already has Python installed.
FROM python:3.12-slim

# Don't write .pyc files, and print logs immediately (no buffering),
# so you see output in `docker compose logs` right away.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# All following commands run inside this folder in the container.
WORKDIR /code

# Install dependencies first. Docker caches this step, so rebuilding after
# a code change is fast as long as requirements.txt hasn't changed.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code in.
COPY app ./app

# Run as a normal user instead of root. A good security habit.
RUN useradd --create-home appuser
USER appuser

# The app listens on port 8000 inside the container.
EXPOSE 8000

# Start the web server. 0.0.0.0 means "accept connections from outside
# the container", which is needed for your browser to reach it.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
