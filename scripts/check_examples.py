"""Run the lab examples and save real HTTP evidence without credentials."""
import concurrent.futures
import contextlib
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"
EVIDENCE.mkdir(exist_ok=True)


def request(path, body=None, headers=None, port=8000):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        response = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        return {"status": response.code, "headers": dict(response.headers),
                "body": json.loads(response.read())}


@contextlib.contextmanager
def server(directory, extra_env=None):
    with tempfile.TemporaryFile() as logs:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=ROOT / directory, env={**os.environ, **(extra_env or {})},
            stdout=logs, stderr=logs, start_new_session=True,
        )
        try:
            for _ in range(100):
                if proc.poll() is not None:
                    raise RuntimeError(f"Server failed: {directory}")
                try:
                    request("/openapi.json")
                    break
                except OSError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Server startup timed out")
            yield proc
        finally:
            if proc.poll() is None:
                proc.send_signal(signal.SIGTERM)
                try:
                    proc.wait(35)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()


def cp1():
    with server("01-localhost-vs-production/develop"):
        develop = request("/ask?question=Hello", {})
        wrong = request("/ask", {"question": "Hello"})
    with server("01-localhost-vs-production/production"):
        production = request("/ask", {"question": "Hello"})
        health = request("/health")
        ready = request("/ready")
    assert [develop["status"], wrong["status"], production["status"], health["status"], ready["status"]] == [200, 422, 200, 200, 200]
    return dict(develop_query=develop, develop_json=wrong, production=production, health=health, ready=ready)


def curl_capture(path, body, headers=None):
    args = ["curl", "-sS", "-i", "-X", "POST", f"http://127.0.0.1:8000{path}",
            "-H", "Content-Type: application/json", "-d", json.dumps(body)]
    for name, value in (headers or {}).items():
        args.extend(["-H", f"{name}: {value}"])
    result = subprocess.run(args, capture_output=True, text=True, check=True)
    return result.stdout


def cp3():
    key = secrets.token_urlsafe(24)
    body = {"question": "Hello"}
    with server("04-api-gateway/develop", {"AGENT_API_KEY": key}):
        missing = curl_capture("/ask", body)
        accepted = curl_capture("/ask", body, {"X-API-Key": key})
    with server("04-api-gateway/production", {"JWT_SECRET": secrets.token_urlsafe(48)}):
        login = request("/auth/token", {"username": "student", "password": "demo123"})
        token = login["body"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        statuses = [request("/ask", body, headers)["status"] for _ in range(11)]
        limited = curl_capture("/ask", body, headers)
    assert statuses == [200] * 10 + [429], statuses
    text = "## Missing API key\n" + missing + "\n## Accepted API key\n" + accepted + "\n## JWT rate limited\n" + limited
    assert key not in text and token not in text
    (EVIDENCE / "cp3-http.txt").write_text(text, encoding="utf-8")
    return {"jwt_login_status": login["status"], "statuses": statuses,
            "raw_http": "evidence/cp3-http.txt", "credentials": "redacted / not persisted"}


def cp4():
    with server("05-scaling-reliability/develop") as proc:
        health, ready = request("/health"), request("/ready")
        with concurrent.futures.ThreadPoolExecutor() as pool:
            pending = pool.submit(request, "/ask?question=Long%20task", {})
            time.sleep(0.05)
            proc.send_signal(signal.SIGTERM)
            response = pending.result()
            code = proc.wait(35)
    assert response["status"] == 200
    return dict(health=health, ready=ready, in_flight=response, process_exit=code)


if __name__ == "__main__":
    checkpoint = sys.argv[1]
    result = {"checkpoint": checkpoint, "python": sys.version, "os": os.name,
              "result": {"cp1": cp1, "cp3": cp3, "cp4": cp4}[checkpoint]()}
    (EVIDENCE / f"{checkpoint}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
