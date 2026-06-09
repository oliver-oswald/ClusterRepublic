#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  Expose all Republic endpoints on localhost + start the Control Panel.
#
#  Runs in the foreground. Each port-forward auto-restarts if it drops. Press
#  Ctrl-C to tear everything down cleanly. Pass --open to launch the panel in
#  your browser.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL="$REPO/local"
CTX="--context colima"
PANEL_PORT="${PANEL_PORT:-9000}"
OPEN=0; [ "${1:-}" = "--open" ] && OPEN=1

kubectl config use-context colima >/dev/null 2>&1 || { echo "colima context not found — run ./local/up.sh first"; exit 1; }

pids=()
cleanup(){ echo; echo "☭ Stopping forwards and panel…"; kill "${pids[@]}" 2>/dev/null || true; exit 0; }
trap cleanup INT TERM

# ns / service / hostPort:targetPort
forwards=(
  "argocd|svc/argocd-server|8080:443"
  "ministry-statistics|svc/kube-prometheus-stack-grafana|3000:80"
  "ministry-statistics|svc/kube-prometheus-stack-prometheus|9090:9090"
  "ai-central-committee|svc/governance-engine|8000:80"
  "ministry-emergency-events|svc/chaos-dashboard|2333:2333"
  "ministry-heavy-computing|svc/state-cinema|9898:9898"
  "ministry-agriculture|svc/national-archive|9101:9001"
  "ministry-heavy-computing|svc/state-registry-adminer|8081:8080"
)

echo "☭ Starting port-forwards…"
for f in "${forwards[@]}"; do
  IFS='|' read -r ns svc map <<<"$f"
  ( while true; do kubectl $CTX -n "$ns" port-forward --address 127.0.0.1 "$svc" "$map" >/dev/null 2>&1; sleep 2; done ) &
  pids+=("$!")
done

# wait for the panel's data sources before starting it
echo -n "  waiting for committee + prometheus"
for _ in $(seq 1 40); do
  if curl -s --max-time 2 http://127.0.0.1:8000/healthz >/dev/null 2>&1 \
     && curl -s --max-time 2 http://127.0.0.1:9090/-/ready >/dev/null 2>&1; then break; fi
  echo -n .; sleep 1
done; echo

echo "☭ Starting Control Panel on http://localhost:${PANEL_PORT}"
( PANEL_PORT="$PANEL_PORT" python3 "$LOCAL/panel/server.py" ) &
pids+=("$!")
sleep 1
[ "$OPEN" = "1" ] && (command -v open >/dev/null && open "http://localhost:${PANEL_PORT}" || true)

cat <<EOF

╔═══════════════════════════════════════════════════════════════╗
║  THE PEOPLE'S HOMELAB REPUBLIC — endpoints                     ║
╠═══════════════════════════════════════════════════════════════╣
║  Control Panel      http://localhost:${PANEL_PORT}
║  State Cinema       http://localhost:9898
║  National Archive   http://localhost:9101   (republic / republic-archive)
║  State Registry     http://localhost:8081   (Adminer → PostgreSQL,
║                       server state-registry, registrar / republic-registry)
║  Grafana            http://localhost:3000   (admin / republic)
║  Prometheus         http://localhost:9090
║  Committee API      http://localhost:8000   (/plan, POST /deliberate)
║  ArgoCD             https://localhost:8080  (admin / argocd-initial-admin-secret)
║  Chaos Dashboard    http://localhost:2333
╚═══════════════════════════════════════════════════════════════╝

Press Ctrl-C to stop.
EOF

wait
