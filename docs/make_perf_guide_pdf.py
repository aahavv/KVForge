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


# progress on the 32k shape: each method's KVForge time next to FlashInfer fp8 from the same run
steps = [("1 baseline\nint8, CUDA cores", 337, 269), ("2 byte-permute\nunpack", 286, 269),
         ("3 batched rescale\n(rank-64 keys)", 256, 267), ("4 int8 K + int4 V\nCUDA cores", 254, 226),
         ("5 tensor cores\nint8 K + int4 V", 196, 216),
         ("6 rotation, groups 128\nfinal run", rows["H32_Hkv8_d128_n32768_b1"][BEST], fi8(rows["H32_Hkv8_d128_n32768_b1"]))]
fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=200)
xs = range(len(steps))
ax.bar([i - 0.19 for i in xs], [k for _, k, _ in steps], width=0.36, color="#0F766E", label="KVForge")
ax.bar([i + 0.19 for i in xs], [f for _, _, f in steps], width=0.36, color="#94A3B8", label="FlashInfer fp8, same run")
for i, (_, k, f) in enumerate(steps):
    ax.text(i - 0.19, k + 4, "%.0f" % k, ha="center", fontsize=7)
    ax.text(i + 0.19, f + 4, "%.0f" % f, ha="center", fontsize=7, color="#475569")
ax.set_xticks(list(xs))
ax.set_xticklabels([n for n, _, _ in steps], fontsize=6.6)
ax.set_ylabel("time per decode step (us)", fontsize=8)
ax.set_ylim(0, 380)
ax.tick_params(axis="y", labelsize=7.5)
ax.legend(fontsize=7, frameon=False, loc="upper right")
ax.set_title("KVForge passes FlashInfer fp8 at method 5 (32k context, 32/8 heads)", fontsize=9, loc="left")
for sp_ in ("top", "right"):
    ax.spines[sp_].set_visible(False)
fig.tight_layout()
fig.savefig(os.path.join(ROOT, "results", "lowrank", "progress_32k.png"))
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
H1("5. The six methods, in detail", new_page=True)
P("Each method below is described the same way: <b>what limited speed at that point</b>, <b>how the method works</b> "
  "(down to the instructions), <b>why it helps</b>, <b>what we measured</b>, and <b>what it cost</b>. All numbers are "
  "for one shape unless stated: 32 query heads, 8 KV heads, head size 128, 32,768 cached tokens, batch 1 "
  "(a Llama-3-8B layer at 32k context).")
BOX("<b>How to read the timings in this chapter.</b> Methods 1 to 5 were measured in single-shape runs while the code "
    "was being developed. The laptop's memory clock was not the same in every run (9001 or 11871 MHz), so a KVForge "
    "time is only meaningful next to the FlashInfer time <b>from the same run</b>, which the tables give. Method 6 is "
    "the final, clean, all-shapes run.", "warn")
FIG("results/lowrank/progress_32k.png", 168,
    "KVForge (teal) against FlashInfer fp8 measured in the same run (grey), after each method. "
    "Lower is better. The gap closes at method 5 and reverses.")

# ---------------------------------------------------------------- method 1
H2("Method 1 - The starting point: a CUDA-core kernel and the bandwidth floor")
P("<b>What the kernel does.</b> One thread block handles one KV head (and, with GQA packing, all G = 4 query heads "
  "that share it) over one chunk of the context. Each token's 128-element row is split over 16 lanes, 8 elements per "
  "lane, so a warp covers 2 tokens per step. Every lane issues the loads for U tokens before using any of them, to "
  "keep bytes in flight. Softmax is online: a running maximum m and running sum l, so scores never leave registers.")
P("<b>How int8 is decoded.</b> A stored element is code x scale + zero, with one (scale, zero) pair per group of "
  "elements. The score needs no per-element dequantization, because the affine map can be pulled out of the sum:")
CODE("q . k  =  sum_i q_i (s c_i + z)  =  s (q . c)  +  z (sum_i q_i)\n"
     "        -> one dot product on the raw codes, then one multiply-add per group")
P("<b>The floor.</b> int8 K and V with groups of 32 is 128 + 16 = 144 bytes per row per tensor: 75.5 MB for this shape. "
  "At the 341 GB/s the probe measured, no kernel can finish in under about 221 us.")
TABLE([["Measured (same run)", "Time", "Note"],
       ["KVForge int8 (CUDA cores)", "337 us", "52% above the bandwidth floor"],
       ["FlashInfer fp8 (tensor cores)", "269 us", "67 MB, near its floor"]], [62, 30, 82])
