#!/usr/bin/env python3
"""
Central Committee Control Panel — host-side control server.

Serves index.html and exposes a same-origin /api so the browser never has to
deal with CORS. Read paths proxy to the (port-forwarded) governance engine and
Prometheus. Crisis paths shell out to kubectl to apply Chaos Mesh experiments —
i.e. the operator (you), not the AI, creates chaos. The in-cluster committee
stays strictly read-only.
"""
import json
import os
import subprocess
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ENGINE = "http://127.0.0.1:8000"
PROM = "http://127.0.0.1:9090"
CTX = ["--context", "colima"]
HERE = Path(__file__).parent
PORT = int(os.getenv("PANEL_PORT", "9000"))

PROM_QUERIES = {
    # node-exporter: whole-node totals (cadvisor per-container labels are empty
    # in this k3s build, so node metrics are the reliable signal of State output).
    "industrial_output_cores": 'sum(rate(node_cpu_seconds_total{mode!="idle"}[2m]))',
    "population_pressure_bytes": 'sum(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes)',
    "instability_restarts_1h": 'sum(increase(kube_pod_container_status_restarts_total[1h]))',
}

# Crisis experiments (operator-triggered). Each targets the State Cinema pods.
CRISES = {
    "purge": """
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata: {name: crisis-purge, namespace: ministry-emergency-events, labels: {republic.io/crisis: "true"}}
spec:
  action: pod-kill
  mode: one
  selector: {namespaces: [ministry-heavy-computing], labelSelectors: {app: state-cinema}}
""",
    "slowdown": """
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata: {name: crisis-slowdown, namespace: ministry-emergency-events, labels: {republic.io/crisis: "true"}}
spec:
  action: delay
  mode: all
  duration: "10m"
  selector: {namespaces: [ministry-heavy-computing], labelSelectors: {app: state-cinema}}
  delay: {latency: "300ms", jitter: "100ms", correlation: "50"}
""",
    "overwork": """
apiVersion: chaos-mesh.org/v1alpha1
kind: StressChaos
metadata: {name: crisis-overwork, namespace: ministry-emergency-events, labels: {republic.io/crisis: "true"}}
spec:
  mode: all
  duration: "10m"
  selector: {namespaces: [ministry-heavy-computing], labelSelectors: {app: state-cinema}}
  stressors: {cpu: {workers: 2, load: 80}}
""",
}
CRISIS_KINDS = "podchaos,networkchaos,stresschaos"


def http_json(url, method="GET", timeout=20):
    req = urllib.request.Request(url, data=b"" if method == "POST" else None, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def prom(expr):
    try:
        url = f"{PROM}/api/v1/query?query=" + urllib.parse.quote(expr)  # noqa
        res = http_json(url)["data"]["result"]
        return float(res[0]["value"][1]) if res else 0.0
    except Exception:
        return None


def kubectl(args, stdin=None, timeout=60):
    p = subprocess.run(["kubectl", *CTX, *args], input=stdin, capture_output=True,
                       text=True, timeout=timeout)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def active_crises():
    rc, out, _ = kubectl(["get", CRISIS_KINDS, "-A", "-l", "republic.io/crisis=true",
                          "-o", "jsonpath={range .items[*]}{.kind}/{.metadata.name} {end}"])
    return out.split() if out else []


def build_state():
    state = {"health": "unknown", "plan": None, "metrics": {}, "crises": active_crises()}
    try:
        state["health"] = http_json(f"{ENGINE}/healthz", timeout=5).get("status", "?")
    except Exception:
        state["health"] = "unreachable"
    try:
        state["plan"] = http_json(f"{ENGINE}/plan", timeout=8)
    except Exception:
        state["plan"] = None
    for key, expr in PROM_QUERIES.items():
        state["metrics"][key] = prom(expr)
    return state


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
        if self.path == "/api/state":
            return self._send(200, json.dumps(build_state()))
        return self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        if self.path == "/api/deliberate":
            try:
                d = http_json(f"{ENGINE}/deliberate", method="POST", timeout=300)
                return self._send(200, json.dumps(d))
            except Exception as e:
                return self._send(502, json.dumps({"error": str(e)}))
        if self.path.startswith("/api/crisis/"):
            name = self.path.rsplit("/", 1)[-1]
            if name == "restore":
                rc, out, err = kubectl(["delete", CRISIS_KINDS, "-n", "ministry-emergency-events",
                                        "-l", "republic.io/crisis=true", "--ignore-not-found"])
                return self._send(200, json.dumps({"ok": rc == 0, "msg": out or "Order restored.", "err": err}))
            if name in CRISES:
                # delete-then-apply so the same crisis can be re-triggered.
                kind = {"purge": "podchaos", "slowdown": "networkchaos", "overwork": "stresschaos"}[name]
                kubectl(["delete", kind, f"crisis-{name}", "-n", "ministry-emergency-events", "--ignore-not-found"])
                rc, out, err = kubectl(["apply", "-f", "-"], stdin=CRISES[name])
                return self._send(200 if rc == 0 else 502, json.dumps({"ok": rc == 0, "msg": out, "err": err}))
            return self._send(404, json.dumps({"error": "unknown crisis"}))
        return self._send(404, json.dumps({"error": "not found"}))


if __name__ == "__main__":
    print(f"Central Committee Control Panel on http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
