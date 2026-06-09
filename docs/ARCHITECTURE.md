# Architecture

## High-level

```
[ Physical Nodes / Proxmox ]
            │
[ Kubernetes (k3s default, Talos optional) ]
            │
   ┌────────────────────────────────────────────────────────┐
   │  Namespaces        = Ministries                          │
   │  NetworkPolicies   = Internal borders                    │
   │  Prometheus/Loki   = Truth System                        │
   │  Ollama + FastAPI  = Central Committee (suggest-only)    │
   │  ArgoCD            = Constitution enforcement            │
   │  Kyverno           = Law / admission control             │
   │  Chaos Mesh        = Emergency events                    │
   └────────────────────────────────────────────────────────┘
```

## Layers

### 1. Base infrastructure (`republic/infrastructure/`)
- **MetalLB** — `LoadBalancer` IPs on bare metal (L2 mode by default).
- **Longhorn** — replicated block storage (the default StorageClass).
- **MinIO** — S3-compatible object storage ("National Archive" backing store).

> CNI (Cilium/Calico) and the cluster itself are provisioned in `bootstrap/`,
> *before* ArgoCD exists, because NetworkPolicy enforcement and the API server
> must be up first. k3s ships flannel by default; swap to Cilium/Calico at
> install time if you want richer NetworkPolicy (see `bootstrap/k3s/README.md`).

### 2. GitOps core (`bootstrap/argocd/` + `republic/argocd/`)
ArgoCD runs the **app-of-apps** pattern:

```
root-app  ──watches──▶  republic/argocd/apps/*.yaml
                              │  each file = one ArgoCD Application
                              ├── infrastructure-metallb        (wave -20)
                              ├── infrastructure-metallb-config (wave -19)
                              ├── infrastructure-longhorn       (wave -18)
                              ├── infrastructure-minio          (wave -17)
                              ├── policies-kyverno              (wave -10)
                              ├── ministries                   (wave -5)
                              ├── policies-laws                 (wave -4)
                              ├── observability-prometheus      (wave 0)
                              ├── observability-loki            (wave 1)
                              ├── observability-dashboards      (wave 2)
                              ├── ai-central-committee          (wave 5)
                              └── chaos-mesh / chaos-experiments(wave 10)
```

Sync-waves (the `argocd.argoproj.io/sync-wave` annotation) guarantee ordering:
storage and admission control come up before the ministries that depend on them.

### 3. Ministry system (`republic/ministries/`)
Each ministry is a namespace plus a fixed bundle:
`Namespace` + `ResourceQuota` + `LimitRange` + `NetworkPolicy` (default-deny +
explicit allows) + `ServiceAccount` (the "minister") + `ConfigMap` (its "laws").

### 4. Observability — the Truth System (`republic/observability/`)
- **kube-prometheus-stack** (Prometheus, Alertmanager, Grafana, node-exporter,
  kube-state-metrics) via Helm.
- **Loki** + promtail for logs.
- Custom Grafana dashboards expressing the political metrics mapping
  (see `docs/CONSTITUTION.md`).

### 5. Central Committee AI (`republic/ai-central-committee/`)
A dedicated namespace running:
- **Ollama** — local LLM runtime.
- **PostgreSQL** — long-term state memory (plans, history).
- **Redis** — short-term deliberation cache.
- **governance-engine** — a FastAPI service that reads Prometheus + the
  Kubernetes API and emits a "Five-Year Plan" YAML. **It has read-only RBAC.**

### 6. Policy engine — the Law (`republic/policies/`)
**Kyverno** ClusterPolicies enforce the constitution at admission time
(resource ceilings per ministry, required labels, no `:latest` tags, etc.).
Kyverno is used instead of OPA/Gatekeeper because its policies are plain YAML
and map cleanly onto the "law" metaphor; the equivalent Rego is noted inline.

### 7. Chaos (`republic/chaos/`)
**Chaos Mesh** injects faults from `ministry-emergency-events`: pod kill,
network delay, node stress. Scheduled, bounded, and opt-in per namespace.

## Data flow when deploying a service
1. Git commit lands on the tracked branch.
2. ArgoCD detects drift and renders manifests.
3. Kyverno validates the request at admission (law check).
4. Kubernetes schedules the workload.
5. Prometheus/Loki begin tracking it immediately (ServiceMonitor / log scrape).
6. The Central Committee observes the new load on its next deliberation tick and
   may *propose* quota changes in the next Plan.
7. The bureaucracy generator writes a daily State Announcement.