P("<b>Diagnosis.</b> Cutting the bytes did not cut the time: the same kernel with half-width keys (rank 64) ran almost "
  "as slowly. When fewer bytes do not help, the kernel is limited by instructions, not memory. So the next methods "
  "remove instructions.")

# ---------------------------------------------------------------- method 2
H2("Method 2 - Integer to float without the slow conversion instruction")
P("<b>The bottleneck.</b> The original unpack turned each 8-bit code into a float with a cast:")
CODE("x[i] = (float)((u.x >> (8 * i)) & 0xFF);      // shift, mask, I2F")
P("I2F, the integer-to-float conversion, issues at a quarter of the rate of an FMA on this GPU (16 per clock per SM "
  "instead of 64). With 256 elements per token (K and V) it was a large share of the work.")
P("<b>The trick.</b> A float32 with exponent bits 0x4B is 2<super>23</super> = 8,388,608, and its 23 mantissa bits count in "
  "steps of exactly 1. So if the byte is placed in the low mantissa bits of 0x4B000000, the float's value is "
  "8,388,608 + code, and one subtraction leaves the code, exactly:")
CODE("// __byte_perm(a, b, sel) builds a word from any 4 of the 8 bytes of a and b.\n"
     "// sel = 0x7540 + i:  byte0 <- byte i of u,  byte1 <- 0x00,  byte2 <- 0x00,  byte3 <- 0x4B\n"
     "x[i] = __uint_as_float(__byte_perm(u.x, 0x4B000000u, 0x7540 + i)) - 8388608.f;")
P("<b>Why it helps.</b> PRMT (byte permute) and FADD both issue at full rate, and PRMT also replaces the shift and the "
  "mask. Per 8 elements: 8 PRMT + 8 FADD at full rate, instead of 8 shifts + 8 masks + 8 quarter-rate I2F "
  "(which cost as much issue time as 32 full-rate instructions).")
TABLE([["Measured (same run)", "Before", "After"],
       ["KVForge int8, full width", "337 us", "286 us (-15%)"],
       ["FlashInfer fp8", "269 us", "269 us"]], [62, 50, 62])
P("<b>Cost.</b> None: the result is bit-exact (codes are below 2<super>23</super>). The same trick works for 4-bit codes with a "
  "mask instead of the permute.", "small")

# ---------------------------------------------------------------- method 3
H2("Method 3 - Rescale once per batch of tokens; the zero point as one number")
P("<b>The bottleneck.</b> Online softmax rescales the running output every time the maximum may change. The original "
  "kernel did that per token, per query head, per element, and the int8 zero point added another multiply per element:")
CODE("// per token, per head j, per element i (8 per lane), int8 values:\n"
     "m_new = max(m, s);  alpha = exp2(m - m_new);  p = exp2(s - m_new);\n"
     "acc[j][i] = fma(v[i], p * scale, fma(acc[j][i], alpha, p * zero));   // 2 FMA per element")
P("<b>The change, part 1: rescale once per U tokens.</b> The U scores loaded together are known before any value is "
  "used, so the kernel first takes the maximum over all U of them, computes one alpha, and scales the accumulator once. "
  "Then each token only adds p x v.")
CODE("mx = max(m, s[0], ..., s[U-1]);   alpha = exp2(m - mx);   acc[j][:] *= alpha;   // once per U tokens\n"
     "for u: p = exp2(s[u] - mx);  acc[j][i] = fma(v[i], p * scale, acc[j][i]);    // 1 FMA per element")
P("<b>The change, part 2: the zero point as a scalar.</b> A lane's 8 elements always lie in one quantization group, so "
  "p x zero is the same number for all 8. It is accumulated once per lane (zacc += p x zero) and added back when "
  "the lanes are merged, instead of being added to each of the 8 elements.")
P("<b>Why it helps.</b> Value work per token per head drops from 16 multiply-adds per lane to 8, plus 1 for the zero "
  "point, plus 8/U for the rescale (U = 4: about 11 instead of 16).")
TABLE([["Measured (same run)", "Before", "After"],
       ["KVForge int8, rank-64 keys", "276 us", "256 us (-7%)"],
       ["KVForge int8, full width", "286 us", "290 us (no gain)"],
       ["FlashInfer fp8", "267 us", "267 us"]], [62, 50, 62])
