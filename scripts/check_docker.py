"""Capture CP2 container responses and exact local image sizes."""
import json
from pathlib import Path
import subprocess
import time

from check_examples import EVIDENCE, request


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def wait(port):
    for _ in range(100):
        try:
            return request("/", port=port)
        except OSError:
            time.sleep(0.5)
    raise RuntimeError("Container startup timed out")


if __name__ == "__main__":
    sizes = {name: int(run("docker", "image", "inspect", "--format", "{{.Size}}", f"my-agent:{name}"))
             for name in ("develop", "advanced")}
    image_rows = [json.loads(line) for line in run("docker", "images", "my-agent", "--format", "json").splitlines()]
    result = {"inspect_size_bytes": sizes, "inspect_size_MiB": {k: v / 1024**2 for k, v in sizes.items()},
              "inspect_reduction_percent": (1 - sizes["advanced"] / sizes["develop"]) * 100,
              "docker_images_rows": image_rows,
              "docker_images": run("docker", "images", "my-agent", "--no-trunc")}
    run("docker", "run", "-d", "--name", "k5-day14-cp2-develop", "-p", "127.0.0.1:8000:8000", "my-agent:develop")
    try:
        wait(8000)
        result["develop_response"] = request("/ask?question=What%20is%20Docker", {})
        assert result["develop_response"]["status"] == 200
    finally:
        run("docker", "rm", "-f", "k5-day14-cp2-develop")
    wait(8082)
    result["nginx_health"] = request("/health", port=8082)
    result["nginx_ask"] = request("/ask", {"question": "Explain microservices"}, port=8082)
    assert result["nginx_health"]["status"] == result["nginx_ask"]["status"] == 200
    (EVIDENCE / "cp2.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
