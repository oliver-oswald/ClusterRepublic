#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  The People's Homelab Republic — LOCAL bring-up (single-node, Mac/colima k3s)
#
#  Idempotent: safe to re-run. Deploys the whole Republic adapted for one node
#  (local-path storage instead of Longhorn/MetalLB/MinIO-on-Longhorn, relaxed
#  quotas in the heavy namespaces, the governance engine run from source via a
#  ConfigMap). When it finishes, run ./local/expose.sh to reach the endpoints.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL="$REPO/local"
CTX="--context colima"

# ── tunables ────────────────────────────────────────────────────────────────
COLIMA_CPU="${COLIMA_CPU:-8}"
COLIMA_MEM="${COLIMA_MEM:-24}"
COLIMA_DISK="${COLIMA_DISK:-100}"
REPO_URL="${REPO_URL:-https://github.com/oliver-oswald/ClusterRepublic.git}"
REPO_REV="${REPO_REV:-claude/homelab-k8s-blueprint-8oo89o}"
MODEL="${MODEL:-llama3.2:1b}"
ARGOCD_VERSION="${ARGOCD_VERSION:-v2.13.2}"

say(){ printf "\n\033[1;33m☭ %s\033[0m\n" "$*"; }
k(){ kubectl $CTX "$@"; }

# ── 0. preflight ──────────────────────────────────────────────────────────────
for bin in colima kubectl helm; do
  command -v "$bin" >/dev/null || { echo "missing '$bin' — install it first (brew install $bin)"; exit 1; }
done

# ── 1. cluster ────────────────────────────────────────────────────────────────
say "Cluster (colima + k3s)"
if colima status >/dev/null 2>&1; then
  echo "colima already running."
else
  colima start --runtime containerd --kubernetes \
    --cpu "$COLIMA_CPU" --memory "$COLIMA_MEM" --disk "$COLIMA_DISK" --vm-type vz
fi
kubectl config use-context colima >/dev/null
k wait --for=condition=Ready node --all --timeout=180s

# ── 2. helm repos ─────────────────────────────────────────────────────────────
say "Helm repositories"
helm repo add kyverno https://kyverno.github.io/kyverno/ >/dev/null 2>&1 || true
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null 2>&1 || true
helm repo add grafana https://grafana.github.io/helm-charts >/dev/null 2>&1 || true
helm repo add chaos-mesh https://charts.chaos-mesh.org >/dev/null 2>&1 || true
helm repo update >/dev/null

# ── 3. GitOps core + policy engine ────────────────────────────────────────────
say "ArgoCD"
k create namespace argocd --dry-run=client -o yaml | k apply -f - >/dev/null
k apply -n argocd --server-side \
  -f "https://raw.githubusercontent.com/argoproj/argo-cd/${ARGOCD_VERSION}/manifests/install.yaml" >/dev/null
k -n argocd rollout status deploy/argocd-server --timeout=300s

say "Kyverno (the Law engine)"
helm upgrade --install kyverno kyverno/kyverno -n kyverno --create-namespace \
  --set admissionController.replicas=1 --set backgroundController.replicas=1 \
  --set cleanupController.replicas=1 --set reportsController.replicas=1 >/dev/null
k -n kyverno rollout status deploy/kyverno-admission-controller --timeout=180s

# ── 4. ministries (1st pass: creates namespaces; ServiceMonitors will fail
#       until the Prometheus CRDs exist — re-applied at the end) ───────────────
say "Ministries (namespaces, quotas, identities, borders)"
k apply -R -f "$REPO/republic/ministries" 2>/dev/null || true

say "Lab adaptation: relax quotas in the heavy namespaces"
for ns in ministry-statistics ministry-emergency-events; do
  k -n "$ns" delete resourcequota quota --ignore-not-found >/dev/null
  k -n "$ns" delete limitrange  defaults --ignore-not-found >/dev/null
done

# ── 5. Truth System ───────────────────────────────────────────────────────────
say "Observability: kube-prometheus-stack"
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  -n ministry-statistics -f "$LOCAL/values-kps.yaml" >/dev/null

say "Observability: Loki"
helm upgrade --install loki grafana/loki-stack \
  -n ministry-statistics -f "$LOCAL/values-loki.yaml" >/dev/null
# loki-stack ships a duplicate default Grafana datasource that crashloops Grafana.
k -n ministry-statistics delete configmap loki-loki-stack --ignore-not-found >/dev/null

say "Observability: dashboards + datasource"
k apply -f "$REPO/republic/observability/dashboards" >/dev/null

# ── 6. Central Committee (local: local-path PVCs + engine-from-source) ────────
say "Central Committee (Ollama, Postgres, Redis, governance engine)"
TMP="$(mktemp -d)"
for f in namespace rbac ollama postgres redis; do
  sed 's/longhorn/local-path/g' "$REPO/republic/ai-central-committee/base/$f.yaml" > "$TMP/$f.yaml"
done
k apply -f "$TMP" >/dev/null
k -n ai-central-committee create configmap governance-engine-src \
  --from-file=app.py="$REPO/republic/ai-central-committee/app/app.py" \
  --from-file=requirements.txt="$REPO/republic/ai-central-committee/app/requirements.txt" \
  --dry-run=client -o yaml | k apply -f - >/dev/null
k apply -f "$LOCAL/governance-engine.yaml" >/dev/null
rm -rf "$TMP"

# ── 7. Emergency Events (Chaos Mesh) ──────────────────────────────────────────
say "Chaos Mesh (Ministry of Emergency Events)"
helm upgrade --install chaos-mesh chaos-mesh/chaos-mesh -n ministry-emergency-events \
  --set chaosDaemon.runtime=containerd \
  --set chaosDaemon.socketPath=/run/containerd/containerd.sock \
  --set dashboard.create=true >/dev/null
echo -n "  waiting for chaos CRDs"
for _ in $(seq 1 30); do k get crd schedules.chaos-mesh.org >/dev/null 2>&1 && break; echo -n .; sleep 2; done; echo
k apply -f "$REPO/republic/chaos/experiments" >/dev/null

# ── 8. Laws via ArgoCD (real GitOps from GitHub) ──────────────────────────────
say "Laws via ArgoCD (synced from $REPO_REV)"
cat <<YAML | k apply -f - >/dev/null
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata: { name: republic-laws, namespace: argocd }
spec:
  project: default
  source: { repoURL: "$REPO_URL", targetRevision: "$REPO_REV", path: republic/policies/laws }
  destination: { server: https://kubernetes.default.svc, namespace: kyverno }
  syncPolicy: { automated: { prune: true, selfHeal: true }, syncOptions: [CreateNamespace=true] }
YAML

# ── 9. ministries + enterprises (2nd pass: CRDs now exist, all objects apply) ──
say "Ministries + State Enterprises (final pass)"
k apply -R -f "$REPO/republic/ministries"

# ── 10. pull the LLM so deliberation works ────────────────────────────────────
say "Pulling LLM model ($MODEL) into Ollama"
k -n ai-central-committee rollout status deploy/ollama --timeout=180s || true
k -n ai-central-committee exec deploy/ollama -- ollama pull "$MODEL" 2>&1 | tail -1 || true

say "The State is operational."
echo "Next: ./local/expose.sh   (port-forwards + control panel)"
