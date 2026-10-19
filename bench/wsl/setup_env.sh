#!/usr/bin/env bash
# Set up a private, user-level Python environment inside WSL2 for the FlashInfer
# and PyTorch SDPA comparison. Nothing is installed system-wide; no sudo needed.
#
#   wsl -d Ubuntu -- bash /mnt/c/Users/aahav/KVForge/bench/wsl/setup_env.sh
set -euo pipefail
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"

if ! command -v uv >/dev/null 2>&1; then
  pip3 install --user --break-system-packages uv
fi
uv --version

if [ ! -d "$HOME/kvbench" ]; then
  uv venv "$HOME/kvbench" --python 3.12
fi

# PyTorch built for CUDA 12.8, the first release with Blackwell (sm_120) kernels.
uv pip install --python "$HOME/kvbench/bin/python" torch numpy --index-url https://download.pytorch.org/whl/cu128 \
  --extra-index-url https://pypi.org/simple

"$HOME/kvbench/bin/python" - <<'EOF'
import torch
print("torch", torch.__version__, "cuda", torch.version.cuda)
print("gpu", torch.cuda.get_device_name(0), "capability", torch.cuda.get_device_capability(0))
x = torch.randn(1024, 1024, device="cuda")
print("matmul ok", float((x @ x).sum().isfinite()))
EOF
