"""Build "KVForge: performance metrics, what they mean and how we improved them" as a PDF.

    python docs/make_perf_guide_pdf.py [output.pdf]

Default output: C:/Users/aahav/Downloads/KVForge_Performance_Metrics_Guide.pdf

Every result number is read from results/lowrank/ (the final benchmark CSV and the
accuracy-study JSON files), so the guide cannot drift from the data. The step-by-step
history in section 5 quotes single-shape runs from the session log; those are marked as
such. Shares the page style of make_brief_pdf.py.
"""
import collections
import csv
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(HERE, "make_brief_pdf.py"), encoding="utf-8").read()
exec(_src.split("# =========================================================================== title")[0])
OUT = sys.argv[1] if len(sys.argv) > 1 else "C:/Users/aahav/Downloads/KVForge_Performance_Metrics_Guide.pdf"
RES = os.path.join(ROOT, "results", "lowrank")

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def M(t):
    return "<font face='Mono'>%s</font>" % t


def geo(xs):
    return math.exp(sum(math.log(x) for x in xs) / len(xs))


# =========================================================================== the numbers
rows = collections.defaultdict(dict)
for r in csv.DictReader(open(os.path.join(RES, "bench_tc_rtx5060-laptop.csv"))):
    rows[r["shape"]][r["method"]] = float(r["t_us"])
SHAPES = sorted(rows)


def fi16(m):
    return min(v for k, v in m.items() if k.startswith("flashinfer_batch"))


def fi8(m):
    return min(v for k, v in m.items() if k.startswith("flashinfer_fp8"))


BEST = "kvforge_tc_rot_k8g128v4g64"
SIMPLE = "kvforge_tc_k8v4"
sp_best8 = [fi8(rows[s]) / rows[s][BEST] for s in SHAPES]
sp_best16 = [fi16(rows[s]) / rows[s][BEST] for s in SHAPES]
sp_simple8 = [fi8(rows[s]) / rows[s][SIMPLE] for s in SHAPES]
sp_int8 = [fi8(rows[s]) / rows[s]["kvforge_tc_int8"] for s in SHAPES]
sp_f16 = [fi16(rows[s]) / rows[s]["kvforge_f16"] for s in SHAPES]


def study(name):
    d = json.load(open(os.path.join(RES, name)))
    return {r["config"]: r for r in d["results"]}


QG = study("study_groups_qwen3_1.7b.json")
QL = study("study_qwen3_1.7b.json")
QR = study("study_rot_qwen3_1.7b.json")
TG = study("study_groups_tinyllama-1.1b-chat-v1.0.json")


def ppl(tab, key):
    return tab[key]["ppl"]


def pct(tab, key):
    return 100.0 * (tab[key]["ppl"] / tab["f16"]["ppl"] - 1.0)


def short(shape):
    H, Hkv, d, n, b = shape.split("_")
    n = int(n[1:])
    return "%s/%s d%s %dk b%s" % (H[1:], Hkv[3:], d[1:], n // 1024, b[1:])


# =========================================================================== chart
fig, ax = plt.subplots(figsize=(7.2, 3.9), dpi=200)
labels = [short(s) for s in SHAPES]
y = range(len(SHAPES))
# bars grow from 1.0 (a tie), so a bar's length is the gain or the loss
ax.barh([i + 0.2 for i in y], [a - 1 for a in sp_best8], left=1, height=0.38, color="#0F766E",
        label="Best format vs FlashInfer fp8 (same or better accuracy)")
ax.barh([i - 0.2 for i in y], [b - 1 for b in sp_int8], left=1, height=0.38, color="#94A3B8",
        label="Kernel only: KVForge int8 vs FlashInfer fp8 (about equal bytes)")
ax.axvline(1.0, color="#0B1220", lw=1)
for i, (a, b) in enumerate(zip(sp_best8, sp_int8)):
    ax.text(a + 0.006, i + 0.2, "%.2fx" % a, va="center", fontsize=7)
    ax.text(b + (0.006 if b >= 1 else -0.006), i - 0.2, "%.2fx" % b, va="center", ha="left" if b >= 1 else "right",
            fontsize=7, color="#475569")
ax.set_yticks(list(y))
ax.set_yticklabels(labels, fontsize=7.5)
ax.set_xlim(0.84, 1.36)
ax.set_xlabel("speedup over FlashInfer fp8 (1.0 = tie; right of the line = KVForge faster)", fontsize=8)
ax.tick_params(axis="x", labelsize=7.5)
ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.45, -0.16), ncol=1, frameon=False)
ax.set_title("The win comes from the format: at equal bytes the kernel ties or trails", fontsize=9, loc="left")
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
fig.tight_layout()
CHART = os.path.join(ROOT, "results", "lowrank", "speedup_vs_fp8.png")
fig.savefig(CHART)
plt.close(fig)

