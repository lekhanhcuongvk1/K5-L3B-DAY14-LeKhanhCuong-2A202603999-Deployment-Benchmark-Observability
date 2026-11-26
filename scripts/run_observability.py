"""Run CP8 against the real Compose stack and retain measurements."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PROD = ROOT / "06-lab-complete/benchmark-observability/production"
EVIDENCE = ROOT / "evidence"
COMPOSE = ["docker", "compose", "-p", "k5-day14-observability", "-f", str(PROD / "docker-compose.yml")]


def save(name, value):
    (EVIDENCE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def http(url):
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}: {url}") from None


def query(expression):
    return http("http://localhost:9090/api/v1/query?" + urllib.parse.urlencode({"query": expression}))


def compose(*args, name=None, faults=None, allowed=(0,)):
    started = datetime.now(timezone.utc).isoformat()
    result = subprocess.run([*COMPOSE, *args], cwd=PROD, env={**os.environ, **(faults or {})},
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    if name:
        (EVIDENCE / f"{name}.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
    print(json.dumps({"command": list(args), "exit_code": result.returncode, "started_at_utc": started}), flush=True)
    if result.returncode not in allowed:
        raise RuntimeError(result.stderr[-3000:])
    return result


def wait_targets(count):
    for _ in range(90):
        targets = http("http://localhost:9090/api/v1/targets")["data"]["activeTargets"]
        agents = [target for target in targets if target["labels"].get("job") == "agent"]
        if len(agents) == count and all(target["health"] == "up" for target in agents):
            save(f"cp8-targets-{count}.json", agents)
            return
        time.sleep(2)
    raise RuntimeError(f"Expected {count} healthy scrape targets")


def snapshot(label):
    queries = {
        "p95_seconds": 'histogram_quantile(0.95,sum by(le)(rate(http_request_duration_seconds_bucket{job="agent",route="/ask"}[1m])))',
        "avg_seconds": 'sum(rate(http_request_duration_seconds_sum{job="agent",route="/ask"}[1m])) / sum(rate(http_request_duration_seconds_count{job="agent",route="/ask"}[1m]))',
        "rps_by_instance": 'sum by(instance)(rate(http_requests_total{job="agent",route="/ask"}[1m]))',
        "rps_by_status": 'sum by(status)(rate(http_requests_total{job="agent",route="/ask"}[1m]))',
        "tokens_by_type": 'sum by(type)(rate(llm_tokens_total{job="agent"}[1m]))',
        "cost_per_hour": 'sum(rate(llm_cost_usd_total{job="agent"}[5m]))*3600',
    }
    save(f"cp8-metrics-{label}.json", {"at_utc": datetime.now(timezone.utc).isoformat(),
                                     "queries": {name: {"expression": expression, "response": query(expression)} for name, expression in queries.items()}})


def locust(name, users=100, duration="2m"):
    return compose("run", "--rm", "--no-deps", "locust", "-f", "/mnt/locust/locustfile.py", "--host", "http://nginx",
                   "--headless", "-u", str(users), "-r", "10", "-t", duration,
                   "--csv", f"/mnt/results/{name}", name=f"cp8-locust-{name}", allowed=(0, 1))


def baseline():
    wait_targets(1)
    result = subprocess.run(["docker", "run", "--rm", "--mount", f"type=bind,source={PROD / 'prometheus'},target=/p,readonly",
                             "--entrypoint", "promtool", "prom/prometheus:v3.16.0", "test", "rules", "/p/alert_rules_test.yml"],
                            capture_output=True, text=True)
    (EVIDENCE / "cp8-alert-rule-tests.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
    result.check_returncode()
    print("promtool alert rule tests passed", flush=True)
    locust("scale_1")
    snapshot("scale1")
    compose("up", "-d", "--scale", "agent=3", name="cp8-scale3-up")
    wait_targets(3)
    # Allow Nginx's DNS resolver to observe the additional instances as well.
    time.sleep(12)
    locust("scale_3")
    snapshot("scale3")
    export_results()
    traces()


def export_results():
    target = ROOT / "benchmark-results"
    target.mkdir(exist_ok=True)
    for path in (PROD / "benchmark-results").glob("*.csv"):
        shutil.copy2(path, target / path.name)


def traces():
    now = datetime.now(timezone.utc)
    params = {"query.service_name": "observable-agent", "query.search_depth": 200,
              "query.start_time_min": (now - timedelta(hours=1)).isoformat(),
              "query.start_time_max": now.isoformat()}
    data = http("http://localhost:16686/api/v3/traces?" + urllib.parse.urlencode(params))
    grouped = {}
    for resource in data.get("result", {}).get("resourceSpans", []):
        for scope in resource.get("scopeSpans", []):
            for span in scope.get("spans", []):
                trace = grouped.setdefault(span["traceId"], {"traceID": span["traceId"], "spans": []})
                trace["spans"].append({"operationName": span["name"],
                                       "startTime": int(span["startTimeUnixNano"]) / 1000,
                                       "duration": (int(span["endTimeUnixNano"]) - int(span["startTimeUnixNano"])) / 1000,
                                       "otlp": span, "resource": resource["resource"]})
    all_traces = list(grouped.values())
    if not all_traces:
        raise RuntimeError("Jaeger has no traces")
    duration = lambda trace: max(span["startTime"] + span["duration"] for span in trace["spans"]) - min(span["startTime"] for span in trace["spans"])
    slow = max(all_traces, key=duration)
    errors = [trace for trace in all_traces if any(
        span["otlp"].get("status", {}).get("code") in (2, "STATUS_CODE_ERROR")
        for span in trace["spans"])]
    if not errors:
        raise RuntimeError("Jaeger sample contains no error trace")
    error = errors[0]
    save("cp8-slow-trace.json", slow)
    save("cp8-error-trace.json", error)
    logs = compose("logs", "--no-color", "--no-log-prefix", "agent").stdout
    records = []
    for line in logs.splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("trace_id") in (slow["traceID"], error["traceID"]):
            records.append(row)
    save("cp8-correlated-logs.json", records)
    assert any(row.get("trace_id") == slow["traceID"] for row in records)
    assert any(row.get("trace_id") == error["traceID"] for row in records)
    slowest = max(slow["spans"], key=lambda span: span["duration"])
    llm = max((span for span in slow["spans"] if span["operationName"].startswith("chat ")), key=lambda span: span["duration"])
    summary = {"sample_traces": len(all_traces), "query": params,
               "slow_trace_id": slow["traceID"], "total_ms": duration(slow) / 1000,
               "longest_span": {"name": slowest["operationName"], "ms": slowest["duration"] / 1000},
               "llm_span": {"name": llm["operationName"], "ms": llm["duration"] / 1000},
               "error_trace_id": error["traceID"]}
    save("cp8-trace-summary.json", summary)
    print(json.dumps(summary), flush=True)


def chaos():
    faults = {"MOCK_ERROR_RATE": "0.2", "MOCK_SLOW_RATE": "0.03"}
    started = time.monotonic()
    changed_at = datetime.now(timezone.utc).isoformat()
    compose("up", "-d", "--scale", "agent=3", "--force-recreate", "agent", faults=faults, name="cp8-chaos-up")
    wait_targets(3)
    compose("run", "--rm", "-d", "--name", "k5-day14-chaos-load", "--no-deps", "locust", "-f",
            "/mnt/locust/locustfile.py", "--host", "http://nginx", "--headless", "-u", "30", "-r", "5",
            "-t", "8m", "--csv", "/mnt/results/chaos", name="cp8-chaos-load-start")
    firing = {}
    observations = []
    phase_b_started = None
    try:
            while time.monotonic() - started < 430:
                alerts = http("http://localhost:9090/api/v1/alerts")
                elapsed = round(time.monotonic() - started, 2)
                observations.append({"elapsed_s": elapsed, "response": alerts})
                for alert in alerts["data"]["alerts"]:
                    if alert["state"] == "firing":
                        firing.setdefault(alert["labels"]["alertname"], elapsed)
                print(json.dumps({"elapsed_s": elapsed, "firing": firing}), flush=True)
                if "AgentHighErrorRate" in firing and phase_b_started is None:
                    save("cp8-alerts-phase-a.json", alerts)
                    snapshot("error-only")
                    phase_b_started = time.monotonic()
                    faults["MOCK_SLOW_RATE"] = "0.3"
                    compose("up", "-d", "--scale", "agent=3", "--force-recreate", "agent", faults=faults, name="cp8-chaos-phase-b-up")
                    wait_targets(3)
                    continue
                needed = {"AgentHighErrorRate", "AgentHighLatencyP95"}
                if needed.issubset(firing):
                    save("cp8-alerts-firing.json", alerts)
                    snapshot("chaos")
                    save("cp8-chaos-timing.json", {"changed_at_utc": changed_at, "faults": faults,
                                                   "phase_b_started_elapsed_s": round(phase_b_started - started, 2),
                                                   "latency_firing_after_phase_b_s": round(time.monotonic() - phase_b_started, 2),
                                                   "first_firing_elapsed_s": firing, "observations": observations})
                    # Keep the load running briefly for screenshots to show ongoing traffic.
                    print("Both required alerts firing; stack and load remain live for screenshots.", flush=True)
                    save("cp8-chaos-process.json", {"container": "k5-day14-chaos-load"})
                    return
                time.sleep(5)
            raise RuntimeError("Required alerts did not both fire within observation window")
    except BaseException:
        subprocess.run(["docker", "stop", "k5-day14-chaos-load"], capture_output=True)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["baseline", "chaos", "traces", "export"])
    args = parser.parse_args()
    {"baseline": baseline, "chaos": chaos, "traces": traces, "export": export_results}[args.phase]()