P("<b>What it revealed.</b> The kernel still had a floor near 245 us that did not move with the bytes: rank-32 keys "
  "(47 MB) ran no faster than rank-64 keys (57 MB), at only 192 GB/s. The kernel used 128 registers per thread, so only "
  "16 warps fit on each SM, too few to hide the chains of shuffles in the score reduction.")
P("<b>Tried and rejected: forcing fewer registers.</b> Asking the compiler for at most 85 or 64 registers (to fit 24 or 32 "
  "warps) made it spill registers to memory (up to 1.7 KB of stack per thread); those kernels ran in 8 to 39 ms, "
  "30 to 150 times slower. The real fix had to cut work, not registers: method 5.", "small")

# ---------------------------------------------------------------- method 4
H2("Method 4 - int8 keys, int4 values: spend the bits where the errors hurt")
P("<b>The idea.</b> Store fewer bytes, but not uniformly. The accuracy study on Qwen3-1.7B showed the two halves of "
  "the cache react very differently to rounding:")
TABLE([["Format", "Perplexity", "Bytes per row (K + V)"],
       ["fp16", "%.2f" % ppl(QR, "f16"), "512"],
       ["int8 K + int8 V (groups of 32)", "%.2f" % ppl(QR, "int8:32"), "288"],
       ["int4 K + int4 V", "%.1f (broken)" % ppl(QR, "int4:32"), "160"],
       ["int8 K + int4 V", "%.2f (+%.2f%%)" % (ppl(QG, "K int8:32 V int4:32"), pct(QG, "K int8:32 V int4:32")), "224"]],
      [70, 44, 60])
P("<b>Why keys are sensitive and values are not.</b> A key error delta changes a score by q . delta, and the softmax "
  "<i>exponentiates</i> scores: a score off by 1 multiplies that token's weight by e = 2.7. Real keys also have a few "
  "outlier channels much larger than the rest (the reason int4 keys broke the model while int4 values did not); "
  "with only 16 levels, the step size is set by the outlier and the normal channels lose most of their precision. A value error, by contrast, enters the output "
  "<i>linearly</i>, weighted by p, and independent rounding errors over thousands of tokens largely cancel.")
P("<b>Kernel change.</b> The key and value formats became separate template parameters (KF, VF). int4 values load "
  "4 bytes per lane per token; the 4-bit codes are unpacked with a mask, and the per-group scale and zero work as before.")
TABLE([["Measured (same run)", "Time"],
       ["KVForge int8 K + int8 V", "275 us"],
       ["KVForge int8 K + int4 V", "254 us (-8%; bytes fell 22%)"],
       ["FlashInfer fp8 (tensor cores)", "226 us"]], [80, 94])
P("<b>The lesson.</b> 22% fewer bytes bought only 8%, and FlashInfer was still ahead: on CUDA cores the kernel was still "
  "instruction-bound (method 3's floor). Fewer bytes only pay once the kernel is memory-bound again.")

# ---------------------------------------------------------------- method 5
H2("Method 5 - Tensor cores for the grouped query heads (the big one)")
P("<b>The bottleneck.</b> In the CUDA-core kernel every one of the 16 lanes of a token repeated the softmax and looped "
  "over the 4 query heads: about 100 warp instructions per token. A tensor core does a 16 x 8 x 16 matrix multiply "
  "(4,096 multiply-adds) in one warp instruction, mma.m16n8k16, with fp16 inputs and fp32 accumulation.")
P("<b>The scores.</b> For 8 tokens at a time, S = Q K<super>T</super>: the query heads are the 16 rows (rows 0 to G-1 are "
  "real heads, the rest are zero), the 8 tokens are the columns, and the 128 head dimensions are summed in 8 steps of 16. "
  "16 tokens = 2 column tiles x 8 steps = 16 mma instructions.")
P("<b>The output, transposed.</b> O<super>T</super> = V<super>T</super> P<super>T</super>: head dimensions are the rows "
  "(8 tiles of 16), query heads the 8 columns, tokens the 16-long sum. 16 tokens = 8 mma instructions. The transposition "
  "is the key: after the score mma, each lane holds head g = lane/4 at tokens 2t and 2t+1 (t = lane mod 4), and that "
  "is <i>exactly</i> the register layout the second mma needs for P<super>T</super>. The probabilities never go through shared "
  "memory or shuffles.")
