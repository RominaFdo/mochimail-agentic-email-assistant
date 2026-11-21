# Mochimail: AI email agent (FastAPI web UI)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Don't run as root.
RUN useradd --create-home mochi
USER mochi

EXPOSE 8000
CMD ["python", "server.py"]
