"""Pick the fp16 plans the library comparison runs, per shape.

For each shape: the naive baseline, the plan the compiler picks (lossless, from
the model alone) and the oracle (best measured fp16 plan in the sweep). Written
to results/compare_plans.csv for bench/wsl/compare.py.
"""
import collections
import csv

rows = [r for r in csv.DictReader(open("results/predicted_rtx5060-laptop.csv")) if r["verified"] == "1" and r["fmt"] == "f16"]
by = collections.defaultdict(list)
for r in rows:
    by[r["shape"]].append(r)

out = []
for shape, rs in sorted(by.items()):
    base = [r for r in rs if r["order"] == "token_major" and r["residency"] == "contiguous" and r["splits"] == "1"
            and r["gqa_pack"] == "0" and r["warps"] == "4" and r["unroll"] == "2"][0]
    chosen = min(rs, key=lambda r: float(r["pred_us"]))
    oracle = min([r for r in rs if r["residency"] == "contiguous"], key=lambda r: float(r["t_us"]))
    for role, r in (("baseline", base), ("kvforge_pick", chosen), ("oracle", oracle)):
        out.append({"shape": shape, "role": role, "order": r["order"], "residency": r["residency"],
                    "block_tokens": r["block_tokens"], "splits": r["splits"], "gqa_pack": r["gqa_pack"],
                    "warps": r["warps"], "unroll": r["unroll"], "windows_t_us": r["t_us"]})
with open("results/compare_plans.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0]))
    w.writeheader()
    w.writerows(out)
print(len(out), "rows")
for o in out:
    print("%-26s %-13s %-12s %-10s bt=%-3s splits=%-2s pack=%s w%s u%s  (%.0f us on Windows)" % (
        o["shape"], o["role"], o["order"], o["residency"], o["block_tokens"], o["splits"], o["gqa_pack"], o["warps"], o["unroll"], float(o["windows_t_us"])))
