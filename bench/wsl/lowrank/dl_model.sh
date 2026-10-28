#!/usr/bin/env bash
# Download a model into the Hugging Face cache (no GPU use).
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
"$HOME/kvbench/bin/python" -c "import sys; from huggingface_hub import snapshot_download; print(snapshot_download(sys.argv[1], allow_patterns=['*.json','*.safetensors','*.model','*.txt']))" "$1"
