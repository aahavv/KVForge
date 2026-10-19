"""Transfer test: what the frozen model achieves on the second GPU, against alternatives.

    python tools/transfer_report.py results/sweep_rtx5060-laptop.csv results/sweep_rtx4060.csv \
        results/predicted_rtx4060.csv

Compares, on the second GPU's measured times and for each shape and eligibility class:
  model     the plan the frozen model (fitted on the first GPU) picks with the second
            GPU's machine file, no refit;
  borrow    the plan that was measured fastest on the FIRST GPU, used as is: "tune
            once, reuse everywhere", the practical alternative to a model;
  oracle    the plan measured fastest on the second GPU;
  baseline  the naive plan.
Regret is T(plan) / T(oracle) - 1 on the second GPU.
"""
import collections
import csv
import json
import math
import sys

a_path, b_path, pred_path = sys.argv[1:4]


def key(r):
    return (r["H"], r["H_kv"], r["d"], r["n"], r["batch"], r["fmt"], r["group"], r["order"], r["residency"],
            r["block_tokens"], r["splits"], r["gqa_pack"], r["warps"], r["unroll"])


def load(p):
    return {key(r): r for r in csv.DictReader(open(p)) if r["verified"] == "1"}


A, B = load(a_path), load(b_path)
pred = {}
for r in csv.DictReader(open(pred_path)):
    if r["verified"] == "1":
        pred[(r["shape"], r["fmt"], r["group"], r["order"], r["residency"], r["block_tokens"], r["splits"], r["gqa_pack"], r["warps"], r["unroll"])] = float(r["pred_us"])


def shape_of(r):
    return "H%s_Hkv%s_d%s_n%s_b%s" % (r["H"], r["H_kv"], r["d"], r["n"], r["batch"])


classes = [("lossless (f16)", lambda r: r["fmt"] == "f16"), ("int8 allowed", lambda r: r["fmt"] != "int4"), ("all formats", lambda r: True)]
common = [k for k in A if k in B]
by_shape = collections.defaultdict(list)
for k in common:
    by_shape[shape_of(B[k])].append(k)
print("plans present on both GPUs: %d of %d / %d" % (len(common), len(A), len(B)))


def pk(r):
    return (shape_of(r), r["fmt"], r["group"], r["order"], r["residency"], r["block_tokens"], r["splits"], r["gqa_pack"], r["warps"], r["unroll"])


def is_baseline(r):
    return (r["fmt"] == "f16" and r["order"] == "token_major" and r["residency"] == "contiguous" and r["splits"] == "1"
            and r["gqa_pack"] == "0" and r["warps"] == "4" and r["unroll"] == "2")


def gmean(x):
    return math.exp(sum(math.log(v) for v in x) / len(x))


res = {}
print("\n%-26s %-14s %9s %9s %9s %9s | %8s %8s" % ("shape", "class", "oracle", "model", "borrow", "baseline", "model%", "borrow%"))
agg = collections.defaultdict(lambda: collections.defaultdict(list))
for sh in sorted(by_shape):
    ks = by_shape[sh]
    base = [float(B[k]["t_us"]) for k in ks if is_baseline(B[k])][0]
    for cname, ok in classes:
        el = [k for k in ks if ok(B[k])]
        orc = min(float(B[k]["t_us"]) for k in el)
        mk = min(el, key=lambda k: pred[pk(B[k])])
        bk = min(el, key=lambda k: float(A[k]["t_us"]))
        tm, tb = float(B[mk]["t_us"]), float(B[bk]["t_us"])
        print("%-26s %-14s %9.1f %9.1f %9.1f %9.1f | %7.1f%% %7.1f%%" % (sh, cname, orc, tm, tb, base, 100 * (tm / orc - 1), 100 * (tb / orc - 1)))
        agg[cname]["model"].append(tm / orc - 1)
        agg[cname]["borrow"].append(tb / orc - 1)
        agg[cname]["speed_model"].append(base / tm)
        agg[cname]["speed_borrow"].append(base / tb)
        res.setdefault(sh, {})[cname] = {"oracle_us": orc, "model_us": tm, "borrow_us": tb, "baseline_us": base,
                                         "model_plan": [B[mk][c] for c in ("fmt", "group", "order", "residency", "splits", "gqa_pack", "warps", "unroll")],
                                         "borrow_plan": [B[bk][c] for c in ("fmt", "group", "order", "residency", "splits", "gqa_pack", "warps", "unroll")]}
