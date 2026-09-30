#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$TASK_ROOT"
mkdir -p .run
TASK_PIDS=()
cleanup() {
  for task_pid in "${TASK_PIDS[@]}"; do kill "$task_pid" 2>/dev/null || true; done
  rm -f .run/native.pids
}
trap cleanup EXIT INT TERM

if [ "${DEV_BACKEND:-native}" = "docker" ]; then
  docker compose stop web >/dev/null 2>&1 || true
  docker compose up -d db api worker
else
  if lsof -nP -iTCP:"${API_PORT:-8000}" -sTCP:LISTEN >/dev/null 2>&1 || lsof -nP -iTCP:"${WEB_PORT:-5173}" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "开发端口已占用；先停止原环境，或指定 API_PORT/WEB_PORT。"
    exit 1
  fi
  UV_CACHE_DIR="$TASK_ROOT/.cache/uv" uv sync --frozen
  export PYTHONPATH="$TASK_ROOT/backend"
  .venv/bin/python -m uvicorn app.main:app --app-dir "$TASK_ROOT/backend" --host 127.0.0.1 --port "${API_PORT:-8000}" > .run/api.log 2>&1 &
  TASK_PIDS+=("$!")
  .venv/bin/python "$TASK_ROOT/worker/app/worker.py" > .run/worker.log 2>&1 &
  TASK_PIDS+=("$!")
fi
TASK_READY=0
for task_attempt in {1..30}; do
  if curl -fsS "http://127.0.0.1:${API_PORT:-8000}/api/v1/ready" >/dev/null 2>&1; then TASK_READY=1; break; fi
  sleep 1
done
if [ "$TASK_READY" = 0 ]; then echo "API 未就绪，请查看 .run/api.log"; exit 1; fi
cd frontend
if [ ! -d node_modules ]; then npm ci; fi
VITE_API_PROXY_TARGET="http://127.0.0.1:${API_PORT:-8000}" node "$TASK_ROOT/frontend/node_modules/vite/bin/vite.js" --host 127.0.0.1 --port "${WEB_PORT:-5173}" --strictPort &
TASK_WEB_PID="$!"
TASK_PIDS+=("$TASK_WEB_PID")
printf '%s\n' "${TASK_PIDS[@]}" > "$TASK_ROOT/.run/native.pids"
wait "$TASK_WEB_PID"
