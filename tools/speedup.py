"""Measured speedup of the compiler's pick over a plain baseline.

    python tools/speedup.py results/predicted_rtx5060-laptop.csv

For every shape the compiler "chooses" the plan with the smallest predicted time
among the eligible formats, without running anything. This reports how that plan
actually measured, against
  * the baseline: fp16, token-major, contiguous, no splitting, no GQA packing,
    4 warps, unroll 2 (what a straightforward first kernel does), and
  * the best plan in the whole sweep (the oracle an exhaustive search would find).
"""
import collections
import csv
import json
import sys

rows = [r for r in csv.DictReader(open(sys.argv[1])) if r["verified"] == "1"]
by = collections.defaultdict(list)
for r in rows:
    by[r["shape"]].append(r)


def baseline(rs):
    for r in rs:
        if (r["fmt"] == "f16" and r["order"] == "token_major" and r["residency"] == "contiguous"
                and r["splits"] == "1" and r["gqa_pack"] == "0" and r["warps"] == "4" and r["unroll"] == "2"):
            return float(r["t_us"])


classes = [("lossless (f16)", lambda r: r["fmt"] == "f16"),
           ("int8 allowed (err<=0.02)", lambda r: r["fmt"] != "int4"),
           ("all formats", lambda r: True)]
out = {}
print("%-26s %-26s %9s %9s %9s %8s %8s" % ("shape", "class", "baseline", "chosen", "oracle", "speedup", "regret"))
for sh in sorted(by):
    rs = by[sh]
    base = baseline(rs)
    for name, ok in classes:
        el = [r for r in rs if ok(r)]
        pick = min(el, key=lambda r: float(r["pred_us"]))
        oracle = min(float(r["t_us"]) for r in el)
        t = float(pick["t_us"])
        out.setdefault(sh, {})[name] = {"baseline_us": base, "chosen_us": t, "oracle_us": oracle,
                                        "speedup_vs_baseline": base / t if base else None,
                                        "regret": t / oracle - 1,
                                        "plan": "%s %s/%s:%s splits=%s pack=%s w%s u%s" % (
                                            pick["fmt"] + (":" + pick["group"] if pick["fmt"] != "f16" else ""),
                                            pick["order"], pick["residency"], pick["block_tokens"], pick["splits"],
                                            pick["gqa_pack"], pick["warps"], pick["unroll"])}
        print("%-26s %-26s %9.1f %9.1f %9.1f %7.2fx %7.1f%%" % (sh, name, base or 0, t, oracle, (base / t) if base else 0, 100 * (t / oracle - 1)))
for name, _ in classes:
    sp = [v[name]["speedup_vs_baseline"] for v in out.values() if v[name]["speedup_vs_baseline"]]
    rg = [v[name]["regret"] for v in out.values()]
    gm = 1.0
    for x in sp:
        gm *= x
    print("geomean speedup over baseline, %-26s %.2fx   mean regret %.1f%%" % (name, gm ** (1 / len(sp)), 100 * sum(rg) / len(rg)))
json.dump(out, open(sys.argv[2] if len(sys.argv) > 2 else "results/figs/speedup.json", "w"), indent=2)
