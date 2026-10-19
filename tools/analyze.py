"""Analyse a KVForge sweep: how much do the three axes matter, and how well does
the model predict?

    python tools/analyze.py --sweep results/sweep_rtx5060-laptop.csv \
        --predicted results/predicted_rtx5060-laptop.csv --out results/figs

`--predicted` is the file written by `kvf predict`. Writes figures and
`summary.json` into --out.
"""
import argparse
import collections
import csv
import json
import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

TEAL, AMBER, INDIGO, ROSE, SLATE, GREEN = "#0F766E", "#F59E0B", "#4F46E5", "#BE123C", "#475569", "#15803D"


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def shape_key(r):
    return "H%s_Hkv%s_d%s_n%s_b%s" % (r["H"], r["H_kv"], r["d"], r["n"], r["batch"])


def fmt_key(r):
    return r["fmt"] + (":" + r["group"] if r["fmt"] != "f16" else "")


def short(k):
    """H32_Hkv8_d128_n32768_b1 -> 'H32/8 d128 n32k b1'"""
    parts = k.split("_")
    H, Hkv, d, n, b = parts[0][1:], parts[1][3:], parts[2][1:], int(parts[3][1:]), parts[4][1:]
    ns = ("%dk" % (n // 1024)) if n % 1024 == 0 else str(n)
    return "H%s/%s\nd%s\nn%s\nb%s" % (H, Hkv, d, ns, b)


def layout_key(r):
    s = r["order"].replace("_major", "") + "/" + r["residency"]
    return s + (":" + r["block_tokens"] if r["residency"] == "paged" else "")


def load(path):
    rows = []
    for r in read_csv(path):
        if r.get("verified", "1") != "1":
            continue
        r["t"] = float(r["t_us"])
        rows.append(r)
    return rows


def style(ax, title, xl, yl):
    ax.set_title(title, fontsize=12, fontweight="bold", loc="left")
    ax.set_xlabel(xl)
    ax.set_ylabel(yl)
    ax.grid(axis="y", color="#E2E8F0", linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", required=True)
    ap.add_argument("--predicted")
    ap.add_argument("--out", default="results/figs")
    ap.add_argument("--heldout-every", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rows = load(a.sweep)
    by_shape = collections.defaultdict(list)
    for r in rows:
        by_shape[shape_key(r)].append(r)
    shapes = sorted(by_shape)
    held = {k for i, k in enumerate(shapes) if a.heldout_every > 0 and i % a.heldout_every == a.heldout_every - 1}
    summary = {"device": rows[0].get("device", ""), "rows": len(rows), "shapes": len(shapes), "heldout_shapes": sorted(held)}

    # ---- H1: spread among configurations that move the same bytes (fp16 only).
    spread = {}
    for k in shapes:
        f16 = [r["t"] for r in by_shape[k] if r["fmt"] == "f16"]
        if f16:
            spread[k] = {"best_us": min(f16), "worst_us": max(f16), "median_us": float(np.median(f16)),
                         "worst_over_best": max(f16) / min(f16), "n_plans": len(f16)}
    summary["fp16_spread"] = spread
    fig, ax = plt.subplots(figsize=(9, 4.6))
    x = np.arange(len(shapes))
    best = [spread[k]["best_us"] for k in shapes]
    med = [spread[k]["median_us"] for k in shapes]
    worst = [spread[k]["worst_us"] for k in shapes]
    w = 0.27
    ax.bar(x - w, best, w, color=TEAL, label="best plan")
    ax.bar(x, med, w, color=AMBER, label="median plan")
    ax.bar(x + w, worst, w, color=ROSE, label="worst plan")
    ax.set_xticks(x)
    ax.set_xticklabels([short(k) for k in shapes], fontsize=8)
    ax.set_yscale("log")
    for i, k in enumerate(shapes):
        ax.text(i, worst[i] * 1.08, "%.1fx" % spread[k]["worst_over_best"], ha="center", fontsize=8, color=SLATE)
    style(ax, "Same bytes, different runtime (fp16 plans only)", "decode shape", "time per decode step (us, log)")
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(a.out, "h1_spread.png"), dpi=160)
    plt.close(fig)

    # ---- how much does each axis matter: best achievable given one axis value.
    axes_def = {
        "format": fmt_key, "layout": layout_key,
        "splits": lambda r: r["splits"], "gqa_pack": lambda r: r["gqa_pack"],
        "warps": lambda r: r["warps"], "unroll": lambda r: r["unroll"],
    }
    axis_effect = {}
    for name, keyf in axes_def.items():
        ratios = collections.defaultdict(list)  # value -> list of (best given value / global best) per shape
        for k in shapes:
            sh = by_shape[k]
            gbest = min(r["t"] for r in sh)
            groups = collections.defaultdict(list)
            for r in sh:
                groups[keyf(r)].append(r["t"])
            for v, ts in groups.items():
                ratios[v].append(min(ts) / gbest)
        axis_effect[name] = {v: float(np.median(rs)) for v, rs in ratios.items()}
    summary["axis_effect"] = axis_effect

    fig, axs = plt.subplots(2, 3, figsize=(12, 6.2))
    for ax, (name, eff) in zip(axs.ravel(), axis_effect.items()):
        keys = sorted(eff, key=lambda s: (len(s), s)) if name in ("format", "layout") else sorted(eff, key=lambda s: int(s))
        vals = [eff[k] for k in keys]
        ax.bar(range(len(keys)), vals, color=[TEAL if v < 1.05 else AMBER if v < 1.5 else ROSE for v in vals])
        ax.set_xticks(range(len(keys)))
        ax.set_xticklabels(keys, rotation=45 if len(keys) > 5 else 0, ha="right" if len(keys) > 5 else "center", fontsize=7)
        ax.axhline(1.0, color=SLATE, linewidth=0.8)
        style(ax, "axis: " + name, "", "best given choice / best overall")
    fig.suptitle("What each axis costs if you pick the wrong value (median over shapes)", fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(a.out, "axis_effect.png"), dpi=160)
    plt.close(fig)

    # ---- speedup of lossy formats over fp16, best plan each.
    speed = collections.defaultdict(dict)
    for k in shapes:
        sh = by_shape[k]
        base = min((r["t"] for r in sh if r["fmt"] == "f16"), default=None)
        for f in sorted({fmt_key(r) for r in sh}):
            t = min(r["t"] for r in sh if fmt_key(r) == f)
            if base:
                speed[k][f] = base / t
    summary["format_speedup_vs_f16"] = speed
    err = collections.defaultdict(list)
    for r in rows:
        if r["fmt"] != "f16":
            err[fmt_key(r)].append(float(r["err_exact"]))
    summary["format_rel_err_median"] = {f: float(np.median(v)) for f, v in err.items()}

    # ---- prediction quality.
    if a.predicted and os.path.exists(a.predicted):
        pred = [r for r in read_csv(a.predicted) if r["verified"] == "1"]
        panels = ((("fitted shapes", lambda k: k not in held), ("held-out shapes", lambda k: k in held))
                  if held else (("all shapes: frozen constants, no refit", lambda k: True),))
        fig, axs = plt.subplots(1, len(panels), figsize=(11 if held else 6, 4.8), sharex=True, sharey=True, squeeze=False)
        for ax, (title, pick) in zip(axs[0], panels):
            sel = [r for r in pred if pick(r["shape"])]
            if not sel:
                continue
            m = np.array([float(r["t_us"]) for r in sel])
            p = np.array([float(r["pred_us"]) for r in sel])
            cols = [{"f16": TEAL, "int8": AMBER, "int4": ROSE}[r["fmt"]] for r in sel]
            ax.scatter(m, p, s=4, c=cols, alpha=0.5, linewidths=0)
            lo, hi = min(m.min(), p.min()) * 0.8, max(m.max(), p.max()) * 1.2
            ax.plot([lo, hi], [lo, hi], color=SLATE, linewidth=1)
            ax.set_xscale("log")
            ax.set_yscale("log")
            mape = float(np.mean(np.abs(p - m) / m))
            style(ax, "%s  (MAPE %.0f%%)" % (title, 100 * mape), "measured (us)", "predicted (us)")
        fig.tight_layout()
        fig.savefig(os.path.join(a.out, "pred_vs_meas.png"), dpi=160)
        plt.close(fig)

    with open(os.path.join(a.out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print("wrote figures and summary.json to", a.out)
    for k in shapes:
        s = spread.get(k)
        if s:
            print("%-26s fp16: best %8.1f us  worst %9.1f us  spread %5.1fx  (%d plans)" % (k, s["best_us"], s["worst_us"], s["worst_over_best"], s["n_plans"]))


if __name__ == "__main__":
    main()