CODE("// score accumulator after mma #1:  lane (g, t) holds  S[head g][token 2t], S[head g][token 2t+1]\n"
     "// P^T operand of mma #2 wants:      lane (g, t) holds  P[token 2t][head g], P[token 2t+1][head g]\n"
     "pb[0] = pack_half2(exp2(s[0][0] - mx), exp2(s[0][1] - mx));   // tokens 2t, 2t+1\n"
     "pb[1] = pack_half2(exp2(s[1][0] - mx), exp2(s[1][1] - mx));   // tokens 2t+8, 2t+9\n"
     "mma16816(o[i], vA[0], vA[1], vA[2], vA[3], pb[0], pb[1]);     // O^T tile i += V^T P^T")
P("<b>Loads made contiguous by permuting dimensions.</b> A dot product does not care about the order of its terms, so "
  "the head dimension is renumbered so that every lane reads one contiguous 16-byte block:")
B(["<b>Keys:</b> lane t of a token reads bytes [16t, 16t + 16) of each 64-dimension chunk; mma step s uses dimensions "
   "64(s/4) + 16t + 4(s mod 4) + {0..3}. The query fragment is built with the same numbering.",
   "<b>Values:</b> lane g reads dimensions [16g, 16g + 16) of tokens 2t, 2t+1, 2t+8, 2t+9. Output row r of tile i is "
   "dimension 16g + i (r = g) or 16g + 8 + i (r = g + 8); the merge writes each value back to its real position."])
P("<b>Dequantization to fp16, two at a time.</b> The fp16 number with bits 0x64XX is 1024 + XX. One byte-permute puts two "
  "codes into such a pair, one subtraction removes the 1024s, and one fused multiply-add applies scale and zero:")
CODE("w2 = (__byte_perm(w, 0, 0x4140) & 0x00FF00FF) | 0x64006400;   // (1024 + c0, 1024 + c1)\n"
     "k2 = __hfma2(__hsub2(w2, 1024.h2), scale.h2, zero.h2);           // (s c0 + z, s c1 + z)\n"
     "// int4 values: even = w & 0x0F0F0F0F, odd = (w >> 4) & 0x0F0F0F0F, then the same path")
P("<b>Why it helps.</b> About 20 warp instructions per token instead of about 100, so the kernel is memory-bound again "
  "and every byte saved now saves time. The 128 x 16 tile of keys is dequantized once and used by all query heads "
  "inside the mma, instead of once per head per lane.")
TABLE([["Measured (same run)", "Time", "Achieved bandwidth"],
       ["KVForge int8 K + int8 V, tensor cores", "240 us", "315 GB/s"],
       ["KVForge int8 K + int4 V, tensor cores", "196 us", "300 GB/s"],
       ["KVForge int8 K + int4 V, CUDA cores", "248 us", "237 GB/s"],
       ["FlashInfer fp8, tensor cores", "216 us", "310 GB/s"]], [80, 30, 64])
P("<b>Correctness.</b> Output error 3.8e-4 against an fp32 reference from the same stored bytes, the same level as "
  "FlashInfer's own fp16 kernel (4e-4): fp16 rounding of the mma inputs, nothing more. <b>Cost:</b> rows G to 15 of the "
  "score tile are padding (75% of the score mma is wasted when G = 4), which is harmless because the tensor cores have "
  "far more throughput than this kernel needs.", "small")

# ---------------------------------------------------------------- method 6
H2("Method 6 - Hadamard rotation, larger groups, fused into the kernel; pipelined loads")
P("<b>The bottleneck.</b> Now memory-bound, every byte counts, and the quantization metadata had become a large share: "
  "a (scale, zero) pair is 4 bytes per group.")
TABLE([["Part", "Groups of 32", "Groups of 64 / 128"],
       ["Key row: 128 int8 codes", "128 + 16 = 144 B (11% metadata)", "128 + 4 = 132 B (group 128)"],
       ["Value row: 128 int4 codes", "64 + 16 = 80 B (20% metadata)", "64 + 8 = 72 B (group 64)"],
       ["Total per row", "224 B", "204 B (-9%)"]], [52, 62, 60])
P("<b>Why bigger groups normally fail.</b> The step size of a group is (max - min) / 255. One outlier channel in a group "
  "of 128 makes the step large for the other 127 channels. Without rotation, int8:128 keys + int4:64 values cost "
  "%+.2f%% perplexity on Qwen3." % pct(QG, "K int8:128 V int4:64"))
P("<b>The rotation.</b> Multiply every query, key and value by H = diag(signs) x Hadamard / sqrt(128), an orthonormal "
  "matrix of +1 and -1 entries. Because H H<super>T</super> = I, scores are unchanged, and the output is rotated back:")
