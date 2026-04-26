#!/bin/bash
set -e

# Next.js standalone needs static files copied into the standalone dir
echo "[START] Setting up Next.js static assets..."
cp -r /app/frontend/.next/static /app/frontend/.next/standalone/.next/static 2>/dev/null || true
cp -r /app/frontend/public /app/frontend/.next/standalone/public 2>/dev/null || true

echo "[START] FastAPI on :8080..."
uvicorn server.app:app --host 127.0.0.1 --port 8080 --timeout-keep-alive 30 &

echo "[START] Next.js on :3000..."
PORT=3000 HOSTNAME=127.0.0.1 node /app/frontend/.next/standalone/server.js &

echo "[START] Waiting for services..."
sleep 4

echo "[START] nginx on :7860..."
exec nginx -g 'daemon off;'
