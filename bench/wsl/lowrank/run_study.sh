#!/usr/bin/env bash
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
cd /mnt/c/Users/aahav/KVForge
"$HOME/kvbench/bin/python" bench/wsl/lowrank/study.py "$@"
