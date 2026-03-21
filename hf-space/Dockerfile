FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl && \
    rm -rf /var/lib/apt/lists/*

# Create app user (HF Spaces runs as uid 1000)
RUN useradd -m -u 1000 app
WORKDIR /home/app

# Copy requirements first (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the agent system
COPY openclaw-skill/ ./openclaw-skill/

# Create memory directory
RUN mkdir -p openclaw-skill/memory && chown -R app:app /home/app

USER app

# HF Spaces expects port 7860
ENV OPENCLAW_PORT=7860
ENV PYTHONUNBUFFERED=1

EXPOSE 7860

WORKDIR /home/app/openclaw-skill
CMD ["python", "api.py"]
