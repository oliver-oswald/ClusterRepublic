# ☭ The People's Homelab Republic

> Kubernetes dressed up as a Cold War simulator — running on your desk, quietly
> becoming more stable than most real governments.

A complete, **local-first**, GitOps-driven Kubernetes homelab blueprint. Under
the (intentionally heavy) political theming, this is a real, reproducible
platform that teaches:

- distributed systems & cluster bootstrapping
- GitOps (ArgoCD app-of-apps)
- policy-as-code (Kyverno admission control)
- observability (Prometheus, Grafana, Loki)
- AI orchestration (a *suggest-only* governance engine on top of Ollama)
- chaos engineering (Chaos Mesh)

Nothing here requires a cloud account. It targets bare metal or a Proxmox
cluster running **k3s** (default) or Talos.

---

## The Metaphor (and why it maps to real infra)

| Theme term            | Real Kubernetes concept                                  |
| --------------------- | -------------------------------------------------------- |
| Ministry              | Namespace + ResourceQuota + LimitRange + NetworkPolicy   |
| Minister              | ServiceAccount identity for the namespace                |
| Laws                  | ConfigMaps + Kyverno policies (admission control)        |
| The Constitution      | This Git repo, enforced by ArgoCD                        |
| Truth System          | Prometheus / Grafana / Loki                              |
| Central Committee     | Ollama + a FastAPI "governance engine" (suggests only)   |
| Five-Year Plan        | A YAML artifact the AI proposes; ArgoCD/humans enforce   |
| Emergency Events      | Chaos Mesh fault injection                               |

**Hard rule:** the AI never mutates the cluster directly. It reads state and
emits *suggestions*. Git + ArgoCD + humans remain the only path to change.
See [`docs/CONSTITUTION.md`](docs/CONSTITUTION.md).

---

## Repository Layout

```
.
├── docs/                         # Architecture, constitution, deployment, boot sequence
├── bootstrap/                    # One-time cluster + ArgoCD bring-up (imperative)
│   ├── k3s/                      # k3s install notes
│   └── argocd/                   # ArgoCD install + the root app-of-apps
└── republic/                     # Everything ArgoCD manages (declarative)
    ├── argocd/                   # AppProject + Application definitions (app-of-apps)
    ├── infrastructure/           # MetalLB, Longhorn, MinIO
    ├── ministries/               # Namespaces, quotas, network policies, identities
    ├── policies/                 # Kyverno cluster policies ("laws")
    ├── observability/            # Grafana dashboards & datasources (the Truth System)
    ├── ai-central-committee/     # Ollama, Postgres, Redis, governance-engine (+ source)
    └── chaos/                    # Chaos Mesh experiments (ministry-emergency-events)
```

ArgoCD only ever syncs the `republic/` tree. The `bootstrap/` tree is run by a
human once to get ArgoCD itself onto the cluster.

---

## Quick Start (TL;DR)

```bash
# 0. Stand up a k3s cluster (see bootstrap/k3s/README.md), then:
export KUBECONFIG=~/.kube/republic.yaml

# 1. One-time bootstrap: install ArgoCD and hand it the constitution.
./bootstrap/argocd/install.sh
kubectl apply -f bootstrap/argocd/root-app.yaml

# 2. Watch the Republic assemble itself.
kubectl -n argocd get applications -w
```

ArgoCD then reads `republic/argocd/apps/` and brings up everything else in
dependency order using sync-waves. Full walkthrough:
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

---

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system overview & layers
- [`docs/CONSTITUTION.md`](docs/CONSTITUTION.md) — design philosophy & non-negotiable rules
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — step-by-step deployment
- [`docs/BOOT_SEQUENCE.md`](docs/BOOT_SEQUENCE.md) — what happens, in what order, on cold start

---

## Status

This is a **blueprint**. Cluster-specific values (IP ranges, storage sizes,
domain names, the GitOps repo URL) are marked with `# CHANGEME` and collected in
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md). Adjust them before declaring the
State operational.
