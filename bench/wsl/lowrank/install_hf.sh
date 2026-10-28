#!/usr/bin/env bash
# Hugging Face libraries for the low-rank study (real model keys and values).
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
uv pip install --python "$HOME/kvbench/bin/python" transformers datasets accelerate 2>&1 | tail -5
"$HOME/kvbench/bin/python" -c 'import transformers, datasets; print("transformers", transformers.__version__, "datasets", datasets.__version__)'
