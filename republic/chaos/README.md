# Ministry of Emergency Events (Chaos)

Chaos Mesh (installed by `chaos-mesh` ArgoCD app) plus scheduled experiments
(`chaos-experiments` app). All experiments are **opt-in** — they only act on
namespaces carrying the label `republic.io/chaos-eligible=true`.

## Enlist a ministry for chaos

```bash
kubectl label ns ministry-heavy-computing republic.io/chaos-eligible=true
```

## Withdraw it

```bash
kubectl label ns ministry-heavy-computing republic.io/chaos-eligible-
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
