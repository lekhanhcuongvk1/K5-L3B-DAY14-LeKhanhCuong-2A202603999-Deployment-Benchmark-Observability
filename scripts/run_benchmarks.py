"""Run CP7 using the supplied CLI tools; retain raw reports and exit codes."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request

from check_examples import ROOT, EVIDENCE

DEVELOP = ROOT / "06-lab-complete/benchmark-observability/develop"


@contextmanager
def agent(version, port, **faults):
    env = {**os.environ, "AGENT_VERSION": version, "PORT": str(port),
           "MOCK_SLOW_RATE": "0.03", "MOCK_ERROR_RATE": "0.01", **faults}
    with tempfile.TemporaryFile() as log:
        proc = subprocess.Popen([sys.executable, "app.py"], cwd=DEVELOP, env=env,
                                stdout=log, stderr=log)
        try:
            for _ in range(200):
                if proc.poll() is not None:
                    raise RuntimeError("Agent exited before readiness")
                try:
                    with urllib.request.urlopen(f"http://localhost:{port}/health", timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Agent startup timed out")
            yield
        finally:
            if proc.poll() is None:
                proc.send_signal(signal.SIGTERM)
                proc.wait(15)


def cli(*args, expected=None):
    started = datetime.now(timezone.utc).isoformat()
    result = subprocess.run([sys.executable, *args], cwd=DEVELOP,
                            capture_output=True, text=True)
    with (EVIDENCE / "cp7-cli.txt").open("a", encoding="utf-8") as log:
        log.write(f"\n$ python {' '.join(args)}\n{result.stdout}{result.stderr}\nexit_code={result.returncode}\n")
    path = EVIDENCE / "cp7-commands.json"
    records = json.loads(path.read_text()) if path.exists() else []
    records.append({"started_at_utc": started, "command": ["python", *args], "exit_code": result.returncode})
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    if "--out" in args:
        filename = args[args.index("--out") + 1]
        shutil.copy2(DEVELOP / filename, ROOT / filename)
        report = json.loads((DEVELOP / filename).read_text())
        print(json.dumps({"file": filename, "exit_code": result.returncode,
                          **{k: report[k] for k in ("accuracy", "passed", "quality_gate", "rps", "latency_ms", "error_rate", "slo") if k in report}},
                         ensure_ascii=False), flush=True)
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr)
    if expected is not None and result.returncode != expected:
        raise RuntimeError(f"Unexpected exit code {result.returncode}: {args}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["baseline", "fixed", "ci"])
    args = parser.parse_args()
    (ROOT / "reports").mkdir(exist_ok=True)
    if args.phase == "baseline":
        with agent("v1", 8001, MOCK_ERROR_RATE="0"), agent("v2", 8002, MOCK_ERROR_RATE="0"):
            cli("eval/run_eval.py", "--url", "http://localhost:8001", "--out", "reports/eval_v1.json", expected=1)
            cli("eval/run_eval.py", "--url", "http://localhost:8002", "--out", "reports/eval_v2.json", "--baseline", "reports/eval_v1.json", expected=0)
            cli("eval/run_eval.py", "--url", "http://localhost:8001", "--baseline", "reports/eval_v2.json", "--out", "reports/eval_v1_regression.json", expected=1)
        with agent("v2", 8002):
            for concurrency in (1, 10, 50, 100):
                cli("load_test.py", "--url", "http://localhost:8002", "--requests", "300", "--concurrency", str(concurrency),
                    "--out", f"reports/load_v2_c{concurrency}.json")
        for slow_rate in ("0", "0.03", "0.1"):
            with agent("v2", 8002, MOCK_SLOW_RATE=slow_rate):
                cli("load_test.py", "--url", "http://localhost:8002", "--requests", "300", "--concurrency", "20",
                    "--out", f"reports/load_v2_slow_{slow_rate}.json")
    elif args.phase == "fixed":
        with agent("v2", 8002, MOCK_ERROR_RATE="0"):
            cli("eval/run_eval.py", "--url", "http://localhost:8002", "--min-accuracy", "1.0",
                "--baseline", "reports/eval_v2.json", "--out", "reports/eval_v2_fixed.json", expected=0)
    else:
        with agent("v2", 8002, MOCK_ERROR_RATE="0", MOCK_SLOW_RATE="0"):
            cli("eval/run_eval.py", "--url", "http://localhost:8002", "--min-accuracy", "1.0",
                "--baseline", "../../../reports/eval_v2_fixed.json", "--out", "reports/eval_ci.json", expected=0)


if __name__ == "__main__":
    main()
