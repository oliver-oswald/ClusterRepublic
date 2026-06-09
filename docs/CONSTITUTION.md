# The Constitution

The humor is the interface; the engineering underneath is real. These are the
non-negotiable rules of the Republic.

## Articles

1. **Everything is local.** No cloud dependency is permitted in the critical
   path. Pulling public container/Helm artifacts is allowed; relying on a hosted
   control plane is not.

2. **The Git repository is the single source of truth.** If it isn't in Git,
   it does not exist. Manual `kubectl edit` against managed resources is heresy
   (ArgoCD will revert it).

3. **ArgoCD is the only enforcer.** All deployments, configs, and policy updates
   flow through ArgoCD syncing this repo. Humans change Git; Git changes the
   cluster.

4. **The AI suggests; it never rules.** The Central Committee has *read-only*
   access to Prometheus and the Kubernetes API. Its output ("Five-Year Plans",
   quota adjustments, incident responses) is advisory YAML written to its own
   store and logs. A human must commit any adopted change to Git. There is no
   code path from the model to a cluster mutation.

5. **Observability is mandatory, not optional.** Every ministry workload must
   expose health and metrics. Unmonitored workloads are illegal.

6. **Every ministry has borders.** Each namespace ships a default-deny
   NetworkPolicy plus explicit allows. No implicit cross-ministry traffic.

7. **Resources are planned.** Every ministry has a ResourceQuota and LimitRange.
   No workload may hoard beyond its allocation.

## Political ↔ Technical metrics mapping

| Metric          | Political interpretation       | Source              |
| --------------- | ------------------------------ | ------------------- |
| CPU usage       | Industrial output              | node-exporter       |
| Memory usage    | Population pressure            | node-exporter       |
| Storage usage   | Agricultural yield             | Longhorn/kubelet    |
| Network traffic | Trade volume                   | node/cni metrics    |
| Latency / p99   | Bureaucratic inefficiency      | app metrics / mesh  |
| Pod restarts    | Political instability          | kube-state-metrics  |
| OOMKills        | Famine                         | kube-state-metrics  |
| Failed admission| Counter-revolutionary activity | Kyverno metrics     |

These are the panels in the Grafana dashboards under
`republic/observability/dashboards/`.

## Priority classes (the social order)

| PriorityClass        | Value   | Who                                        |
| -------------------- | ------- | ------------------------------------------ |
| `republic-vanguard`  | 1000000 | Central Committee, observability control   |
| `republic-high`      | 100000  | Heavy Computing, security                  |
| `republic-normal`    | 1000    | Default for most ministry workloads        |
| `republic-low`       | 100     | Batch, chaos, best-effort citizens         |

Defined in `republic/ministries/_shared/priorityclasses.yaml`.
