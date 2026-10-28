"""Per-shape summary of results/lowrank/bench_tc_rtx5060-laptop.csv: KVForge's
compressed-cache kernels against FlashInfer's best fp16 and best fp8 kernel.

    python tools/lowrank_summary.py [csv]
"""
import collections
import csv
import math
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "results/lowrank/bench_tc_rtx5060-laptop.csv"
rows = collections.defaultdict(dict)
for r in csv.DictReader(open(path)):
    rows[r["shape"]][r["method"]] = float(r["t_us"])

# perplexity cost on Qwen3-1.7B / TinyLlama-1.1B, from results/lowrank/study_*.json
OURS = {
    "kvforge_tc_rot_k8g128v4g64": "rot K int8:128 + V int4:64 (PPL +0.0% / +0.13%)",
    "kvforge_tc_k8v4": "K int8:32 + V int4:32 (PPL +0.2% / +0.14%)",
}
print("%-26s %8s %8s | %-28s %8s %7s %7s" % ("shape", "FI f16", "FI fp8", "KVForge", "us", "vs fp8", "vs f16"))
geo = collections.defaultdict(list)
for shape in sorted(rows):
    m = rows[shape]
    f16 = min(v for k, v in m.items() if k.startswith("flashinfer_batch"))
    f8 = min(v for k, v in m.items() if k.startswith("flashinfer_fp8"))
    for name in OURS:
        if name not in m:
            continue
        t = m[name]
        geo[name].append((f8 / t, f16 / t))
        print("%-26s %8.1f %8.1f | %-28s %8.1f %6.2fx %6.2fx" % (shape, f16, f8, name.replace("kvforge_tc_", ""), t, f8 / t, f16 / t))
    ours16 = min(v for k, v in m.items() if k in ("kvforge_f16", "kvforge_f16_pick"))
    geo["fp16 (new kernel or pick) vs FI fp16"].append((f16 / ours16, f16 / ours16))
print()
for name, xs in geo.items():
    g8 = math.exp(sum(math.log(a) for a, _ in xs) / len(xs))
    g16 = math.exp(sum(math.log(b) for _, b in xs) / len(xs))
    lo = min(a for a, _ in xs)
    hi = max(a for a, _ in xs)
    if name in OURS:
        print("%-42s speedup vs FI fp8: geomean %.2fx (range %.2f..%.2f); vs FI fp16: geomean %.2fx" % (OURS[name], g8, lo, hi, g16))
    else:
        print("%-42s speedup: geomean %.2fx (range %.2f..%.2f)" % (name, g16, lo, hi))
