"""
The People's Central Committee — Governance Engine.

A *suggest-only* service. It reads the Truth System (Prometheus) and the
Kubernetes API (read-only RBAC) and asks a local LLM (Ollama) to draft an
advisory "Five-Year Plan". Plans are written to Postgres, cached in Redis, and
logged as State Announcements. Nothing here mutates the cluster — by
constitutional design (see docs/CONSTITUTION.md, Article 4).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import textwrap
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
import psycopg
import yaml
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("central-committee")

# --- Configuration (all from env / ConfigMap / Secret) ----------------------
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("MODEL", "llama3.2:1b")
DELIBERATION_INTERVAL = int(os.getenv("DELIBERATION_INTERVAL", "3600"))
PG_DSN = (
    f"host={os.getenv('PG_HOST', 'localhost')} "
    f"dbname={os.getenv('PG_DB', 'committee')} "
    f"user={os.getenv('PG_USER', 'committee')} "
    f"password={os.getenv('PG_PASSWORD', 'committee')}"
)

# Political-metric queries (PromQL). See docs/CONSTITUTION.md for the mapping.
METRIC_QUERIES = {
    "industrial_output_cores": 'sum(rate(container_cpu_usage_seconds_total{container!=""}[5m]))',
    "population_pressure_bytes": 'sum(container_memory_working_set_bytes{container!=""})',
    "political_instability_restarts_1h": 'sum(increase(kube_pod_container_status_restarts_total[1h]))',
    "famine_oomkills_1h": 'sum(increase(kube_pod_container_status_last_terminated_reason{reason="OOMKilled"}[1h]))',
    "industrial_output_by_ministry": 'sum by (namespace) (rate(container_cpu_usage_seconds_total{namespace=~"ministry-.*"}[5m]))',
}

# --- Prometheus metrics this service exposes ---------------------------------
DELIBERATIONS = Counter("committee_deliberations_total", "Five-Year Plans drafted")
DELIBERATION_FAILURES = Counter("committee_deliberation_failures_total", "Failed deliberations")
LAST_PLAN_TS = Gauge("committee_last_plan_timestamp_seconds", "Unix time of last plan")


# --- Truth System (Prometheus) ----------------------------------------------
async def query_prometheus(client: httpx.AsyncClient, expr: str):
    try:
        r = await client.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": expr}, timeout=15)
        r.raise_for_status()
        result = r.json()["data"]["result"]
        if not result:
            return None
        # Scalar-ish single value, or a per-namespace map.
        if len(result) == 1 and "namespace" not in result[0].get("metric", {}):
            return float(result[0]["value"][1])
        return {m["metric"].get("namespace", "?"): float(m["value"][1]) for m in result}
    except Exception as exc:  # the Truth System may be briefly unavailable
        log.warning("Prometheus query failed (%s): %s", expr, exc)
        return None


async def gather_metrics() -> dict:
    async with httpx.AsyncClient() as client:
        snapshot = {}
        for name, expr in METRIC_QUERIES.items():
            snapshot[name] = await query_prometheus(client, expr)
        return snapshot


# --- Kubernetes API (read-only) ----------------------------------------------
def gather_cluster_state() -> dict:
    """Read namespaces, quotas and pod health. Read-only; never mutates."""
    try:
        from kubernetes import client as k8s, config as k8s_config

        try:
            k8s_config.load_incluster_config()
        except Exception:
            k8s_config.load_kube_config()

        core = k8s.CoreV1Api()
        ministries = [
            ns.metadata.name
            for ns in core.list_namespace(label_selector="republic.io/ministry=true").items
        ]
        quotas = {}
        for q in core.list_resource_quota_for_all_namespaces().items:
            quotas.setdefault(q.metadata.namespace, {})
            if q.status and q.status.used:
                quotas[q.metadata.namespace] = {
                    "used": dict(q.status.used or {}),
                    "hard": dict(q.status.hard or {}),
                }
        return {"ministries": ministries, "quotas": quotas}
    except Exception as exc:
        log.warning("Kubernetes read failed: %s", exc)
        return {"ministries": [], "quotas": {}}


# --- Central Committee Brain (Ollama) ----------------------------------------
SYSTEM_PROMPT = textwrap.dedent(
    """
    You are the Central Planning Committee of The People's Homelab Republic.
    You are given a snapshot of the State's metrics (CPU = industrial output,
    memory = population pressure, storage = agricultural yield, pod restarts =
    political instability, OOMKills = famine).

    Draft a concise "Five-Year Plan" as STRICT YAML with this shape:

    plan:
      assessment: <one sentence on the state of the Republic>
      compute_expansion: <true|false>
      agriculture_storage_increase_pct: <integer 0-50>
      communications_bandwidth_limit_pct: <integer 0-50>
    actions:
      - namespace: <ministry namespace>
        suggestion: <short advisory action, e.g. "raise CPU quota by 1 core">
    announcement: <one dramatic state-bulletin sentence in Soviet bureaucratic style>

    These are ADVISORY SUGGESTIONS ONLY. Output YAML only, no prose, no fences.
    """
).strip()


async def ensure_model(client: httpx.AsyncClient):
    """Pull the model if Ollama doesn't have it yet."""
    try:
        tags = (await client.get(f"{OLLAMA_URL}/api/tags", timeout=10)).json()
        have = {m["name"] for m in tags.get("models", [])}
        if MODEL in have or any(n.startswith(MODEL.split(":")[0]) for n in have):
            return
        log.info("Pulling model %s (first run, may take a while)...", MODEL)
        async with client.stream("POST", f"{OLLAMA_URL}/api/pull",
                                  json={"name": MODEL}, timeout=None) as resp:
            async for _ in resp.aiter_lines():
                pass
    except Exception as exc:
        log.warning("Model ensure failed: %s", exc)


