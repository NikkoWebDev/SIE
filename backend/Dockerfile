FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m -u 1001 vyntra && chown -R vyntra:vyntra /app
USER vyntra

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:10000/api/health')" || exit 1

CMD uvicorn main:app \
    --host 0.0.0.0 \
    --port 10000 \
    --workers 1 \
    --loop uvloop \
    --ws-ping-interval 25 \
    --ws-ping-timeout 10 \
    --timeout-keep-alive 120