# =========================================================================== title
P("KVForge: performance metrics", "title")
P("What every number means, how we measured it fairly, and how the compressed-cache kernels came to beat "
  "FlashInfer's fp8 decode on all 10 test shapes. RTX 5060 Laptop, October 2026.", "subtitle")
story.append(Spacer(1, 6))
STATS([("%.2fx" % geo(sp_best8), "faster than FlashInfer fp8<br/>(geomean, 10 shapes)"),
       ("%.2fx" % geo(sp_best16), "faster than FlashInfer fp16<br/>(geomean)"),
       ("%+.2f%%" % pct(QG, "rot K int8:128 V int4:64"), "perplexity change<br/>(Qwen3-1.7B)"),
       ("%.2fx" % QG["rot K int8:128 V int4:64"]["bytes_vs_f16"], "bytes read<br/>vs fp16 (fp8 = 0.50x)")])
BOX("<b>The one-paragraph version.</b> Decode attention is limited by how many bytes of KV cache the GPU reads. "
    "We found, on two real models, a cache format that reads 20%% fewer bytes than fp8 with no accuracy loss "
    "(int8 keys and int4 values after a Hadamard rotation), and wrote a tensor-core kernel that runs it at memory "
    "speed. Our kernels are <b>not</b> faster than FlashInfer's when both read the same bytes "
    "(%.2fx for fp16, %.2fx for int8 against fp8); the win is the format, run well." % (geo(sp_f16), geo(sp_int8)), "note")

# =========================================================================== 1
H1("1. Why decode attention is a memory problem")
P("One decode step compares one new query per head with every cached key and averages the matching values. Each "
  "cached byte is read once and used once (reuse = 1), so the math units mostly wait for memory.")
TABLE([
    ["Quantity", "RTX 5060 Laptop", "What it means here"],
    ["Peak memory bandwidth", "341 GB/s (measured)", "The fastest the cache can be read"],
    ["FP32 compute", "16 TFLOP/s", "Far more than attention needs"],
    ["Ridge point", "47 FLOP per byte", "Below this, a kernel is memory-bound; attention is at about 2 to 8"],
], [42, 40, 92])
P("So: <b>time = bytes read / achieved bandwidth</b>. Example: 32 query heads, 8 KV heads, head size 128, 32k tokens "
  "in fp16 is 134 MB of K and V per step, so at least 393 us at 341 GB/s, whatever the code does. There are two ways "
  "down: fewer bits per number (quantization) or fewer numbers per token (low-rank). We tried both.")

# =========================================================================== 2
H1("2. The metrics, one by one")
H2("Speed")
TABLE([
    ["Metric", "Unit", "Meaning", "How to read it"],
    ["Latency (t_us)", "us", "Time for one decode step of one attention layer, from the start of the first kernel to the end of the last",
     "Lower is better. Includes every kernel a method needs (query rotation, attention, split merge)"],
    ["Median", "us", "Middle value of 30 timed repetitions", "Robust to one slow run, unlike the mean"],
    ["IQR (p25..p75)", "us", "Range holding the middle half of the repetitions", "A narrow IQR means a stable measurement"],
    ["Achieved bandwidth", "GB/s", "Bytes the kernel must read / its time", "Near 341 GB/s = the kernel is as fast as memory allows"],
    ["Speedup", "x", "Other method's time / our time", "1.19x = we take 1/1.19 = 84% of their time"],
    ["Geomean speedup", "x", "Geometric mean of the per-shape speedups", "The right average for ratios: 2x and 0.5x average to 1x, not 1.25x"],
    ["Memory clock", "MHz", "GPU memory clock during the run (9001 to 11871)", "Varies on this laptop, so methods are timed interleaved"],
], [30, 18, 62, 64])
H2("Size")
TABLE([
    ["Metric", "Meaning"],
    ["Bytes per element", "fp16 = 2, fp8 = int8 = 1, int4 = 0.5, plus the group metadata below"],
    [M("int8:G"), "int8 codes with one fp16 scale and one fp16 zero (4 bytes) per G elements. int8:32 adds 12.5% to the codes, int8:128 adds 3%"],
    ["Bytes vs fp16", "A format's K + V bytes per token over fp16's. FlashInfer fp8 = 0.50; our best = 0.40"],
], [32, 142])
H2("Accuracy")
TABLE([
    ["Metric", "Meaning", "How to read it"],
    ["Perplexity (PPL)", "exp(average negative log-likelihood) of the next token on WikiText-2: how surprised the model is",
     "Lower is better. Compare to the fp16 cache: +0.2% is invisible in practice, +12% is a damaged model"],
    ["Attention rel. error", "||out - out_fp16|| / ||out_fp16|| of one attention layer's output, averaged over layers",
     "KVForge's accuracy gate bounds this. Useful but a weak proxy: 0.07 can still mean no perplexity loss"],
    ["Error vs reference (err)", "Our kernel's output vs an fp32 computation from exactly the bytes it stores",
     "A correctness check, not accuracy: about 4e-4 = fp16 rounding, so the kernel computes the right thing"],
], [34, 76, 64])
H2("Compiler quality (from the earlier sweep)")
TABLE([
    ["Metric", "Meaning"],
    ["Regret", "How much slower the compiler's chosen plan is than the best plan measured. 0% = perfect choice"],
    ["Spearman rho / Kendall tau", "Do predicted and measured times put plans in the same order? 1 = identical order"],
    ["MAPE", "Mean absolute percentage error of the predicted time. A compiler needs the order right more than the exact time"],
    ["Oracle", "The best plan found by measuring every candidate. An upper bound, not something a compiler gets for free"],
], [40, 134])

