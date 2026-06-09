#!/usr/bin/env bash
# Installs ArgoCD into the cluster. Run once, by a human, against an empty
# cluster that already has a CNI and storage-capable nodes.
#
# After this completes, apply bootstrap/argocd/root-app.yaml to hand ArgoCD
# the Constitution (this repo).
set -euo pipefail

ARGOCD_VERSION="${ARGOCD_VERSION:-v2.13.2}"   # pin for reproducibility
NS=argocd

echo "==> Creating namespace ${NS}"
kubectl create namespace "${NS}" --dry-run=client -o yaml | kubectl apply -f -

echo "==> Installing ArgoCD ${ARGOCD_VERSION}"
kubectl apply -n "${NS}" \
  -f "https://raw.githubusercontent.com/argoproj/argo-cd/${ARGOCD_VERSION}/manifests/install.yaml"

echo "==> Waiting for ArgoCD server to become available"
kubectl -n "${NS}" rollout status deploy/argocd-server --timeout=300s

cat <<'EOF'

==> ArgoCD is up.

Initial admin password:
  kubectl -n argocd get secret argocd-initial-admin-secret \
    -o jsonpath='{.data.password}' | base64 -d; echo

Now hand ArgoCD the Constitution:
  kubectl apply -f bootstrap/argocd/root-app.yaml

EOF