async def draft_plan(snapshot: dict) -> str:
    async with httpx.AsyncClient() as client:
        await ensure_model(client)
        prompt = f"Snapshot of the Republic:\n{json.dumps(snapshot, indent=2)}\n\nDraft the Plan."
        r = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "system": SYSTEM_PROMPT,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7},
            },
            timeout=300,
        )
        r.raise_for_status()
        return r.json().get("response", "").strip()


# --- Long-term memory (Postgres) ---------------------------------------------
def init_db():
    with psycopg.connect(PG_DSN) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS plans (
                id          SERIAL PRIMARY KEY,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
                snapshot    JSONB,
                plan_yaml   TEXT,
                announcement TEXT
            )
            """
        )
        conn.commit()


def store_plan(snapshot: dict, plan_yaml: str, announcement: str) -> int:
    with psycopg.connect(PG_DSN) as conn:
        row = conn.execute(
            "INSERT INTO plans (snapshot, plan_yaml, announcement) VALUES (%s, %s, %s) RETURNING id",
            (json.dumps(snapshot), plan_yaml, announcement),
        ).fetchone()
        conn.commit()
        return row[0]


def latest_plan() -> dict | None:
    with psycopg.connect(PG_DSN) as conn:
        row = conn.execute(
            "SELECT id, created_at, plan_yaml, announcement FROM plans ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if not row:
        return None
    return {"id": row[0], "created_at": row[1].isoformat(), "plan_yaml": row[2], "announcement": row[3]}


# --- The deliberation cycle --------------------------------------------------
async def deliberate() -> dict:
    log.info("== Convening the Central Committee ==")
    snapshot = await gather_metrics()
    snapshot["cluster"] = gather_cluster_state()

    plan_text = await draft_plan(snapshot)

    announcement = "The State deliberates."
    try:
        parsed = yaml.safe_load(plan_text)
        if isinstance(parsed, dict) and parsed.get("announcement"):
            announcement = str(parsed["announcement"])
    except Exception:
        log.warning("Plan was not valid YAML; storing raw text.")

    plan_id = store_plan(snapshot, plan_text, announcement)
    DELIBERATIONS.inc()
    LAST_PLAN_TS.set(datetime.now(timezone.utc).timestamp())
    log.info("📜 STATE ANNOUNCEMENT (Plan #%s): %s", plan_id, announcement)
    return {"id": plan_id, "announcement": announcement, "plan_yaml": plan_text}


async def deliberation_loop():
    # Give datastores a moment to come up before the first session.
    await asyncio.sleep(15)
    while True:
        try:
            await deliberate()
        except Exception as exc:
            DELIBERATION_FAILURES.inc()
            log.exception("Deliberation failed: %s", exc)
        await asyncio.sleep(DELIBERATION_INTERVAL)


# --- HTTP surface ------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
    except Exception as exc:
        log.warning("DB init deferred: %s", exc)
    task = asyncio.create_task(deliberation_loop())
    yield
    task.cancel()


app = FastAPI(title="Central Committee Governance Engine", lifespan=lifespan)


@app.get("/healthz")
def healthz():
    return {"status": "vigilant"}


@app.get("/metrics")
def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/plan")
def get_plan():
    plan = latest_plan()
    return plan or {"message": "No Five-Year Plan has yet been drafted."}


@app.post("/deliberate")
async def trigger():
    """Convene an extraordinary session immediately (still suggest-only)."""
    return await deliberate()