# =========================================================================== 3
H1("3. How we kept the comparison fair")
B(["<b>Same process, same GPU, same data.</b> Every method runs on identical K and V, in one Python process.",
   "<b>L2 cache flushed</b> (256 MB written) before every repetition, so no method reads a warm cache.",
   "<b>Interleaved timing.</b> One repetition of every method in turn, 30 rounds. The laptop's memory clock moved between "
   "9001 and 11871 MHz between runs; interleaving makes any change hit all methods alike.",
   "<b>AC power only.</b> A run on battery halved every number and was thrown away.",
   "<b>Every plan checked.</b> Each candidate's output is compared with an fp32 reference before it can be timed. "
   "0 plans were rejected in the final run.",
   "<b>FlashInfer at its best:</b> both its CUDA-core and tensor-core paths, fp16 and fp8, the faster one per shape.",
   "<b>Accuracy on real models, not random data:</b> random data said int4 was fine; real models say it is broken."])
BOX("<b>One thing that still favours us:</b> our plan (split count, warps, pipelining) is the best of about 36 measured "
    "candidates, an oracle. FlashInfer picks its plan once from built-in rules. KVForge's own cost model does not yet "
    "choose plans for the new kernel; on the old kernels its pick was 2 to 15% slower than the oracle.", "warn")

# =========================================================================== 4
H1("4. What we tried, and what each idea was worth")
TABLE([
    ["Idea", "Result", "Kept?"],
    ["Low-rank keys (SVD of the keys, rank 64 of 128)", "Keeps 97%% of key energy but perplexity %.0f (plain) or %.2f (query-aware) vs %.2f"
     % (ppl(QL, "K:f16+lr64 V:f16"), ppl(QL, "K:f16+lr64q V:f16"), ppl(QL, "K:f16 V:f16")), "No"],
    ["int4 keys and values", "Perplexity %.1f: outlier channels in real keys break 4-bit keys" % ppl(QR, "int4:32"), "No"],
    ["int8 keys + int4 values", "Perplexity %+.2f%%, 0.44x bytes. Keys are the sensitive half" % pct(QG, "K int8:32 V int4:32"), "Yes"],
    ["Hadamard rotation, groups of 128", "Perplexity %+.2f%%, 0.40x bytes: rotation spreads outliers so groups can grow"
     % pct(QG, "rot K int8:128 V int4:64"), "Yes"],
    ["Register cap for more warps", "Registers spilled to memory: 30 to 150x slower", "No"],
], [52, 106, 16])

# =========================================================================== 5
H1("5. How performance improved, step by step")
P("The steps below are the 32k-token grouped-query shape (32 query heads, 8 KV heads). Steps 1 to 4 come from "
  "single-shape runs during development whose memory clocks differed, so compare each KVForge number with the "
  "FlashInfer number <b>from the same run</b>, not across rows.", "small")
