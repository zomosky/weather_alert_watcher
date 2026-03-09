#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$ROOT_DIR"

echo "[dev] Starting backend dependencies (db/redis/api/worker)..."
docker compose stop web >/dev/null 2>&1 || true
docker compose up -d db redis api worker

echo "[dev] Waiting for API health endpoint..."
for i in {1..30}; do
  if curl -fsS "http://localhost:8000/api/v1/health" >/dev/null 2>&1; then
    echo "[dev] API is ready."
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "[dev][warn] API health check timeout, frontend will still start."
    break
  fi
  sleep 1
done

echo "[dev] Starting frontend dev server..."
cd "$ROOT_DIR/frontend"
if [ ! -d "node_modules" ]; then
  echo "[dev] node_modules not found, running npm install..."
  npm install
fi

npm run dev
