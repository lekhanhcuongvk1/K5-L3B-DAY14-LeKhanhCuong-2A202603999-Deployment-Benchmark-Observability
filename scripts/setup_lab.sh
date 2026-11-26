#!/usr/bin/env bash
set -euo pipefail
UV="$HOME/.venvs/bootstrap/bin/uv"
"$UV" python install 3.11
"$UV" venv --python 3.11 "$HOME/.venvs/day14"
"$UV" pip install --python "$HOME/.venvs/day14/bin/python" \
  -r 06-lab-complete/requirements.txt \
  httpx prometheus-client
"$HOME/.venvs/day14/bin/python" -c 'import os,sys; print(sys.version); print(os.name)'