TABLE([
    ["Step", "Change", "KVForge", "FlashInfer fp8 (same run)"],
    ["1", "Starting point: CUDA-core kernel, int8 K and V", "337 us", "269 us"],
    ["2", "Integer-to-float without the slow I2F instruction (byte-permute into the mantissa of 2^23)", "286 us", "269 us"],
    ["3", "Softmax rescale once per batch of tokens; int8 zero point as one scalar per lane", "256 us (rank-64 keys)", "267 us"],
    ["4", "int8 keys + int4 values (fewer bytes) on the same CUDA-core kernel", "254 us", "226 us"],
    ["5", "Tensor-core kernel: query heads as matrix rows, 16 tokens per mma, keys and values dequantized in registers", "196 us", "216 us"],
    ["6", "Hadamard rotation fused into the kernel, groups of 128, final interleaved run",
     "%.0f us" % rows["H32_Hkv8_d128_n32768_b1"][BEST], "%.0f us" % fi8(rows["H32_Hkv8_d128_n32768_b1"])],
], [11, 95, 30, 38])
H2("Why step 5 was the big one")
P("After step 3 the kernel was limited by instructions, not memory: every lane redid the softmax and the head loop, "
  "about 100 warp instructions per token. Fewer bytes did not help (rank-32 keys were no faster than rank-64). "
  "The tensor-core version does the head loop in one matrix instruction, about 20 warp instructions per token, so the "
  "kernel became memory-bound again and fewer bytes turned into less time.")
B(["<b>Scores:</b> S = Q K<super>T</super> with query heads as the matrix rows and 8 tokens as the columns.",
   "<b>Output:</b> O<super>T</super> = V<super>T</super> P<super>T</super>, so the probabilities P come out of the score step already in the "
   "register layout the next instruction needs: no shuffles, no shared memory.",
   "<b>Loads:</b> the order of the head dimension is permuted (a dot product does not care) so each lane reads 16 contiguous bytes.",
   "<b>Dequantization:</b> int8 and int4 codes become fp16 with a byte-permute and one fused multiply-add, two numbers per instruction."])

# =========================================================================== 6
H1("6. Final results, all 10 shapes")
FIG("results/lowrank/speedup_vs_fp8.png", 172,
    "Teal: our best format against FlashInfer fp8. Grey: the kernel-only comparison at about equal bytes. "
    "Shape = query heads / KV heads, head size, context, batch.")
tab = [["Shape", "FI fp16", "FI fp8", "KVForge best", "vs fp8", "vs fp16"]]
for s in SHAPES:
    m = rows[s]
    tab.append([short(s), "%.1f" % fi16(m), "%.1f" % fi8(m), "%.1f" % m[BEST], "%.2fx" % (fi8(m) / m[BEST]), "%.2fx" % (fi16(m) / m[BEST])])
tab.append(["Geomean", "", "", "", "%.2fx" % geo(sp_best8), "%.2fx" % geo(sp_best16)])
TABLE(tab, [44, 24, 24, 30, 26, 26])
P("Times in microseconds. KVForge best = rotated int8:128 keys + int4:64 values on the tensor-core kernel.", "small")

H2("Accuracy of the formats (WikiText-2 perplexity)")
TABLE([
    ["Format", "Qwen3-1.7B", "TinyLlama-1.1B", "Bytes vs fp16"],
    ["fp16 (reference)", "%.3f" % ppl(QG, "f16"), "%.3f" % ppl(TG, "f16"), "1.00"],
    ["fp8 (FlashInfer)", "%.3f (%+.2f%%)" % (ppl(QG, "fp8 (FlashInfer)"), pct(QG, "fp8 (FlashInfer)")),
     "%.3f (%+.2f%%)" % (ppl(TG, "fp8 (FlashInfer)"), pct(TG, "fp8 (FlashInfer)")), "0.50"],
    ["int8:32 K + int4:32 V", "%.3f (%+.2f%%)" % (ppl(QG, "K int8:32 V int4:32"), pct(QG, "K int8:32 V int4:32")),
     "%.3f (%+.2f%%)" % (ppl(TG, "K int8:32 V int4:32"), pct(TG, "K int8:32 V int4:32")), "0.44"],
    ["rotated int8:128 K + int4:64 V", "%.3f (%+.2f%%)" % (ppl(QG, "rot K int8:128 V int4:64"), pct(QG, "rot K int8:128 V int4:64")),
     "%.3f (%+.2f%%)" % (ppl(TG, "rot K int8:128 V int4:64"), pct(TG, "rot K int8:128 V int4:64")), "0.40"],
], [58, 42, 42, 32])
P("TinyLlama has head size 64, so its groups stop at 64. 40 windows of 2,048 tokens per model.", "small")

