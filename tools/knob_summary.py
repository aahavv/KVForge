"""How much each plan knob matters on the new kernels, from every searched plan.

    python tools/knob_summary.py [results/lowrank/knobs_all_plans.csv]

For each variant, shape and knob value: the best time with the knob held at that
value, over the best time overall. "Worst value costs" = the largest of those per
shape (the same measure as the "Which axes matter" table in docs/results.md),
reported as the median and the maximum over shapes. "Best value" = the value
the overall winner used, counted over shapes.
"""
import collections
import csv
import statistics
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "results/lowrank/knobs_all_plans.csv"
plans = collections.defaultdict(list)
for r in csv.DictReader(open(path)):
    plans[(r["variant"], r["shape"])].append(r)

KNOBS = ["splits", "pack", "U", "warps"]
for variant in sorted({v for v, _ in plans}):
    print("\n%s" % variant)
    spread = []
    per_knob = {k: [] for k in KNOBS}
    winners = {k: collections.Counter() for k in KNOBS}
    for (v, shape), rs in sorted(plans.items()):
        if v != variant:
            continue
        t = {id(r): float(r["t_us"]) for r in rs}
        best = min(rs, key=lambda r: t[id(r)])
        tb = t[id(best)]
        spread.append(max(t.values()) / tb)
        for k in KNOBS:
            vals = sorted({r[k] for r in rs})
            if len(vals) < 2:
                continue
            worst = max(min(t[id(r)] for r in rs if r[k] == val) for val in vals) / tb
            per_knob[k].append(worst - 1)
            winners[k][best[k]] += 1
    print("  plans per shape: %d; worst/best plan: median %.2fx, range %.2fx..%.2fx"
          % (len(rs), statistics.median(spread), min(spread), max(spread)))
    for k in KNOBS:
        if not per_knob[k]:
            print("  %-6s fixed (not searched)" % k)
            continue
        print("  %-6s worst value costs: median %4.0f%%, max %4.0f%%   winning values: %s"
              % (k, 100 * statistics.median(per_knob[k]), 100 * max(per_knob[k]),
                 ", ".join("%s x%d" % (val, c) for val, c in winners[k].most_common())))
