#!/usr/bin/env bash
# Run a Python script in the private WSL environment, logging to a file.
#   wsl -d Ubuntu -- bash /mnt/c/Users/aahav/KVForge/bench/wsl/run.sh script.py logfile [args...]
set -uo pipefail
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
script="$1"; log="$2"; shift 2
"$HOME/kvbench/bin/python" "$script" "$@" > "$log" 2>&1
echo "exit=$?" >> "$log"
