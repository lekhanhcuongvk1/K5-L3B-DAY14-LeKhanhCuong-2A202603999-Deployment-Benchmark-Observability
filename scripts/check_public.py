"""Verify the four K5 cloud endpoints without persisting the API key."""
import json
import argparse
import os
from datetime import datetime, timezone
from pathlib import Path
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-only", action="store_true", help="Run the three checks that do not need a key")
    parser.add_argument("--env-file", type=Path, help="Read private BASE and AGENT_API_KEY from a local ignored file")
    args = parser.parse_args()
    env = dict(os.environ)
    if args.env_file:
        from dotenv import dotenv_values
        env.update({k: v for k, v in dotenv_values(args.env_file).items() if v is not None})
    base = env.get("BASE", "").rstrip("/")
    key = env.get("AGENT_API_KEY", "")
    if not base.startswith("https://") or (not args.public_only and not key):
        raise SystemExit("Set BASE=https://<deployed-host> and AGENT_API_KEY, or use --public-only")
    results = []
    for method, path, authenticated, expected in (
        ("GET", "/health", False, 200), ("GET", "/ready", False, 200),
        ("POST", "/ask", False, 401), ("POST", "/ask", True, 200),
    ):
        if authenticated and args.public_only:
            continue
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
            if key and key in body:
                raise RuntimeError("Response unexpectedly contained credentials; refusing to save")
            results.append({"method": method, "path": path, "authenticated": authenticated,
                            "expected": expected, "status": response.code, "body": body})
    report = {"base_url": base, "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "checks": results, "complete": not args.public_only,
              "passed": not args.public_only and all(row["status"] == row["expected"] for row in results)}
    name = "cp6-public-partial.json" if args.public_only else "cp6-public.json"
    evidence = Path(__file__).resolve().parents[1] / "evidence" / name
    evidence.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for row in results:
        print(f"{row['method']} {row['path']} auth={row['authenticated']}: {row['status']}")
    raise SystemExit(0 if all(row["status"] == row["expected"] for row in results) else 1)


if __name__ == "__main__":
    main()