CODE("(q H) . (k H) = q H H^T k^T = q . k                    // scores exactly unchanged\n"
     "sum_t p_t (v_t H) = o H   ->   o = (o H) H^T            // output rotated back after attention")
P("Each rotated coordinate is a +/- mix of all 128 original ones, so an outlier's energy is spread evenly over the "
  "whole row; the groups become flat and the step size small. Result: rotated int8:128 + int4:64 is "
  "%+.2f%% perplexity on Qwen3 and %+.2f%% on TinyLlama (fp8: %+.2f%% and %+.2f%%)."
  % (pct(QG, "rot K int8:128 V int4:64"), pct(TG, "rot K int8:128 V int4:64"), pct(QG, "fp8 (FlashInfer)"), pct(TG, "fp8 (FlashInfer)")))
P("<b>Fused, with no matrix in memory.</b> Multiplying by a Hadamard matrix is a fast Walsh-Hadamard transform: 7 "
  "butterfly stages (log2 128) of additions and subtractions, O(d log d), no 128 x 128 matrix read. The query is rotated "
  "in the attention kernel's prologue in shared memory (G heads x 128 values), and the output is rotated back inside the "
  "split-merge kernel, so there are no extra launches. Keys and values are rotated once, when they are written to the cache.")
CODE("for (h = 1; h < 128; h *= 2)                 // 7 stages, all threads, barrier between stages\n"
     "  for each pair (j, j + h):  (x[j], x[j+h]) = (x[j] + x[j+h], x[j] - x[j+h]);\n"
     "q_rot = fwht(q * signs) / sqrt(128);         // prologue      out = fwht(o) * signs / sqrt(128)   // merge")
P("<b>Pipelined loads.</b> A second loop variant keeps two register sets and issues the next 16-token tile's loads "
  "before computing the current one, so a warp always has memory requests in flight. It costs registers (187 instead "
  "of 127, so fewer warps per SM). The plan search picked it in 6 of 30 cases, mostly short contexts with few splits; "
  "never for the best format. An honest small effect.")
TABLE([["Final run (same run, all methods)", "Time", "vs FlashInfer fp8"],
       ["KVForge int8:32 K + int4:32 V", "%.1f us" % rows["H32_Hkv8_d128_n32768_b1"][SIMPLE], "%.2fx" % (fi8(rows["H32_Hkv8_d128_n32768_b1"]) / rows["H32_Hkv8_d128_n32768_b1"][SIMPLE])],
       ["KVForge rotated int8:128 K + int4:64 V", "%.1f us" % rows["H32_Hkv8_d128_n32768_b1"][BEST], "%.2fx" % (fi8(rows["H32_Hkv8_d128_n32768_b1"]) / rows["H32_Hkv8_d128_n32768_b1"][BEST])],
       ["FlashInfer fp8", "%.1f us" % fi8(rows["H32_Hkv8_d128_n32768_b1"]), "1.00x"],
       ["FlashInfer fp16", "%.1f us" % fi16(rows["H32_Hkv8_d128_n32768_b1"]), "%.2fx" % (fi8(rows["H32_Hkv8_d128_n32768_b1"]) / fi16(rows["H32_Hkv8_d128_n32768_b1"]))]],
      [80, 34, 60])
P("<b>Cost.</b> The rotation needs splits >= 2 (the merge does the inverse rotation) and adds a few microseconds of "
  "prologue per block; on the smallest shapes it is a wash (8k context: 62.1 vs 63.8 us without it). In a full model "
  "the output rotation could instead be folded into the output projection W_O for free.", "small")

H2("The six methods together")
TABLE([["#", "Method", "Removes", "Effect"],
       ["1", "Bandwidth floor analysis", "Nothing: finds the target", "Shows 52% headroom; kernel was instruction-bound"],
       ["2", "Byte-permute int-to-float", "Quarter-rate I2F conversions", "-15% time"],
       ["3", "Batched rescale, scalar zero", "~1/3 of value-side multiply-adds", "-7% time; exposes a 245 us floor"],
       ["4", "int8 K + int4 V", "22% of the bytes, at +0.2% perplexity", "-8% on CUDA cores (still instruction-bound)"],
       ["5", "Tensor cores", "~80% of instructions per token", "Memory-bound: 196 vs 216 us, first win over fp8"],
       ["6", "Rotation + big groups + pipeline", "9% more bytes, at +0.0% perplexity", "1.19x over fp8 across 10 shapes"]],
      [7, 46, 60, 61])

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
