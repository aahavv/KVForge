"""Build "KVForge: how it works, line by line" as a PDF.

    python docs/make_howitworks_pdf.py [output.pdf]

Default output: C:/Users/aahav/Downloads/KVForge_How_It_Works.pdf

Shares the page style and helpers of docs/make_brief_pdf.py (everything above its
title section is executed here). The worked example is a real run of
demo/try_model.ps1 (Qwen2.5-7B shape, n 4096, batch 64, budget 0.2) on the
RTX 5060 Laptop; out/try/H28_4_d128_n4096_b64/ holds its files.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(HERE, "make_brief_pdf.py"), encoding="utf-8").read()
exec(_src.split("# =========================================================================== title")[0])
OUT = sys.argv[1] if len(sys.argv) > 1 else "C:/Users/aahav/Downloads/KVForge_How_It_Works.pdf"


def M(t):
    return "<font face='Mono'>%s</font>" % t


# =========================================================================== title
story.append(Spacer(1, 18 * mm))
P("KVForge: how it works, line by line", "title")
P("The inputs, the ten pipeline stages, why it is a compiler, and every line of a real run explained", "subtitle")
P("Compiler Design, VIT Vellore &nbsp;|&nbsp; Aahav Yadav (24BKT0138), Akshat Kapur (24BDS0318), Rishab Jajodia (24BDS0268) &nbsp;|&nbsp; 16 October 2026", "small")
story.append(Spacer(1, 8))
TABLE([
    ["Part", "What it covers"],
    ["1. The four inputs", "What the compiler is given, and which input depends on the LLM and which on the GPU"],
    ["2. The pipeline, stage by stage", "Lexer to verified kernel, with the real files each stage produces"],
    ["3. Why this is a compiler", "Side-by-side with a classic C compiler"],
    ["4. Reading a run, line by line", "A real run (Qwen2.5-7B, 64 users) with every printed line explained"],
    ["5. What that run tells us", "Ranking right, times wrong by 2.5\u20133\u00d7, and the likely reason"],
    ["6. Glossary", "Every term used, in one place"],
], [56, 118])
BOX("<b>In one paragraph.</b> You describe one attention layer of a model in a 10-line program and leave the decisions you want "
    "made as question marks. The compiler lists every way to fill them, predicts how long each would take on your GPU from "
    "measured hardware numbers, throws out those that are too inaccurate for your budget, keeps the fastest, and writes CUDA code "
    "for it. A test driver then compiles that code, runs it on the GPU, checks the answer against a reference and times it.", "note")

# =========================================================================== 1 inputs
H1("1. The four inputs", new_page=True)
TABLE([
    ["Input", "File", "What it says", "Depends on"],
    ["Program", M("model.kv"), "The model's attention shape (H, H_kv, d), the context length n and batch, which choices are left open (?), and the accuracy budget", "The LLM and your scenario"],
    ["Machine file", M("machines\\rtx5060-laptop.gpu"), "Measured GPU facts: 26 SMs, 341 GB/s, 148 ns latency, 32-byte sector, 65,536 registers per SM, launch cost", "The GPU"],
    ["Register table", M("machines\\resources_sm120.csv"), "Registers each of the 288 kernel variants uses, read from the compiled binary with cuobjdump", "The GPU generation"],
    ["Cost constants", M("model\\constants_rtx5060.cal"), "10 fitted numbers plus the measured error of each lossy format", "Fitted once on the 5060, then frozen"],
], [26, 44, 74, 30])
H2("The model's numbers")
P("The compiler never loads the model's weights or real text. It needs five numbers, three of which come from the model's "
  "published configuration file (config.json on Hugging Face):")
TABLE([
    ["Field", "Meaning", "config.json key", "Llama-3-8B", "Qwen2.5-7B"],
    ["H", "query heads per layer", "num_attention_heads", "32", "28"],
    ["H_kv", "key/value heads per layer", "num_key_value_heads", "8", "4"],
    ["d", "numbers in each key, query or value vector", "head_dim (or hidden_size / H)", "128", "128"],
    ["n", "tokens already in the cache (context length)", "your choice", "e.g. 32768", "e.g. 4096"],
    ["batch", "conversations decoded together", "your choice", "e.g. 1", "e.g. 64"],
], [16, 56, 46, 28, 28])
P("Where to type them: " + M("demo\\try_model.ps1") + " asks for them and writes the .kv file; or write the .kv file yourself. "
  "Limits of what we built: d must be 64 or 128 (each GPU thread takes 8 numbers, so d = 128 uses 16 threads and d = 64 uses 8, "
  "both dividing a 32-thread warp evenly; d = 96 would need 12); query-head packing exists for H / H_kv = 2, 4 or 8.")
H2("The program, field by field")
CODE("""target max_rel_err = 0.2                      # accuracy budget (here: 20%, lets int4 in)

