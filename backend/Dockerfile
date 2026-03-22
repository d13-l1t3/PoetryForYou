FROM python:3.12-slim

WORKDIR /app

# Install ffmpeg and other dependencies for faster-whisper
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
COPY requirements-audio.txt /app/requirements-audio.txt
COPY requirements-llm.txt /app/requirements-llm.txt
RUN pip install --no-cache-dir -r /app/requirements.txt -r /app/requirements-audio.txt -r /app/requirements-llm.txt

COPY app /app/app
COPY data /app/data

# Security: run as non-root user
RUN useradd --create-home appuser
USER appuser

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

