#!/usr/bin/env bash
# Install FlashInfer's pre-built kernels for this PyTorch's CUDA version and show
# exactly what happens.
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
PY="$HOME/kvbench/bin/python"
TAG=$("$PY" -c "import torch; print('cu' + torch.version.cuda.replace('.', ''))")
echo "index tag: $TAG"
uv pip install --python "$PY" flashinfer-jit-cache --extra-index-url "https://flashinfer.ai/whl/$TAG" 2>&1 | tail -25
echo "---- after:"
"$PY" -c "import flashinfer_jit_cache as j, os; print('jit cache', getattr(j,'__version__','?'), os.path.dirname(j.__file__))" 2>&1 | tail -2