decode model(H: 28, H_kv: 4, d: 128, n: 4096, batch: 64) {
  Q: query<H, d, f32>                          # the new token's queries: H vectors of d floats
  K: kvcache<n, d, ?, ?, ?>                    # keys:   n tokens x d, then format, order, residency
  V: kvcache<n, d, ?, ?, ?>                    # values: same
  O = decode_attn(Q, K, V, scale = auto, splits = ?, gqa_pack = ?)
}""")
TABLE([
    ["Position", "Meaning", "If you write a value", "If you write ?"],
    ["kvcache 3rd field: format", "How each number is stored", "f16, int8:128, int4:64 ...", "Compiler tries f16, int8:64/128, int4:32/64/128 (lossy only with a budget)"],
    ["kvcache 4th: order", "Which data sits next to which in memory", "head_major or token_major", "Compiler tries both"],
    ["kvcache 5th: residency", "One block of memory or pages", "contiguous or paged:16 ...", "Compiler tries contiguous and pages of 16 to 128 tokens"],
    ["splits", "How many pieces each cache scan is cut into", "1, 2, 4 ... 64", "Compiler tries powers of 2 up to 64, dropping pieces shorter than 128 tokens"],
    ["gqa_pack", "One worker per KV head serving all its query heads", "true / false", "Compiler tries both if H / H_kv is 2, 4 or 8"],
    ["scale = auto", "Softmax scale 1/\u221ad", "a number", "\u2014"],
], [34, 46, 38, 56])
P("A question mark is a <b>hole</b>: \u201ccompiler, decide this\u201d. Pinning a value removes that choice from the search. The naive "
  "comparison program pins everything (f16, token_major, contiguous, splits = 1, gqa_pack = false), which is why only 4 "
  "candidates remain for it (2 warp counts \u00d7 2 unroll factors, which are always searched).")

# =========================================================================== 2 pipeline
H1("2. The pipeline, stage by stage", new_page=True)
P("Shown for the Llama-3-8B demo program (" + M("demo\\3_budget.kv") + ": H 32, H_kv 8, d 128, n 32768, batch 1, budget 0.02).")
stages = [
    ("1. Lexer: characters \u2192 tokens",
     "It reads " + M("K: kvcache&lt;n, d, ?, ?, ?&gt;") + " and cuts it into labelled pieces: " + M("K") + ", " + M(":") +
     ", keyword " + M("kvcache") + ", " + M("&lt;") + ", name " + M("n") + ", " + M(",") + " \u2026 and the hole " + M("?") +
     ". This is the same job as in a C compiler. Code: " + M("src/lexer.cpp") + "."),
    ("2. Parser: tokens \u2192 syntax tree",
     "It checks the grammar (a decode block contains declarations, then " + M("decode_attn(...)") + ") and builds a tree: a decode "
     "function with a query Q, caches K and V, and an attention call whose splits and gqa_pack are holes. A missing bracket gives "
     "an error with the line number. Code: " + M("src/parser.cpp") + "."),
    ("3. Semantic checks: is the program meaningful?",
     "Grammatically valid programs can still be nonsense; these checks catch it, and several of the 19 smoke tests check exactly "
     "these errors: 32 query heads must divide evenly over 8 KV heads; the head size must be 64 or 128; an int8 group size must "
     "divide d; K and V must leave the same things open; " + M("target bw_peek_gbs") + " is a typo and is rejected."),
    ("4. IR: one internal form of the program",
     "The tree becomes a small intermediate representation (from " + M("ir.txt") + "). The ? is part of the cache's <b>type</b>: "
     "the program is incomplete, and the next stages complete it."),
]
for t, b in stages:
    H2(t)
    P(b)
CODE("""%K = kvf.kvcache : kvcache<32768x128x?, ?/?>        <- type still has holes
%O = kvf.decode_attn %Q, %K, %V : tensor<32x128xf32> {scale = 0.0883883}""")
H2("5. Enumerate: list every way to fill the holes")
P("6 formats \u00d7 8 layouts \u00d7 7 split counts \u00d7 2 packing choices \u00d7 2 warp counts \u00d7 2 unroll factors = <b>2,688 "
  "candidate plans</b>. Formats: f16; int8 with groups of 64 or 128; int4 with groups of 32, 64 or 128. Layouts: the 8 listed "
  "in part 4. Split counts: 1 to 64. Pinning something in the program shrinks that dimension to one value; with no budget only "
  "f16 is allowed, giving 448. Code: " + M("src/plan.cpp") + ".")
H2("6. Cost model: predict each plan's time without running it")
P("The heart of the project (" + M("src/cost.cpp") + "). For each plan the compiler works out:")
B(["<b>Bytes.</b> For int8:128 the cache payload is 64 MB plus 2 MB of per-group scale factors; each split also writes small "
   "partial results that must be merged.",
   "<b>How fast those bytes can arrive.</b> Splitting 32 ways makes 256 blocks of work across 26 SMs. The register table says how "
   "many blocks fit on one SM at once, which gives how many bytes are being fetched at the same moment. Little's law (bytes in "
   "flight \u00f7 latency) turns that into the bandwidth actually reached, capped at 341 GB/s. Too few splits leave most SMs idle, "
   "which is why splits = 1 is slow for one long conversation.",
   "<b>Arithmetic time.</b> The dot products plus unpacking int8 back to numbers, counted as warp instructions and divided by the "
   "SM's issue rate.",
   "<b>Fixed overheads.</b> Kernel launch, the merge step, page-table lookups.",
   "These combine into one predicted time per plan: 313 \u00b5s for the plan chosen here."])
H2("7. Rank and apply the accuracy gate")
P("Plans are sorted fastest first (a stable sort, so ties keep their listed order). The int4 plans are predicted fastest "
  "(297 \u00b5s), but their recorded error is 14%, above the 2% budget, so the gate rejects them: all 1,344 int4 plans are "
  "marked rejected, and the report keeps them so you can see what the budget cost. The fastest surviving plan wins: int8:128, "
  "head-major, contiguous, split 32, packing on, 8 warps, unroll 4. Code: " + M("src/passes.cpp") + ".")
H2("8. Rewrite the IR: holes become decisions")
P("The pass replaces the operation and fills in the types. The program is now fully specified, like a C compiler turning a "
  "generic operation into a specific one once it knows the types.")
CODE("""%K = kvf.kvcache : kvcache<32768x128xint8:128, head_major/contiguous>
%O = kvf.decode_attn_split %Q, %K, %V {format = int8:128, splits = 32,
      gqa_pack = true, warps = 8, unroll = 4, pred_us = 313.484}""")
H2("9. Code generation: IR \u2192 CUDA")
P("The CUDA is not written instruction by instruction. " + M("runtime/kvf_kernels.cuh") + " holds one kernel <b>template</b> with "
  "switches for format, group size, packing, layout and so on. Code generation (" + M("src/codegen.cpp") + ") emits a short file "
  "that sets those switches (from the real " + M("decode_budget.cu") + "):")
CODE("""a.splits = 32;  a.warps = 8;  a.group_shift = 7;
return kvf::launch<kvf::FMT_INT8, 128, 4, 4, kvf::ORD_HEAD, false>(a, st);""")
H2("10. nvcc, then verify and time")
P("NVIDIA's compiler, nvcc, turns that into GPU machine code; at this point the template is specialised, so everything not "
  "needed for int8 head-major is removed and the constants are folded in. The test driver (" + M("runtime/kvf_driver.cu") + ") "
  "then (1) creates random Q, K and V and stores K and V in int8 head-major form; (2) runs the kernel and compares it with a "
  "double-precision reference: they match to 3.6 \u00d7 10<super>\u22127</super>, so the kernel is correct, and the 0.84% gap to "
  "exact attention is int8's own rounding; (3) times 50 runs and prints measured against predicted: 273 \u00b5s against 313 \u00b5s.")

# =========================================================================== 3 compiler
H1("3. Why this is a compiler", new_page=True)
TABLE([
    ["Classic C compiler", "KVForge"],
    ["Lexer, parser, type checking", "Same: stages 1 to 3"],
    ["Intermediate representation", "Stage 4: an SSA-style IR whose types can contain holes"],
    ["Optimisation passes guided by cost heuristics (inline? unroll?)",
     "Stages 5 to 8: a search pass over plans, an analytic cost model in place of heuristics, an accuracy-gate pass, and an IR rewrite"],
    ["Code generation: instruction selection, register allocation",
     "Stage 9 picks and configures a pre-written template; nvcc then does instruction selection and register allocation"],
], [64, 110])
P("The front end (stages 1 to 4) is a textbook compiler. The research contribution is the middle (stages 5 to 8): deciding "
  "<i>how</i> to run the operation by predicting cost from measured hardware facts instead of timing candidates. The back end is "
  "deliberately thin: KVForge does not write GPU instructions itself, it chooses and configures kernels and lets nvcc do the "
  "low-level code generation. That puts it in the same family as Halide and TVM, which also separate <i>what</i> to compute from "
  "<i>how</i> to schedule it.")
BOX("<b>If asked \u201cis this really a compiler?\u201d:</b> it is a domain-specific compiler whose optimisation pass is a "
    "cost-model-driven search, with nvcc as its back end. It has a language with a grammar and type rules, an IR that is "
    "transformed by passes, and a code generator; what it optimises is the schedule and data representation of one operator, "
    "which is what Halide and TVM optimise too.", "note")

# =========================================================================== 4 run
H1("4. Reading a run, line by line", new_page=True)
P("A real run of " + M("demo\\try_model.ps1") + " on the RTX 5060 Laptop: model qwen2.5-7b, context 4,096 tokens, 64 "
  "conversations at once, budget 0.2. Files: " + M("out\\try\\H28_4_d128_n4096_b64\\") + ".")

RUN = [
    ("One attention layer: H=28 H_kv=4 d=128 n=4096 batch=64  ->  KV cache 512 MB per layer in fp16",
     "Size of what one decode step must read for one layer: K and V (2) \u00d7 4 KV heads \u00d7 128 numbers \u00d7 4,096 tokens "
     "\u00d7 64 conversations \u00d7 2 bytes = 512 MB. Qwen2.5-7B has 28 layers, so the whole model's cache is 14 GB, which is why "
     "only one layer is tested on an 8 GB card."),
    ("target max_rel_err = 0.2",
     "The budget you typed: answers may be up to 20% off exact attention. That admits int4 (measured error 11\u201314%). "
     "0.02 admits int8 only; 0 means fp16 only."),
    ("K: kvcache<n, d, ?, ?, ?>  /  splits = ?, gqa_pack = ?",
     "The holes (part 1). Filled by stages 5 to 8: every combination is listed, predicted, gated, and the fastest survivor's "
     "values are written into the IR."),
    ("Candidates evaluated: 1152",
     "6 formats \u00d7 8 layouts \u00d7 6 split counts \u00d7 1 packing choice \u00d7 2 warp counts \u00d7 2 unroll factors. "
     "Split 64 was dropped because 4,096 \u00f7 64 = 64 tokens per piece, below the 128-token minimum. Packing is impossible "
     "because 28 \u00f7 4 = 7 query heads per KV head and kernels exist for groups of 2, 4 and 8 only."),
    ("format: int4:128 (4.25 bits/element)",
     "Each number stored in 4 bits; every group of 128 numbers carries a 16-bit scale and a 16-bit zero point, adding "
     "32 \u00f7 128 = 0.25 bits per number. Chosen because it moves the fewest bytes and passes the 0.2 budget."),
    ("layout: head_major/contiguous",
     "How the cache is arranged in memory (all 8 options below). Chosen because it had the lowest predicted time, but only "
     "barely: the 8 layouts predicted 3,024 to 3,069 \u00b5s, a 1.5% spread. Layout hardly matters on these GPUs, which our sweep "
     "also measured."),
    ("partition: splits=1 w4 u2",
     "How the work is cut up. splits = 1: each cache scan is done by one block, unsplit (1,792 blocks already keep all 26 SMs "
     "busy, so splitting would only add merge work). No \u201cpack\u201d: each query head gets its own block. w4: 4 warps "
     "(4 \u00d7 32 = 128 threads) per block. u2: each thread keeps 2 loads in flight per loop step (unroll). Warps and unroll tied "
     "on predicted time; the stable sort kept the first listed."),
    ("blocks = 1792   active SMs = 26",
     "Blocks = query heads (no packing) \u00d7 conversations \u00d7 splits = 28 \u00d7 64 \u00d7 1 = 1,792 independent pieces "
     "of work. The GPU has 26 SMs, so all 26 are busy, several blocks each, in waves."),
    ("accuracy: calibrated relative error 0.143969",
     "Not computed for this run: it is the median error int4:128 showed across the 5060 sweep (random test data), stored in "
     "the constants file and used by the accuracy gate. 0.144 \u2264 0.2, so int4 passed."),
    ("T_total 3024.16 us (compute bound)",
     "The model's prediction for this plan. It estimated memory time 1,127 \u00b5s and arithmetic time 2,994 \u00b5s; the "
     "larger one names the bound. int4 is compute bound here because every one of the 7 query heads unpacks the same 4-bit "
     "data separately."),
    ("built ...\\pick\\bench.exe",
     "nvcc compiled the generated decode_model.cu with the test driver into a program."),
    ("device / plan",
     "Which GPU ran it, and the plan the program was built with, to confirm compiler and program agree."),
    ("check: relative error vs dequantised reference 6.44e-07 (PASS)",
     "Correctness of the kernel. The CPU computes attention in double precision on the <i>same</i> int4-rounded data; the GPU "
     "result differs by 0.00006%, ordinary floating-point noise. The kernel computes exactly what int4 attention should."),
    ("accuracy: relative error vs exact fp32 attention 0.143",
     "Cost of the format. The same comparison against attention on the original, unrounded numbers: 14.3% off, matching "
     "the 0.144 the gate used. For fp16 this is 0.03%."),
    ("time: 7657.79 us median (IQR 7622.78..7676.48, 50 reps)",
     "Measured on the GPU: 50 runs, each preceded by writing a 96 MB buffer so the cache cannot be served from the on-chip L2 "
     "left over from the previous run, timed with CUDA events. Median is the middle run; IQR is the range of the middle half "
     "(25th to 75th percentile). A narrow IQR means a stable measurement."),
    ("rate: 18.6 GB/s of KV payload",
     "Payload bytes \u00f7 time: the int4 cache is 512 MB \u00d7 4.25 \u00f7 16 = 136 MB; 136 MB in 7.66 ms = 18.6 GB/s. "
     "It counts each cache byte once, so it is low when the kernel reads bytes more than once or is busy computing."),
    ("predicted 3024.16 us, measured 7657.79 us (ratio 2.53)",
     "Measured \u00f7 predicted. 1.0 is perfect; on the shapes the model was fitted and tested on, the average gap is about 15%. "
     "2.53 is a large miss, explained in part 5."),
    ("naive kernel: Candidates evaluated: 4 ... f16 token_major/contiguous splits=1 w4 u2",
     "The comparison program pins format, layout, splits and packing, so only warps \u00d7 unroll (2 \u00d7 2) remain."),
    ("naive: time 13067.30 us, rate 41.1 GB/s, ratio 3.12",
     "The naive kernel: 13.1 ms. KVForge's pick is 13,067 \u00f7 7,658 = <b>1.71\u00d7 faster</b>, but at 14% error, which "
     "you allowed with the budget."),
]
rows = [["Printed line", "What it means and where the value comes from"]]
for a, b in RUN:
    rows.append([M(a.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")), b])
data = []
for i, r in enumerate(rows):
    data.append([Paragraph(r[0], S["cellh"] if i == 0 else ParagraphStyle("mc", parent=S["cell"], fontName="Mono", fontSize=7.4, leading=9.6)),
                 Paragraph(r[1], S["cellh"] if i == 0 else S["cell"])])
t = Table(data, colWidths=[64 * mm, 110 * mm], repeatRows=1)
t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, GRID), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                       ("BACKGROUND", (0, 0), (-1, 0), INK), ("BACKGROUND", (0, 1), (0, -1), PALE),
                       ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                       ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
story.append(t)
story.append(Spacer(1, 8))

H2("The layout options")
P("Layout decides which numbers sit next to each other in memory. A GPU fetches memory in 32-byte pieces, so what is adjacent "
  "decides how many fetched bytes are useful. One <i>row</i> below is one token's d numbers for one KV head.")
TABLE([
    ["Option", "Arrangement", "What a block scanning one KV head sees"],
    ["head_major / contiguous", "conversation \u2192 KV head \u2192 token \u2192 d numbers", "One long unbroken run: all tokens of its head are adjacent"],
    ["token_major / contiguous", "conversation \u2192 token \u2192 KV head \u2192 d numbers", "Runs of one row (256 bytes in fp16), then a jump past the other heads' rows"],
    ["head_major / paged:16, 32, 64, 128", "Cache cut into pages of 16\u2013128 tokens, placed anywhere in memory, found through a page table (as vLLM does); head-major inside a page",
     "A run as long as the page, then a page-table lookup (one extra dependent memory read) before the next page"],
    ["token_major / paged:16, 64", "Same pages, token-major inside a page", "Short runs and page lookups"],
], [40, 66, 68])
P("<b>Basis of the choice:</b> the same as everything else, the lowest predicted time. The cost model charges layouts for short "
  "runs and for page lookups (22 ns each, a fitted constant). Its short-run penalty was fitted to almost nothing, because the "
  "measurements showed layout costs at most 8%; page lookups are what separates them, so contiguous layouts usually win. Paged "
  "layouts exist because real serving systems use them to share GPU memory among many conversations; the compiler shows what "
  "that costs.")

H2("Partition terms")
TABLE([
    ["Term", "Meaning", "Options searched"],
    ["splits", "Cut each conversation's token range into pieces handled by separate blocks, then merge the partial results with a small second kernel. More pieces = more SMs busy for one long conversation, but more merge work.", "1, 2, 4 ... 64 (pieces \u2265 128 tokens)"],
    ["gqa_pack", "One block serves all query heads that share a KV head, reading that KV head once instead of once per query head. Needs more registers.", "on/off, if H/H_kv is 2, 4, 8"],
    ["warps", "A warp is 32 GPU threads that execute together. More warps per block = more loads in flight, more registers used.", "4 or 8"],
    ["unroll", "How many loads each thread issues before waiting for the first. Higher = more bytes in flight per thread.", "2 or 4"],
    ["block", "One independent piece of work given to one SM. An SM runs several blocks at once if registers allow.", "follows from the above"],
    ["SM", "Streaming multiprocessor: one of the GPU's 26 cores, each running many threads.", "fixed by the GPU"],
], [22, 112, 40])

# =========================================================================== 5 lessons
H1("5. What that run tells us")
TABLE([
    ["", "Predicted", "Measured"],
    ["KVForge pick (int4)", "3,024 \u00b5s", "7,658 \u00b5s"],
    ["Naive kernel (fp16)", "4,191 \u00b5s", "13,067 \u00b5s"],
    ["Speedup of the pick", "1.39\u00d7", "1.71\u00d7"],
], [60, 57, 57])
B(["<b>The ranking was right:</b> the plan the model called faster was faster, by more than it predicted.",
   "<b>The times were wrong by 2.5\u20133.1\u00d7.</b> Both kernels took far longer than predicted.",
   "<b>Most likely reason (consistent with the arithmetic, not proven):</b> with no packing, each of the 7 query heads that share "
   "a KV head reads that KV head separately. For the naive kernel that is 512 MB \u00d7 7 = 3.76 GB per step; 3.76 GB in 13.07 ms "
   "is 288 GB/s, close to the card's 341 GB/s limit. So the kernel was streaming at near full speed but reading the cache 7 "
   "times. The model assumes about 74% of those repeat reads come from the on-chip L2 cache (the fitted constant "
   "unpack_l2_hit); with 1,792 blocks in flight they evidently do not.",
   "<b>The shape is outside what the model was fitted on:</b> the sweep's largest batch was 8 and its groups were 1, 4 and 8 "
   "query heads per KV head. Batch 64 with a group of 7 is new territory.",
   "<b>The budget is the user's decision:</b> 0.2 let in 14% error. With 0.02 the compiler would have chosen int8 (about 0.8% "
   "error)."])
BOX("<b>How to say it:</b> \u201cOn shapes like the ones we fitted on, predictions are within about 15%; here, at 64 users and a "
    "head ratio we never measured, the times are off by 2.5\u00d7, but the plan it picked was still the faster one. Modelling "
    "repeated reads at large batch is the fix.\u201d", "callout")

# =========================================================================== 6 glossary
H1("6. Glossary")
TABLE([
    ["Term", "Meaning"],
    ["KV cache", "Stored key and value vectors of every earlier token, read in full at every decode step"],
    ["Decode step", "Producing one new token; reads the whole cache once"],
    ["Query / key / value", "Per-token vectors: what a token looks for / what it offers to be matched on / what it passes on"],
    ["Head", "One of several parallel attention computations in a layer, each with its own vectors"],
    ["GQA", "Grouped-query attention: several query heads share one KV head, shrinking the cache"],
    ["d (head_dim)", "Length of each query, key and value vector"],
    ["f16 / int8 / int4", "16-, 8- or 4-bit storage per number; lower bits = fewer bytes, more rounding error"],
    ["Group (int8:128)", "Numbers sharing one scale and zero point; 128 numbers per group here"],
    ["Hole (?)", "A choice the program leaves to the compiler"],
    ["Plan / candidate", "One complete set of choices: format, layout, splits, packing, warps, unroll"],
    ["Cost model", "Formula predicting a plan's time from bytes, bandwidth, latency, registers and instruction counts"],
    ["Accuracy gate", "Pass that rejects plans whose format error exceeds the budget"],
    ["Memory / compute bound", "Whether waiting for memory or doing arithmetic takes longer"],
    ["Little's law", "Bandwidth reached = bytes in flight \u00f7 latency"],
    ["Register", "Fastest per-thread storage; 65,536 per SM, shared by all its threads"],
    ["L2 cache", "32 MB on-chip memory shared by all SMs; much faster than the main 8 GB memory"],
    ["IR", "Intermediate representation: the compiler's internal form of the program"],
    ["nvcc", "NVIDIA's CUDA compiler; the back end that produces GPU machine code"],
    ["Regret", "How much slower the chosen plan is than the best plan found by measuring all of them"],
], [40, 134])


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Body", 7.5)
    canvas.setFillColor(SLATE)
    if doc.page > 1:
        canvas.drawString(18 * mm, 10 * mm, "KVForge | How it works | Compiler Design, VIT Vellore")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, str(doc.page))
    canvas.restoreState()


doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
                        title="KVForge: how it works, line by line", author="Aahav Yadav, Akshat Kapur, Rishab Jajodia")
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print("wrote", OUT)
