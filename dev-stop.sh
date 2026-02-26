#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORCE_PORTS="${DEV_STOP_FORCE_PORTS:-0}"

cd "$ROOT_DIR"

echo "[dev] Stopping frontend dev server (vite)..."
if command -v pkill >/dev/null 2>&1; then
  pkill -f "vite --host" || true
  pkill -f "vite" || true
else
  echo "[dev] pkill not available, please stop vite manually."
fi

echo "[dev] Stopping all compose services..."
docker compose down

check_port() {
  local port="$1"
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "[dev][warn] Port $port is still in use."
    lsof -nP -iTCP:"$port" -sTCP:LISTEN || true
    if command -v docker >/dev/null 2>&1; then
      local ids
      ids="$(docker ps --filter "publish=$port" --format "{{.ID}}" || true)"
      if [ -n "$ids" ]; then
        echo "[dev][warn] Docker containers still publishing $port:"
        docker ps --filter "publish=$port" --format "table {{.Names}}\t{{.Ports}}" || true
        if [ "$FORCE_PORTS" = "1" ]; then
          echo "[dev] DEV_STOP_FORCE_PORTS=1 set, stopping containers on port $port..."
          docker stop $ids >/dev/null || true
        else
          echo "[dev][hint] Run with DEV_STOP_FORCE_PORTS=1 to force stop non-project containers on that port."
        fi
      fi
    fi
  else
    echo "[dev] Port $port is free."
  fi
}

check_port 5173
check_port 8000