print()
summary = {}
for cname, _ in classes:
    d = agg[cname]
    summary[cname] = {"model_regret_mean": sum(d["model"]) / len(d["model"]), "model_regret_max": max(d["model"]),
                      "borrow_regret_mean": sum(d["borrow"]) / len(d["borrow"]), "borrow_regret_max": max(d["borrow"]),
                      "model_speedup_geomean": gmean(d["speed_model"]), "borrow_speedup_geomean": gmean(d["speed_borrow"])}
    print("%-16s model: regret mean %5.1f%% max %5.1f%%, speedup %.2fx | borrow: regret mean %5.1f%% max %5.1f%%, speedup %.2fx" % (
        cname, 100 * summary[cname]["model_regret_mean"], 100 * summary[cname]["model_regret_max"], summary[cname]["model_speedup_geomean"],
        100 * summary[cname]["borrow_regret_mean"], 100 * summary[cname]["borrow_regret_max"], summary[cname]["borrow_speedup_geomean"]))

# agreement between the two GPUs on which plans are good
def rank(v):
    idx = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    for pos, i in enumerate(idx):
        r[i] = pos
    return r


rhos = []
for sh in sorted(by_shape):
    ks = by_shape[sh]
    ra, rb = rank([float(A[k]["t_us"]) for k in ks]), rank([float(B[k]["t_us"]) for k in ks])
    n = len(ks)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    rhos.append(num / den)
summary["gpu_to_gpu_measured_rank_correlation_mean"] = sum(rhos) / len(rhos)
print("\nmeasured rank correlation between the two GPUs' own timings (plan by plan): mean %.3f" % summary["gpu_to_gpu_measured_rank_correlation_mean"])
json.dump({"summary": summary, "per_shape": res}, open("results/figs_rtx4060/transfer_summary.json", "w"), indent=2)

# ---------------------------------------------------------------------------
# New-shape test: a shape nobody tuned. The alternative to the model is to reuse the
# first GPU's winning plan of the most similar OTHER shape (same head size, nearest
# context length, batch and group size), snapping split counts that the new shape
# does not allow to the nearest allowed one.
def shape_params(sh):
    p = sh.split("_")
    H, Hkv, d, n, b = int(p[0][1:]), int(p[1][3:]), int(p[2][1:]), int(p[3][1:]), int(p[4][1:])
    return H, Hkv, d, n, b, H // Hkv


def distance(s1, s2):
    H1, K1, d1, n1, b1, g1 = shape_params(s1)
    H2, K2, d2, n2, b2, g2 = shape_params(s2)
    return (0 if d1 == d2 else 100) + abs(math.log2(n1 / n2)) + abs(math.log2(b1 / b2)) + (0 if g1 == g2 else 3)


print("\n--- new-shape test: model vs reusing the nearest other shape's winner (first GPU's tuning) ---")
print("%-26s %-14s %-26s %9s %9s | %8s %8s" % ("shape", "class", "nearest other shape", "model", "nn-borrow", "model%", "nn%"))
nn_agg = collections.defaultdict(lambda: collections.defaultdict(list))
for sh in sorted(by_shape):
    ks = by_shape[sh]
    others = [o for o in by_shape if o != sh]
    src = min(others, key=lambda o: distance(sh, o))
    for cname, ok in classes:
        el = [k for k in ks if ok(B[k])]
        orc = min(float(B[k]["t_us"]) for k in el)
        mk = min(el, key=lambda k: pred[pk(B[k])])
        sk = min((k for k in by_shape[src] if ok(B[k])), key=lambda k: float(A[k]["t_us"]))
        # snap the donor plan onto this shape's plan set
        same = [k for k in el if k[5:10] == sk[5:10] and k[11:] == sk[11:] or (k[5:10] == sk[5:10] and k[11] == sk[11] and k[12:] == sk[12:])]
        cand = [k for k in el if k[5:10] == sk[5:10] and k[11] == sk[11] and k[12] == sk[12] and k[13] == sk[13]]
        if not cand:
            cand = [k for k in el if k[5:10] == sk[5:10]]
        pick = min(cand, key=lambda k: abs(math.log2(int(k[10])) - math.log2(int(sk[10]))))
        tn = float(B[pick]["t_us"])
        tm = float(B[mk]["t_us"])
        nn_agg[cname]["model"].append(tm / orc - 1)
        nn_agg[cname]["nn"].append(tn / orc - 1)
        print("%-26s %-14s %-26s %9.1f %9.1f | %7.1f%% %7.1f%%" % (sh, cname, src, tm, tn, 100 * (tm / orc - 1), 100 * (tn / orc - 1)))
print()
for cname, _ in classes:
    d = nn_agg[cname]
    summary[cname]["nearest_shape_borrow_regret_mean"] = sum(d["nn"]) / len(d["nn"])
    summary[cname]["nearest_shape_borrow_regret_max"] = max(d["nn"])
    print("%-16s model: regret mean %5.1f%% max %5.1f%% | nearest-shape borrow: regret mean %5.1f%% max %5.1f%%" % (
        cname, 100 * sum(d["model"]) / len(d["model"]), 100 * max(d["model"]), 100 * sum(d["nn"]) / len(d["nn"]), 100 * max(d["nn"])))
json.dump({"summary": summary, "per_shape": res}, open("results/figs_rtx4060/transfer_summary.json", "w"), indent=2)
