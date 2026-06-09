# Boot Sequence

What happens, in order, on a cold start. Steps 1–3 are imperative (a human runs
them once). Everything after is driven by ArgoCD sync-waves.

| Wave | Phase                         | Component(s)                                  |
| ---- | ----------------------------- | --------------------------------------------- |
| —    | Infrastructure boots          | nodes, k3s, CNI (bootstrap)                   |
| —    | GitOps core                   | ArgoCD installed, root app applied (bootstrap)|
| -20  | LoadBalancer                  | MetalLB controller + speaker                  |
| -19  | LoadBalancer config           | IPAddressPool + L2Advertisement               |
| -18  | Storage                       | Longhorn (default StorageClass)               |
| -17  | Object storage                | MinIO                                         |
| -10  | Law engine                    | Kyverno                                       |
| -5   | Ministries                    | namespaces, quotas, netpols, identities       |
| -4   | Laws                          | Kyverno ClusterPolicies                       |
| 0    | Truth System (metrics)        | kube-prometheus-stack                         |
| 1    | Truth System (logs)           | Loki + promtail                               |
| 2    | Dashboards                    | Grafana dashboards / datasources              |
| 5    | Central Committee             | Ollama, Postgres, Redis, governance-engine    |
| 10   | Emergency events              | Chaos Mesh + experiments                      |

## The deliberation loop

Once the governance-engine pod is healthy (wave 5) it runs:

1. Scrape Prometheus for the political metrics (CPU/mem/storage/restarts).
2. Read Kubernetes API state (namespaces, quotas, pod health) — **read-only**.
3. Ask Ollama to reason over the snapshot.
4. Emit a **Five-Year Plan** YAML (advisory) → Postgres + logs + `/plan` API.
5. Sleep `DELIBERATION_INTERVAL` (default 1h) and repeat.

## "The State declares itself operational"

When all Applications report `Synced/Healthy`:

```bash
kubectl -n argocd get applications
```

…the bureaucracy generator (a CronJob in `ministry-statistics`) emits its first
State Announcement to logs and a ConfigMap. The Republic is operational.
