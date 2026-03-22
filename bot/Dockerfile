FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY bot.py /app/bot.py

# Security: run as non-root user
RUN useradd --create-home appuser
USER appuser

ENV PYTHONUNBUFFERED=1

CMD ["python", "bot.py"]

