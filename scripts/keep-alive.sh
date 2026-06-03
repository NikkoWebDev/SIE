#!/usr/bin/env bash
set -euo pipefail
# Keep-alive cron for Render backend — run every 10 minutes
# Add to crontab: */10 * * * * /path/to/scripts/keep-alive.sh
URLS=(
  "https://sie-8agt.onrender.com/api/health"
  "https://sie-8agt.onrender.com/api/warmup"
)
for url in "${URLS[@]}"; do
  curl -s -o /dev/null -w "%{http_code}" "$url" || true
done
echo "keep-alive pinged $(date)"
