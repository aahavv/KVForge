#!/usr/bin/env bash
# Install only the pre-built FlashInfer kernels for this GPU (sm120f), and list
# what is installed.
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
PY="$HOME/kvbench/bin/python"
SP="$HOME/kvbench/lib/python3.12/site-packages"
echo "installed jit packages:"; ls "$SP" | grep -i jit_cache
echo "providers dir:"; ls "$SP/flashinfer_jit_cache/providers" 2>&1 | head
uv pip install --python "$PY" "flashinfer-jit-cache-sm120f==0.7.1+cu130" --no-deps --extra-index-url https://flashinfer.ai/whl/cu130 2>&1 | tail -6
echo "---- after:"
ls "$SP" | grep -i jit_cache
ls "$SP/flashinfer_jit_cache/providers" 2>&1 | head
du -sh "$SP/flashinfer_jit_cache" 2>/dev/null
