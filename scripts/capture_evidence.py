"""Capture real local service pages with Chrome's headless screenshot CLI."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CHROME = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")


def capture(name, url, height=1100):
    target = ROOT / "screenshots" / name
    with tempfile.TemporaryDirectory(prefix="day14-chrome-") as profile:
        result = subprocess.run([str(CHROME), "--headless=new", "--disable-gpu", "--no-first-run",
                                 "--hide-scrollbars", f"--user-data-dir={profile}", "--window-size=1600," + str(height),
                                 "--virtual-time-budget=15000", f"--screenshot={target}", url],
                                capture_output=True, text=True, timeout=60)
        if result.returncode or not target.exists():
            raise RuntimeError(result.stderr[-2500:])
    print(f"Captured {name}: {target.stat().st_size} bytes", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("page", choices=["grafana", "alerts", "traces", "public"])
    args = parser.parse_args()
    if args.page == "grafana":
        snapshot = json.loads((ROOT / "evidence/cp8-metrics-scale3.json").read_text(encoding="utf-8"))
        end = int(snapshot["queries"]["p95_seconds"]["response"]["data"]["result"][0]["value"][0] * 1000)
        capture("grafana-dashboard.png", f"http://localhost:3000/d/day14-agent-overview?from={end-110000}&to={end}&kiosk", 1800)
    elif args.page == "alerts":
        capture("prometheus-alert-firing.png", "http://localhost:9090/alerts", 1400)
    elif args.page == "traces":
        summary = json.loads((ROOT / "evidence/cp8-trace-summary.json").read_text(encoding="utf-8"))
        capture("jaeger-slow-trace.png", "http://localhost:16686/trace/" + summary["slow_trace_id"], 1200)
        capture("jaeger-error-trace.png", "http://localhost:16686/trace/" + summary["error_trace_id"], 1200)
    else:
        report = json.loads((ROOT / "evidence/cp6-public.json").read_text(encoding="utf-8"))
        capture("running.png", report["base_url"] + "/health", 600)
        capture("test.png", (ROOT / "evidence/cp6-public.json").as_uri(), 1500)
