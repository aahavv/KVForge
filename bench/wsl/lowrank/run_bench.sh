#!/usr/bin/env bash
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/lib/wsl/lib"
cd /mnt/c/Users/aahav/KVForge
"$HOME/kvbench/bin/python" bench/wsl/lowrank/bench_lr.py "$@"
