"""Verify the four K5 cloud endpoints without persisting the API key."""
import json
import os
from pathlib import Path
import urllib.error
import urllib.request


def main():
    base = os.environ["BASE"].rstrip("/")
    key = os.environ["AGENT_API_KEY"]
    if not base.startswith("https://") or not key:
        raise SystemExit("Set BASE=https://<deployed-host> and a nonempty AGENT_API_KEY")
    results = []
    for method, path, authenticated, expected in (
        ("GET", "/health", False, 200), ("GET", "/ready", False, 200),
        ("POST", "/ask", False, 401), ("POST", "/ask", True, 200),
    ):
        headers = {"Content-Type": "application/json"}
        if authenticated:
            headers["X-API-Key"] = key
        req = urllib.request.Request(base + path, method=method, headers=headers,
                                     data=b'{"question":"Hello"}' if method == "POST" else None)
        try:
            response = urllib.request.urlopen(req, timeout=120)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            body = response.read().decode("utf-8", "replace")
            if key in body:
                raise RuntimeError("Response unexpectedly contained credentials; refusing to save")
            results.append({"method": method, "path": path, "authenticated": authenticated,
                            "expected": expected, "status": response.code, "body": body})
    report = {"base_url": base, "checks": results,
              "passed": all(row["status"] == row["expected"] for row in results)}
    evidence = Path(__file__).resolve().parents[1] / "evidence" / "cp6-public.json"
    evidence.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for row in results:
        print(f"{row['method']} {row['path']} auth={row['authenticated']}: {row['status']}")
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
