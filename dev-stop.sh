#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$TASK_ROOT"
if [ -f .run/native.pids ]; then
  while IFS= read -r task_pid; do
    case "$task_pid" in ''|*[!0-9]*) continue ;; esac
    # A recycled PID must still refer to a process started for this application.
    task_command="$(ps -p "$task_pid" -o command= 2>/dev/null || true)"
    case "$task_command" in *"$TASK_ROOT"*) kill "$task_pid" 2>/dev/null || true ;; esac
  done < .run/native.pids
  rm -f .run/native.pids
fi
if [ "${DEV_BACKEND:-native}" = "docker" ]; then docker compose down; fi
