#!/usr/bin/env bash
# Install FlashInfer into the private WSL environment (user level, no sudo).
# The pre-built kernel package (flashinfer-jit-cache) means no CUDA compiler is
# needed inside WSL for the kernels it ships.
#
#   wsl -d Ubuntu -- bash /mnt/c/Users/aahav/KVForge/bench/wsl/install_flashinfer.sh
set -euo pipefail
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
PY="$HOME/kvbench/bin/python"

CUDA_TAG=$("$PY" -c "import torch; print('cu' + torch.version.cuda.replace('.', ''))")
echo "torch built for $CUDA_TAG"

uv pip install --python "$PY" ninja numpy
uv pip install --python "$PY" flashinfer-python
# Pre-built kernels for this CUDA version (index hosted by the FlashInfer project).
uv pip install --python "$PY" flashinfer-jit-cache --extra-index-url "https://flashinfer.ai/whl/$CUDA_TAG" || \
  echo "WARNING: no pre-built kernel package for $CUDA_TAG; FlashInfer will need a CUDA compiler (JIT)"

"$PY" -m pip --version >/dev/null 2>&1 || true
uv pip list --python "$PY" 2>/dev/null | grep -i -E "flashinfer|torch|cuda" || true
