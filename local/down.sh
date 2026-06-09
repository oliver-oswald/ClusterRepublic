#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  Stop the local exposure (port-forwards + Control Panel).
#  Workloads keep running in the cluster. Pass --cluster to also stop the
#  colima VM (state is preserved; `./local/up.sh` or `colima start` resumes it).
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

echo "☭ Stopping Control Panel and port-forwards…"
# Kill expose.sh + its auto-restart loop subshells FIRST, or they respawn the forwards.
pkill -f "local/expose.sh"                2>/dev/null && echo "  expose.sh stopped"     || true
pkill -f "local/panel/server.py"          2>/dev/null && echo "  panel stopped"         || true
pkill -f "panel/server.py"                2>/dev/null || true
pkill -f "port-forward --address 127.0.0.1" 2>/dev/null && echo "  port-forwards stopped" || true

if [ "${1:-}" = "--cluster" ]; then
  echo "☭ Stopping colima VM (state preserved)…"
  colima stop
fi
echo "done."
