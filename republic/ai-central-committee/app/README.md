# Governance Engine

The Central Committee's brain. FastAPI service that turns the Truth System's
metrics into an advisory **Five-Year Plan** via a local LLM. **Suggest-only** —
its Kubernetes RBAC is read-only and there is no code path that mutates the
cluster.

## Endpoints

| Method | Path           | Purpose                                          |
| ------ | -------------- | ------------------------------------------------ |
| GET    | `/healthz`     | Liveness/readiness                               |
| GET    | `/metrics`     | Prometheus metrics for the engine itself         |
| GET    | `/plan`        | The latest Five-Year Plan (YAML + announcement)  |
| POST   | `/deliberate`  | Convene an extraordinary session now             |

## Config (env)

See `republic/ai-central-committee/base/governance-engine.yaml`
(`PROMETHEUS_URL`, `OLLAMA_URL`, `MODEL`, `DELIBERATION_INTERVAL`, `PG_*`).

## Build

```bash
docker build -t ghcr.io/CHANGEME/governance-engine:0.1.0 .
docker push ghcr.io/CHANGEME/governance-engine:0.1.0
```

## Run locally (without a cluster)

```bash
pip install -r requirements.txt
PROMETHEUS_URL=http://localhost:9090 OLLAMA_URL=http://localhost:11434 \
  PG_HOST=localhost uvicorn app:app --reload
```

The Kubernetes read step degrades gracefully (empty state) when run outside a
cluster, so you can iterate on the planning logic locally.
