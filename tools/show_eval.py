"""Compact view of `kvf calibrate` / `kvf evaluate` output.

    python tools/show_eval.py results/calibrate_rtx5060.txt [--per-shape]
"""
import re
import sys

text = open(sys.argv[1], encoding="utf-8-sig").read()
per_shape = "--per-shape" in sys.argv
parts = text.split("=== HELD-OUT shapes (not used in the fit) ===")
names = ["FIT shapes", "HELD-OUT shapes"] if len(parts) == 2 else ["shapes"]
for name, block in zip(names, parts):
    print("##", name)
    for line in block.splitlines():
        if re.match(r"^(lossless|accuracy|no accuracy)", line):
            print(" ", line)
        elif re.search(r"MAPE|Spearman|Kendall|regret mean|regret max|top-1", line):
            print("   ", line.strip())
        elif per_shape and "rows=" in line:
            print("      ", line.strip()[:170])
