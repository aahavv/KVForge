"""How much tuning effort does the cost model save?

For every shape in a sweep, it compares three ways of choosing a plan:
  model top-k   time only the k plans the model ranks fastest, keep the fastest measured
  random k      time k plans picked at random (exact expectation, no sampling)
  brute force   time every plan (regret 0, but every plan is run)

Regret = measured time of the chosen plan / fastest measured time in the sweep - 1,
the same definition as src/fit.cpp. k = 1 reproduces the regret in docs/results.md.

    python tools/tuning_effort.py results/predicted_rtx5060-laptop.csv
    python tools/tuning_effort.py results/predicted_rtx4060.csv --all-heldout
"""
import argparse
import csv
from collections import defaultdict
from math import comb

HELDOUT = {"H32_Hkv32_d128_n4096_b1", "H32_Hkv8_d128_n4096_b8", "H32_Hkv8_d64_n16384_b1"}
CLASSES = [("fp16 only", {"f16"}), ("int8 allowed", {"f16", "int8"}), ("all formats", {"f16", "int8", "int4"})]
KS = [1, 2, 3, 5, 10, 20, 50]


def model_topk(rows, k):
    # stable sort on the prediction, as the compiler ranks plans
    ranked = sorted(rows, key=lambda r: r["pred"])
    return min(r["t"] for r in ranked[:k])


def random_k(rows, k):
    # expected fastest of k plans drawn without replacement: the i-th fastest (0-based)
    # is the minimum with probability C(N-1-i, k-1) / C(N, k)
    t = sorted(r["t"] for r in rows)
    n = len(t)
    k = min(k, n)
    return sum(t[i] * comb(n - 1 - i, k - 1) for i in range(n - k + 1)) / comb(n, k)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("predicted")
    ap.add_argument("--all-heldout", action="store_true",
                    help="every shape is unseen (transfer test: constants fitted on another GPU)")
    args = ap.parse_args()

    shapes = defaultdict(list)
    for r in csv.DictReader(open(args.predicted)):
        if r["verified"] != "1":
            continue
        shapes[r["shape"]].append({"fmt": r["fmt"], "t": float(r["t_us"]), "pred": float(r["pred_us"])})

    groups = [("all 10 shapes", sorted(shapes))]
    if not args.all_heldout:
        groups.insert(0, ("3 held-out shapes", sorted(s for s in shapes if s in HELDOUT)))

    print(f"Tuning effort: {args.predicted}")
    print("Mean regret over shapes (lower is better). 'plans' = how many plans are timed on the GPU.\n")
    for gname, keys in groups:
        for cname, fmts in CLASSES:
            per = [[r for r in shapes[s] if r["fmt"] in fmts] for s in keys]
            sizes = [len(p) for p in per]
            print(f"{gname}, {cname}: {min(sizes)} to {max(sizes)} plans per shape")
            print(f"  {'plans timed':>11} {'% of search':>12} {'model top-k':>12} {'random k':>10}  worst shape (model)")
            for k in KS:
                best = [min(r["t"] for r in p) for p in per]
                m = [model_topk(p, k) / b - 1 for p, b in zip(per, best)]
                rnd = [random_k(p, k) / b - 1 for p, b in zip(per, best)]
                frac = sum(min(k, n) / n for n in sizes) / len(sizes)
                print(f"  {k:>11} {100 * frac:>11.2f}% {100 * sum(m) / len(m):>11.1f}% "
                      f"{100 * sum(rnd) / len(rnd):>9.1f}%  {100 * max(m):.1f}%")
            # smallest k at which the model's shortlist is within 2% / 5% on every shape
            for tol in (0.05, 0.02):
                need = []
                for p in per:
                    b = min(r["t"] for r in p)
                    need.append(next(k for k in range(1, len(p) + 1) if model_topk(p, k) / b - 1 <= tol))
                print(f"  within {int(tol * 100)}% of the best on every shape: model needs top {max(need)} "
                      f"(per shape: {', '.join(map(str, need))})")
            print()


if __name__ == "__main__":
    main()
