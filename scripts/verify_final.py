"""Save the unmodified grader output and probe concurrency / invalid input."""
import concurrent.futures
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import tempfile
import time

from check_examples import EVIDENCE, ROOT, request


def main():
    graded = subprocess.run([sys.executable, "check_production_ready.py"],
                            cwd=ROOT / "06-lab-complete", capture_output=True, text=True)
    (EVIDENCE / "cp5-production-ready.txt").write_text(graded.stdout + graded.stderr, encoding="utf-8")
    print(graded.stdout, flush=True)
    graded.check_returncode()
    name = "k5-day14-extra-redis"
    subprocess.run(["docker", "run", "--rm", "-d", "--name", name, "-p", "127.0.0.1:16389:6379", "redis:7-alpine"], check=True, capture_output=True)
    key = secrets.token_urlsafe(32)
    headers = {"X-API-Key": key}
    env = {**os.environ, "AGENT_API_KEY": key, "REDIS_URL": "redis://127.0.0.1:16389/0",
           "RATE_LIMIT_PER_MINUTE": "10", "DAILY_BUDGET_USD": "1", "MONTHLY_BUDGET_USD": "10"}
    proc = None
    try:
        with tempfile.TemporaryFile() as log:
            proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--workers", "2", "--port", "8016"],
                                    cwd=ROOT / "06-lab-complete", env=env, stdout=log, stderr=log)
            for _ in range(150):
                try:
                    if request("/ready", port=8016)["status"] == 200:
                        break
                except OSError:
                    pass
                time.sleep(0.1)
            invalid = [request("/ask", body, headers, port=8016)["status"] for body in
                       ({}, {"question": ""}, {"question": "   "}, {"question": "x" * 2001}, {"question": 42})]
            unauthorized = [request("/ask", {"question": "hello"}, h, port=8016)["status"]
                            for h in ({}, {"X-API-Key": "incorrect"})]
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
                futures = [pool.submit(request, "/ask", {"question": "Docker"}, headers, 8016) for _ in range(20)]
                codes = [future.result()["status"] for future in futures]
            subprocess.run(["docker", "stop", name], check=True, capture_output=True)
            down = {path: request(path, headers=headers, port=8016)["status"] for path in ("/health", "/ready")}
            blocked = request("/ask", {"question": "Hello"}, headers, port=8016)["status"]
            assert invalid == [422] * 5, invalid
            assert unauthorized == [401, 401], unauthorized
            assert codes.count(200) == codes.count(429) == 10, codes
            assert down == {"/health": 200, "/ready": 503} and blocked == 503
            result = {"invalid_input_statuses": invalid, "unauthorized_statuses": unauthorized,
                      "concurrent_20_requests_2_workers": {"200": codes.count(200), "429": codes.count(429)},
                      "redis_down": down, "ask_when_redis_down": blocked}
            (EVIDENCE / "cp5-extra.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps(result, indent=2))
    finally:
        if proc is not None and proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            proc.wait(20)
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)


if __name__ == "__main__":
    main()
