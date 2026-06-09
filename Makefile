# The People's Homelab Republic — operator conveniences.
# These wrap the imperative bootstrap steps. After bootstrap, ArgoCD governs all.

KUBECONFIG ?= $(HOME)/.kube/republic.yaml
export KUBECONFIG

.PHONY: help bootstrap-argocd root-app status password lint validate \
        build-engine declare-operational

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

bootstrap-argocd: ## Install ArgoCD into the cluster (one-time)
	./bootstrap/argocd/install.sh

root-app: ## Hand ArgoCD the Constitution (apply the app-of-apps)
	kubectl apply -f bootstrap/argocd/root-app.yaml

status: ## Show all ArgoCD Applications
	kubectl -n argocd get applications

password: ## Print the initial ArgoCD admin password
	@kubectl -n argocd get secret argocd-initial-admin-secret \
	  -o jsonpath='{.data.password}' | base64 -d; echo

lint: ## Validate all YAML is well-formed (needs yq or python)
	@find republic bootstrap -name '*.yaml' -print0 \
	  | xargs -0 -I{} sh -c 'python3 -c "import sys,yaml; list(yaml.safe_load_all(open(sys.argv[1])))" {} || echo "BAD: {}"'

validate: ## Client-side validate manifests against the cluster API
	@find republic -name '*.yaml' -print0 \
	  | xargs -0 -I{} kubectl apply --dry-run=client -f {} >/dev/null && echo "manifests OK"

build-engine: ## Build & push the governance-engine image (set IMG=...)
	docker build -t $(IMG) republic/ai-central-committee/app
	docker push $(IMG)

declare-operational: ## Convene the Central Committee and print the first Plan
	kubectl -n ai-central-committee exec deploy/governance-engine -- \
	  sh -c 'wget -qO- --post-data="" http://localhost:8000/deliberate' || true
