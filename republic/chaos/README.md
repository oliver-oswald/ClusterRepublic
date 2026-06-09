# Ministry of Emergency Events (Chaos)

Chaos Mesh (installed by `chaos-mesh` ArgoCD app) plus scheduled experiments
(`chaos-experiments` app). All experiments are **opt-in** — Chaos Mesh selects
targets by **pod** label, so they only act on pods carrying
`republic.io/chaos-eligible=true`. No pod has it by default, so nothing is
disrupted until you enlist one.

## Enlist workloads for chaos

```bash
# Label existing pods of a workload...
kubectl -n ministry-heavy-computing label pod -l app=state-cinema \
  republic.io/chaos-eligible=true

# ...or bake it into the pod template so new pods inherit it:
kubectl -n ministry-heavy-computing patch deploy state-cinema --type merge \
  -p '{"spec":{"template":{"metadata":{"labels":{"republic.io/chaos-eligible":"true"}}}}}'
```

## Withdraw them

```bash
kubectl -n ministry-heavy-computing label pod -l app=state-cinema \
  republic.io/chaos-eligible-
```

## Experiments

| File                 | Effect                                            | Schedule       |
| -------------------- | ------------------------------------------------- | -------------- |
| `pod-purge.yaml`     | Kills one eligible pod ("political purge")        | every 30 min   |
| `network-delay.yaml` | +100ms latency for 5 min ("bureaucratic slowdown")| hourly @ :15   |

## Watch the fallout

The Regional Stability Map dashboard will show restarts (instability) climb;
network delay shows up as p99 latency (bureaucratic inefficiency). The Central
Committee will note the disturbance in its next Five-Year Plan.

## Pause everything

Suspend the schedules without deleting them:

```bash
kubectl -n ministry-emergency-events patch schedule pod-purge \
  --type merge -p '{"spec":{"pause":true}}'
```
