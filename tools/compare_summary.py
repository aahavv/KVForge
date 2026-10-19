"""Summarise the library comparison: KVForge kernels against FlashInfer and PyTorch SDPA.

    python tools/compare_summary.py results/compare_rtx5060-laptop.csv

All methods ran in one WSL process on the same GPU, K and V, timer and cache flush
(bench/wsl/compare.py). Everything is fp16 and lossless: the libraries are
compared on what they all support. Writes results/figs/compare_library.png and
results/figs/compare_summary.json.
"""
import collections
import csv
import json
import math
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

TEAL, AMBER, INDIGO, ROSE, SLATE = "#0F766E", "#F59E0B", "#4F46E5", "#BE123C", "#475569"

rows = list(csv.DictReader(open(sys.argv[1])))
by = collections.defaultdict(dict)
for r in rows:
    by[r["shape"]][r["method"]] = float(r["t_us"])


def best(d, prefix):
    v = [t for m, t in d.items() if m.startswith(prefix)]
    return min(v) if v else None


def short(k):
    p = k.split("_")
    n = int(p[3][1:])
    return "H%s/%s\nd%s\nn%s\nb%s" % (p[0][1:], p[1][3:], p[2][1:], ("%dk" % (n // 1024)) if n % 1024 == 0 else n, p[4][1:])


def gmean(x):
    return math.exp(sum(map(math.log, x)) / len(x))


shapes = sorted(by)
out = {"per_shape": {}, "geomean_vs_flashinfer": {}}
series = {"kvforge_pick": [], "kvforge_oracle": [], "sdpa": [], "kvforge_baseline": []}
for sh in shapes:
    d = by[sh]
    fi = best(d, "flashinfer")
    vals = {"kvforge_pick": d["kvforge_pick"], "kvforge_oracle": d["kvforge_oracle"],
            "sdpa": best(d, "sdpa"), "kvforge_baseline": d["kvforge_baseline"]}
    out["per_shape"][sh] = {"flashinfer_us": fi, **{k + "_us": v for k, v in vals.items()}}
    for k, v in vals.items():
        series[k].append(v / fi)
for k, v in series.items():
    out["geomean_vs_flashinfer"][k] = {"geomean": gmean(v), "min": min(v), "max": max(v)}
json.dump(out, open("results/figs/compare_summary.json", "w"), indent=2)

fig, ax = plt.subplots(figsize=(10, 4.8))
w = 0.2
x = range(len(shapes))
labels = [("kvforge_pick", "KVForge: compiler's pick", TEAL), ("kvforge_oracle", "KVForge: best contiguous plan", INDIGO),
          ("sdpa", "PyTorch SDPA (best backend)", AMBER), ("kvforge_baseline", "naive baseline", ROSE)]
for i, (k, name, c) in enumerate(labels):
    vals = [min(v, 4.0) for v in series[k]]
    ax.bar([xx + (i - 1.5) * w for xx in x], vals, w, color=c, label=name)
    if k == "kvforge_baseline":
        for xx, v in zip(x, series[k]):
            if v > 4.0:
                ax.text(xx + (i - 1.5) * w, 4.02, "%.1fx" % v, ha="center", fontsize=7, color=ROSE)
ax.axhline(1.0, color="black", linewidth=1)
ax.text(len(shapes) - 0.45, 1.03, "FlashInfer = 1.0", ha="right", fontsize=8)
ax.set_xticks(list(x))
ax.set_xticklabels([short(s) for s in shapes], fontsize=8)
ax.set_ylim(0, 4.3)
ax.set_ylabel("time relative to FlashInfer (lower is better)")
ax.set_title("fp16 decode attention on the RTX 5060 Laptop: time relative to FlashInfer", loc="left", fontsize=11, fontweight="bold")
ax.grid(axis="y", color="#E2E8F0")
ax.set_axisbelow(True)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper left")
fig.tight_layout()
fig.savefig("results/figs/compare_library.png", dpi=160)

print("%-26s %9s %9s %9s %9s | %7s" % ("shape", "flashinf", "kvf_pick", "kvf_orcl", "sdpa", "pick/FI"))
for sh in shapes:
    p = out["per_shape"][sh]
    print("%-26s %9.1f %9.1f %9.1f %9.1f | %6.2fx" % (sh, p["flashinfer_us"], p["kvforge_pick_us"], p["kvforge_oracle_us"], p["sdpa_us"], p["kvforge_pick_us"] / p["flashinfer_us"]))
for k, v in out["geomean_vs_flashinfer"].items():
    print("geomean %-18s %.2fx FlashInfer's time (min %.2f, max %.2f)" % (k, v["geomean"], v["min"], v["max"]))
