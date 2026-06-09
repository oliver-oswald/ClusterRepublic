# Local Lab Harness (single-node, Mac/colima)

Scripts to run the entire People's Homelab Republic on one machine via
**colima + k3s** — no bare metal, no cloud. The full blueprint targets
multi-node bare metal; these scripts apply the single-node adaptations
automatically (see "What's adapted" below).

## Prerequisites

```bash
brew install colima kubectl helm   # one time
```

## Usage

```bash
./local/up.sh        # deploy everything (idempotent — safe to re-run)
./local/expose.sh    # port-forward all endpoints + start the Control Panel
                     #   add --open to launch the panel in your browser
./local/down.sh      # stop port-forwards + panel (workloads keep running)
./local/down.sh --cluster   # also stop the colima VM (state preserved)
```

`up.sh` takes ~10–20 min on a first run (image pulls + the LLM model).
`expose.sh` runs in the foreground; press **Ctrl-C** to tear forwards down.

## Endpoints (after `expose.sh`)

| Service | URL | Login |
| --- | --- | --- |
| Control Panel | http://localhost:9000 | — |
| State Cinema | http://localhost:9898 | — |
| National Archive (MinIO) | http://localhost:9101 | `republic` / `republic-archive` |
| State Registry (Adminer) | http://localhost:8081 | PostgreSQL · `state-registry` · `registrar` / `republic-registry` |
| Grafana | http://localhost:3000 | `admin` / `republic` |
| Prometheus | http://localhost:9090 | — |
| Committee API | http://localhost:8000 | `/plan`, POST `/deliberate` |
| ArgoCD | https://localhost:8080 | `admin` / see below |
| Chaos Dashboard | http://localhost:2333 | — |

ArgoCD password:
```bash
kubectl --context colima -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d; echo
```

## The Control Panel (`panel/`)

A tiny same-origin server (`panel/server.py`) that serves `panel/index.html`,
proxies the committee + Prometheus (no CORS), visualizes the latest Five-Year
Plan and the political metrics, and has buttons to **convene the committee** and
**manufacture a crisis** (Chaos Mesh faults applied via `kubectl` — the operator
creates chaos, never the read-only AI).

## What's adapted for single-node

- **Storage**: `local-path` (k3s built-in) instead of Longhorn; MetalLB and the
  Longhorn-backed MinIO are skipped (port-forwards replace LoadBalancers).
- **Quotas**: the `ResourceQuota`/`LimitRange` in `ministry-statistics` and
  `ministry-emergency-events` are dropped — upstream charts/daemonsets don't fit
  the strict ministry quotas on one node.
- **Governance engine**: run from source (`app.py`) inside a stock `python`
  image via a ConfigMap, so there's no image to build or push.
- **Loki**: the loki-stack chart's duplicate default Grafana datasource is
  removed (it otherwise crashloops Grafana).

Tunables (env vars for `up.sh`): `COLIMA_CPU`, `COLIMA_MEM`, `COLIMA_DISK`,
`MODEL`, `REPO_URL`, `REPO_REV`.