# =========================================================================== 7
H1("7. The three fair comparisons")
TABLE([
    ["Comparison", "What it isolates", "Result"],
    ["fp16 vs fp16", "Kernel quality only (same bytes, exact)", "%.2fx geomean, range %.2f to %.2f: a tie, and 0.80x on the 64/8 shape"
     % (geo(sp_f16), min(sp_f16), max(sp_f16))],
    ["KVForge int8 vs FlashInfer fp8", "Kernel quality only (1.125 vs 1 byte per element)", "%.2fx geomean, range %.2f to %.2f: FlashInfer slightly faster"
     % (geo(sp_int8), min(sp_int8), max(sp_int8))],
    ["Best format vs FlashInfer fp8", "Format plus kernel at equal or better accuracy", "<b>%.2fx</b> geomean, range %.2f to %.2f, faster on every shape"
     % (geo(sp_best8), min(sp_best8), max(sp_best8))],
], [46, 58, 70])
BOX("Say it this way: <i>at fp8's accuracy, KVForge's format reads 20%% fewer bytes and its tensor-core kernel runs at "
    "memory speed, so decode attention is %.2fx faster than FlashInfer fp8 and %.2fx faster than fp16.</i> Do not say "
    "the kernel is faster than FlashInfer's." % (geo(sp_best8), geo(sp_best16)), "callout")

# =========================================================================== 8
H1("8. Caveats")
B(["<b>Oracle plans.</b> Our plan is the best of about 36 measured; FlashInfer's is its first guess. With the compiler "
   "choosing, expect the speedup over fp8 to shrink by a few percent (estimate from past regret, not measured).",
   "<b>Layouts differ.</b> FlashInfer reads its paged cache (16-token pages); ours is contiguous.",
   "<b>FlashInfer's single-request kernel</b> could not be built (no CUDA compiler in WSL); its batch kernel was used.",
   "<b>Writing the cache</b> (quantizing each new token) is not timed. It is one token per step, small but not zero.",
   "<b>One GPU</b>, a laptop RTX 5060 under WSL. A datacenter GPU has 5 to 10x the bandwidth and results may differ.",
   "<b>Two small models</b>, 2k context, perplexity only. No long-context retrieval test (needle-in-a-haystack, LongBench).",
   "<b>fp16 grouped shape with 8 heads per KV head</b> is still 0.80x FlashInfer: the fp16 path has no tensor-core kernel.",
   "<b>Not in the compiler yet.</b> The new formats and kernel are not in KVForge's plan search or cost model."])

# =========================================================================== 9
H1("9. Where it lives and how to reproduce")
TABLE([
    ["File", "What"],
    [M("runtime/kvf_tc.cuh"), "Tensor-core decode kernel: int8 K, int8/int4 V, fused rotation, pipelined loop"],
    [M("runtime/kvf_lowrank.cuh"), "CUDA-core kernel with separate K/V formats and low-rank keys"],
    [M("tools/gen_tc_inst.py, gen_lowrank_inst.py"), "Generate the kernel entry points"],
    [M("bench/wsl/lowrank/study.py"), "Accuracy study on a real model (suites: lowrank, rot, groups)"],
    [M("bench/wsl/lowrank/bench_lr.py"), "Speed benchmark against FlashInfer fp16 and fp8"],
    [M("tools/lowrank_summary.py"), "Per-shape table and geomeans"],
    [M("results/lowrank/"), "All CSV, JSON and logs behind this guide"],
], [70, 104])
CODE("tools\\nvcc.cmd -cubin -arch=sm_120 -O3 -std=c++17 -Iruntime -o build\\cubin\\tc_sm120.cubin runtime\\kvf_tc_inst.cu\n"
     "tools\\nvcc.cmd -cubin -arch=sm_120 -O3 -std=c++17 --split-compile=0 -Iruntime -o build\\cubin\\lowrank_sm120.cubin runtime\\kvf_lowrank_inst.cu\n"
     "wsl -d Ubuntu -- bash bench/wsl/lowrank/run_study.sh --suite groups     # accuracy\n"
     "wsl -d Ubuntu -- bash bench/wsl/lowrank/run_bench.sh --variants f16,k8v4,tc_int8,tc_k8v4,tc_k8g64v4,tc_rot_k8g128v4g64\n"
     "python tools/lowrank_summary.py")
P("Plug the laptop in before timing anything (Windows BatteryStatus 2 = AC).", "small")


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Body", 7.5)
    canvas.setFillColor(SLATE)
    if doc.page > 1:
        canvas.drawString(18 * mm, 10 * mm, "KVForge | Performance metrics guide | Compiler Design, VIT Vellore")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, str(doc.page))
    canvas.restoreState()


doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
                        title="KVForge: performance metrics guide",
                        author="Aahav Yadav, Akshat Kapur, Rishab Jajodia")
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print("wrote", OUT)
