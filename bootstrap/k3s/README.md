# Cluster Bootstrap (k3s)

k3s is the default for the Republic (simpler). Talos is a fine alternative if
you want a more "state-planned", immutable OS vibe — the rest of the repo is
distribution-agnostic.

## Control plane

We disable k3s's bundled servicelb (Klipper) because **MetalLB** is the
Republic's LoadBalancer, and optionally Traefik if you prefer another ingress.

```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server \
  --disable servicelb \
  --disable traefik \
  --flannel-backend=vxlan \
  --write-kubeconfig-mode 644" sh -

# Token for joining workers:
sudo cat /var/lib/rancher/k3s/server/node-token
```

> **Richer NetworkPolicy (optional but recommended):** k3s ships flannel, which
> does not enforce NetworkPolicy. For the ministry borders to be *enforced*
> (Article 6 of the Constitution), install with `--flannel-backend=none
> --disable-network-policy` and then deploy **Cilium** or **Calico** as the CNI
> before applying the root app. The ministry NetworkPolicies in this repo are
> standard `networking.k8s.io/v1` objects and work with any policy-capable CNI.

## Workers

```bash
curl -sfL https://get.k3s.io | K3S_URL=https://<control-plane-ip>:6443 \
  K3S_TOKEN=<node-token> sh -
```

## Kubeconfig

```bash
scp <control-plane>:/etc/rancher/k3s/k3s.yaml ~/.kube/republic.yaml
sed -i 's/127.0.0.1/<control-plane-ip>/' ~/.kube/republic.yaml
export KUBECONFIG=~/.kube/republic.yaml
kubectl get nodes -o wide
```

Proceed to `bootstrap/argocd/`.
