# Deployment Guide

## 0. Prerequisites

- 1 control-plane node + 2–5 workers (bare metal or Proxmox VMs).
- `kubectl`, `helm`, and `git` on your workstation.
- A reachable LAN IP range you can dedicate to MetalLB.
- This repo pushed to a Git remote ArgoCD can reach.

## 1. Values you MUST change (`# CHANGEME`)

| What                | File                                                              |
| ------------------- | ----------------------------------------------------------------- |
| GitOps repo URL     | `bootstrap/argocd/root-app.yaml`, `republic/argocd/apps/*.yaml`   |
| MetalLB IP pool     | `republic/infrastructure/metallb/config/ipaddresspool.yaml`       |
| Storage sizes       | `republic/infrastructure/minio/values.yaml`, ministry quotas      |
| Ingress/domain      | dashboards & ingress objects (none assumed by default)            |
| Postgres password   | `republic/ai-central-committee/base/postgres-secret.yaml`         |

A quick way to find them all:

```bash
grep -rn "CHANGEME" .
```

> Set the repo URL everywhere at once:
> ```bash
> NEW=https://github.com/<you>/<repo>.git
> grep -rl "https://github.com/CHANGEME/republic.git" . \
>   | xargs sed -i "s#https://github.com/CHANGEME/republic.git#${NEW}#g"
> ```

## 2. Cluster

See `bootstrap/k3s/README.md` for the k3s install (control plane + workers,
optional Cilium/Calico CNI). Confirm:

```bash
kubectl get nodes -o wide
```

## 3. ArgoCD bootstrap (one time)

```bash
./bootstrap/argocd/install.sh        # installs ArgoCD into the argocd namespace
kubectl apply -f bootstrap/argocd/root-app.yaml
```

Grab the initial admin password:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d; echo
```

## 4. Watch the Republic assemble itself

```bash
kubectl -n argocd get applications -w
```

Order is enforced by sync-waves (see `docs/ARCHITECTURE.md`): MetalLB →
Longhorn → MinIO → Kyverno → ministries → laws → observability → Central
Committee → chaos.

## 5. Verify

```bash
# Storage class present and default
kubectl get storageclass

# Ministries exist with quotas
kubectl get ns -l republic.io/ministry=true
kubectl get resourcequota -A

# Truth System
kubectl -n ministry-statistics get pods

# Central Committee (read-only) is deliberating
kubectl -n ai-central-committee logs deploy/governance-engine | tail
```

## 6. Access dashboards

By default no Ingress/hostname is assumed (homelabs vary). Port-forward:

```bash
# Grafana
kubectl -n ministry-statistics port-forward svc/kube-prometheus-stack-grafana 3000:80
# ArgoCD
kubectl -n argocd port-forward svc/argocd-server 8080:443
# Governance engine API
kubectl -n ai-central-committee port-forward svc/governance-engine 8000:80
```

## 7. Building the governance-engine image

The manifests reference `ghcr.io/CHANGEME/governance-engine:0.1.0`. Build and
push it (or point at a local registry):

```bash
cd republic/ai-central-committee/app
docker build -t ghcr.io/CHANGEME/governance-engine:0.1.0 .
docker push ghcr.io/CHANGEME/governance-engine:0.1.0
```

## Teardown

```bash
kubectl delete -f bootstrap/argocd/root-app.yaml   # stops enforcement
# then delete namespaces / uninstall ArgoCD as desired
```
