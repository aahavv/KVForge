"""Build "KVForge: the complete guide" as a PDF: the one document to refer to.

    python docs/make_complete_guide_pdf.py [output.pdf]

Default output: C:/Users/aahav/Downloads/KVForge_Complete_Guide.pdf

Merges and extends the project brief and "how it works": background, claims, the
inputs (given and collected), every machine-file key, the register table, every
cost constant, the cost model with a worked example that reproduces the compiler's
own numbers, the compiler pipeline and why it is a compiler, every output file,
and the Qwen2.5-7B run line by line. Shares the page style of make_brief_pdf.py.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(HERE, "make_brief_pdf.py"), encoding="utf-8").read()
exec(_src.split("# =========================================================================== title")[0])
OUT = sys.argv[1] if len(sys.argv) > 1 else "C:/Users/aahav/Downloads/KVForge_Complete_Guide.pdf"

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String  # noqa: E402

INDIGO = colors.HexColor("#4F46E5")
INDIGO_L = colors.HexColor("#E0E7FF")
AMBER = colors.HexColor("#F59E0B")
ROSE = colors.HexColor("#BE123C")


def M(t):
    return "<font face='Mono'>%s</font>" % t


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def H3(t):
    story.append(Paragraph(t, ParagraphStyle("h3", parent=S["body"], fontName="Body-Bold", spaceBefore=6, spaceAfter=2)))


def LINES(rows, w0=64, w1=110):
    """Two-column table: monospace left (a printed line or key), prose right."""
    mono = ParagraphStyle("mc", parent=S["cell"], fontName="Mono", fontSize=7.4, leading=9.6)
    data = []
    for i, r in enumerate(rows):
        if i == 0:
            data.append([Paragraph(r[0], S["cellh"]), Paragraph(r[1], S["cellh"])])
        else:
            data.append([Paragraph(esc(r[0]), mono), Paragraph(r[1], S["cell"])])
    t = Table(data, colWidths=[w0 * mm, w1 * mm], repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, GRID), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("BACKGROUND", (0, 0), (-1, 0), INK), ("BACKGROUND", (0, 1), (0, -1), PALE),
                           ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                           ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story.append(t)
    story.append(Spacer(1, 8))


# ------------------------------------------------------------------ flow diagram
def flow_diagram():
    W, Hh = 174 * mm, 118 * mm
    d = Drawing(W, Hh)

    def box(x, y, w, h, fill, title, lines, tcol=colors.white, lcol=None):
        d.add(Rect(x * mm, y * mm, w * mm, h * mm, fillColor=fill, strokeColor=None, rx=4, ry=4))
        d.add(String((x + 3) * mm, (y + h - 6) * mm, title, fontName="Body-Bold", fontSize=8.6, fillColor=tcol))
        for i, ln in enumerate(lines):
            d.add(String((x + 3) * mm, (y + h - 11 - i * 4.1) * mm, ln, fontName="Body", fontSize=7, fillColor=lcol or tcol))

    def arrow(x1, y1, x2, y2, col=SLATE):
        d.add(Line(x1 * mm, y1 * mm, x2 * mm, y2 * mm, strokeColor=col, strokeWidth=1.2))
        import math
        a = math.atan2(y2 - y1, x2 - x1)
        p = [x2 * mm, y2 * mm,
             (x2 - 2.6 * math.cos(a - 0.45)) * mm, (y2 - 2.6 * math.sin(a - 0.45)) * mm,
             (x2 - 2.6 * math.cos(a + 0.45)) * mm, (y2 - 2.6 * math.sin(a + 0.45)) * mm]
        d.add(Polygon(p, fillColor=col, strokeColor=None))

    # row 1: the three input sources
    box(0, 88, 54, 30, TEAL, "A. YOU GIVE (per model)", ["model.kv program:", "H, H_kv, d  (from config.json)",
                                                       "n (context), batch (users)", "? holes + accuracy budget"])
    box(60, 88, 54, 30, INDIGO, "B. TOOLS COLLECT (per GPU)", ["bw_probe.exe -> machine file:", "bandwidth, latency, SMs, launch",
                                                             "dump_resources.py -> register", "table of the 288 kernels"])
    box(120, 88, 54, 30, AMBER, "C. FITTED ONCE (frozen)", ["sweep.exe timed 20,928 plans", "kvf calibrate fitted 10", "constants + format errors",
                                                          "-> constants_rtx5060.cal"], tcol=INK)
    for x in (27, 87, 147):
        arrow(x, 88, 87 if x != 87 else 87, 80)
    # row 2: the compiler
    box(0, 44, 174, 35, PALE, "kvf.exe plan  -  THE COMPILER (no GPU needed)", [
        "front end:   lexer -> parser -> semantic checks -> IR with holes (kvf.decode_attn)",
        "middle:      enumerate every plan -> cost model predicts each plan's time from A + B + C",
        "             -> accuracy gate removes formats over budget -> fastest survivor chosen",
        "             -> IR rewritten (kvf.decode_attn_split, holes filled)",
        "back end:    CUDA source that configures the kernel template"], tcol=INK)
    arrow(87, 44, 87, 36)
    # row 3: outputs
    box(0, 0, 84, 35, GREEN, "OUTPUT 1: files from kvf.exe", ["report.txt  - the reasoning, predicted cost",
                                                           "plans.csv   - every candidate, predicted",
                                                           "ir.txt      - program before/after planning",
                                                           "decode_model.cu, plan_info.h - the CUDA"])
    box(90, 0, 84, 35, ROSE, "OUTPUT 2: build_plan.ps1 -> bench.exe", ["nvcc compiles the CUDA + test driver",
                                                                    "runs on the GPU with random data",
                                                                    "check vs reference (PASS/FAIL)",
                                                                    "time, rate, predicted vs measured"])
    arrow(60, 36, 42, 35.5)
    arrow(114, 36, 132, 35.5)
    return d


# =========================================================================== title
story.append(Spacer(1, 14 * mm))
P("KVForge: the complete guide", "title")
P("What the project is, what it claims, what goes in, what the tools collect, how it is processed, why it is a compiler, "
  "what comes out, and a real run explained line by line", "subtitle")
P("Compiler Design, VIT Vellore &nbsp;|&nbsp; Aahav Yadav (24BKT0138), Akshat Kapur (24BDS0318), Rishab Jajodia (24BDS0268) "
  "&nbsp;|&nbsp; 16 October 2026", "small")
story.append(Spacer(1, 6))
BOX("<b>This is the one document to refer to.</b> It replaces the separate explanations given so far. Every number in it was "
    "measured on our hardware or printed by our programs; where something is an explanation we believe but have not proven, it "
    "says so. Read parts 1 to 3 for the idea, 4 to 8 for the mechanism from input to output, 9 and 10 for your own run.", "note")
TABLE([
    ["Part", "Contents"],
    ["1. Background from zero", "Attention, the KV cache, the decode step, and the GPU words used everywhere else"],
    ["2. What KVForge is", "The problem, the three levers, the idea in one paragraph"],
    ["3. Our claims", "What we claim with evidence, and what we do not claim"],
    ["4. Input A: what you give", "The .kv program, every field, the holes, the budget, where to type it"],
    ["5. Input B and C: what the tools collect", "bw_probe and every machine-file line; the register table and the 288 kernels; the 10 cost constants and how they were fitted"],
    ["6. Processing: the ten stages", "Lexer to verified kernel, with the cost model worked through by hand"],
    ["7. Why this is a compiler", "Side by side with a C compiler, and how to answer the question"],
    ["8. The output", "Every file produced and every column in it"],
    ["9. Your Qwen2.5-7B run, line by line", "Every printed line explained"],
    ["10. What that run tells us", "Ranking right, times off by 2.5 to 3.1 times, and the reason"],
    ["11. Results of the whole project", "Measured findings and limits"],
    ["12. Running it yourself", "Every command"],
    ["13. Questions you may be asked", "Short answers"],
    ["14. Glossary", "Every term"],
], [52, 122])
H2("The whole system on one page")
FIG_D = flow_diagram()
story.append(KeepTogether([FIG_D, Paragraph("Figure 1. Three input sources (A changes per model, B per GPU, C never), one compiler, two kinds of output.", S["caption"])]))

# =========================================================================== 1 background
H1("1. Background from zero", new_page=True)
H2("Attention and the KV cache")
P("A language model reads and writes text as <b>tokens</b> (word pieces). Inside each of its layers, attention lets every token "
  "look back at the earlier ones. For that, each token produces three vectors of numbers per <b>head</b> (a head is one of "
  "several parallel attention computations in a layer):")
B(["<b>Query (q)</b>: what this token is looking for.",
   "<b>Key (k)</b>: what this token offers to be matched against.",
   "<b>Value (v)</b>: the information this token passes on if someone attends to it."])
P("Example: the prompt <i>What is the capital of France?</i> (about 7 tokens) is answered <i>The capital of France is "
  "Paris</i>. While reading the prompt (the <b>prefill</b> phase, all prompt tokens at once), every token in every layer "
  "computes its k and v, and they are stored. That store, one table per layer of all earlier tokens' keys and values, is the "
  "<b>KV cache</b>.")
P("Then the answer is generated one token at a time (the <b>decode</b> phase). To produce <i>The</i>, the newest position "
  "computes a query, takes its dot product with every stored key (how relevant is each earlier token?), turns those scores into "
  "weights with softmax (they add up to 1), and adds up the stored values with those weights. Its own k and v are appended to "
  "the cache. To produce <i>capital</i>, the same happens over one more entry, and so on until <i>Paris</i>, whose query "
  "looks back over all 12 earlier tokens.")
BOX("<b>The key fact:</b> every decode step reads the <b>whole</b> cache once, and uses each byte for only one or two "
    "arithmetic operations before moving on. The cache is kept because the alternative, recomputing every earlier token's k "
    "and v at every step, is far more work.", "callout")
H2("How big the cache gets, and why reading it is the bottleneck")
P("Llama-3-8B stores, per token and per layer: K and V (2) \u00d7 8 KV heads \u00d7 128 numbers \u00d7 2 bytes = 4 KB; over 32 "
  "layers, 128 KB per token. At 32,768 tokens that is 4 GB for one conversation, 128 MB per layer per step. The GPU reads "
  "memory at 341 GB/s (measured), so one layer's read alone takes about 0.4 ms. The arithmetic on those bytes is small: about 4 "
  "operations per byte, while our GPU can do about 47 per byte before memory stops being the limit. So decode attention is "
  "<b>memory bound</b>: its time is set by how many bytes it reads and how well it keeps the memory system busy.")
P("Model weights are also read every step (about 16 GB for an 8B model in fp16), but they are shared by all conversations in "
  "a batch, while each conversation has its own cache. With long contexts or many users the cache dominates. That is why we "
  "optimise only this operator.")
H2("GPU words used in this document")
TABLE([
    ["Word", "Meaning", "On the RTX 5060 Laptop"],
    ["DRAM / GPU memory", "The main memory on the card; large and slow compared to on-chip storage", "8.5 GB, 341 GB/s read"],
    ["Bandwidth", "Bytes per second that can be read", "341 GB/s whole GPU, 79 GB/s one SM"],
    ["Latency", "Time from asking for data to receiving it", "148 ns when idle"],
    ["SM (streaming multiprocessor)", "One of the GPU's cores; each runs many threads at once", "26 SMs"],
    ["Thread", "One sequence of instructions; thousands run at once", "\u2014"],
    ["Warp", "32 threads that execute the same instruction together", "up to 48 warps per SM"],
    ["Block", "A group of warps given to one SM as one piece of work", "up to 24 blocks per SM"],
    ["Register", "The fastest storage, private to a thread; a fixed pool per SM shared by all its threads", "65,536 per SM"],
    ["L2 cache", "On-chip memory shared by all SMs, between them and DRAM", "32 MB, 1,581 GB/s"],
    ["Sector", "The smallest piece the memory system fetches", "32 bytes"],
    ["Kernel / launch", "A GPU function, and the act of starting it from the CPU", "20.8 \u00b5s per launch (Windows)"],
    ["Bytes in flight", "Data requested but not yet arrived; more in flight = more bandwidth, up to the limit", "\u2014"],
    ["Little's law", "Bandwidth reached = bytes in flight \u00f7 latency", "\u2014"],
    ["Occupancy", "How many warps an SM holds at once; limited by registers, warp slots and block slots", "\u2014"],
], [36, 92, 46])

# =========================================================================== 2 what
H1("2. What KVForge is")
BOX("You describe one attention layer of a model in a 10-line program and leave the decisions you want made as question marks. "
    "KVForge lists every way to fill them, predicts how long each would take on your GPU from measured hardware numbers, throws "
    "out the ones that are too inaccurate for your budget, keeps the fastest, and writes CUDA code for it. A test driver then "
    "compiles that code, runs it on the GPU, checks the answer against a reference and times it.", "note")
H2("The problem")
P("There are thousands of ways to run decode attention: how each number is stored, how the cache is arranged in memory, and how "
  "the work is divided across the GPU. The fastest depends on the model's shape, the context length, the number of users and the "
  "GPU. Today engineers pick by hand (libraries such as FlashInfer) or by timing hundreds of candidates on every GPU "
  "(autotuning). Classic compiler cost models do not help: they score a schedule by how much data it reuses from fast memory, "
  "and in decode every byte is used once (<b>reuse = 1</b>) for every schedule, so they rate all schedules the same. Yet we "
  "measured up to 6.4\u00d7 difference between plans that read exactly the same bytes.")
H2("The three levers")
TABLE([
    ["Lever (axis)", "Choices", "What it changes", "Measured effect"],
    ["Representation (format)", "f16; int8 or int4 with groups of 32/64/128", "Bytes per number: fewer bytes, less to read, some rounding error",
     "Best lossy format vs fp16: 1.8\u00d7 (median); the demo's 3.09\u00d7"],
    ["Partition", "split count, GQA packing, warps, unroll", "How many SMs are busy, how many bytes are in flight, whether shared KV heads are read once",
     "Wrong split count: up to 58% slower; packing off: 40%; demo's 1.96\u00d7"],
    ["Placement (layout)", "head- or token-major; contiguous or paged", "How many fetched bytes are useful",
     "At most 8%: barely matters on these GPUs (a negative finding)"],
], [32, 42, 54, 46])
P("The goal is one number: the shortest time per decode step that stays within your accuracy budget. The three levers are what "
  "move it.")

# =========================================================================== 3 claims
H1("3. Our claims")
H2("What we claim, with the evidence")
TABLE([
    ["#", "Claim", "Evidence (measured)"],
    ["1", "Plans that read the same bytes differ greatly in speed, so a reuse-based model cannot choose among them (hypothesis H1)",
     "1.8\u00d7 to 6.4\u00d7 spread among fp16 plans on the RTX 5060; 1.1\u00d7 to 4.6\u00d7 on the RTX 4060"],
    ["2", "A bandwidth model built from measured hardware numbers ranks plans well without running them",
     "Rank correlation 0.88 on three shapes held out from fitting; time error 15%"],
    ["3", "The compiler's choice is much faster than a straightforward kernel",
     "1.93\u00d7 (fp16 only), 3.00\u00d7 (int8 allowed), 3.64\u00d7 (int4 allowed), averaged over 10 shapes; live demo 1.96\u00d7 and 3.09\u00d7"],
    ["4", "It is competitive with an expert-tuned library", "Its pick takes 1.06\u00d7 FlashInfer's time on average (0.94\u00d7 to 1.33\u00d7), fp16"],
    ["5", "The model transfers to a different GPU generation without retuning",
     "RTX 4060 with constants fitted on the 5060: rank correlation 0.886, regret 6.6% fp16, 11.8% int8, 16.1% all formats"],
    ["6", "The compiler emits correct code", "44,224 runs checked against a double-precision reference, none failed"],
], [8, 80, 86])
H2("What we do not claim")
B(["We are <b>not</b> faster than FlashInfer: 6% slower on average, 33% slower on one shape.",
   "We have tested <b>two laptop GPUs</b> only (Blackwell RTX 5060, Ada RTX 4060), not server GPUs.",
   "int8 and int4 error was measured on <b>random test data</b>, not on a real model's text output.",
   "Predictions are good on shapes like those we fitted on; on shapes far outside them (part 10) the times can be off by 2.5\u00d7 or more, even when the ranking is still right.",
   "Novelty is moderate: each ingredient exists separately; the combination, the accuracy budget in the language, and the transfer test are ours."])

# =========================================================================== 4 input A
H1("4. Input A: what you give (the program)", new_page=True)
P("The compiler never loads a model's weights or any real text. It needs only the shape of one attention layer and your "
  "scenario. Three numbers come from the model's published " + M("config.json") + " (for example on Hugging Face); two are your choice.")
TABLE([
    ["Field", "Meaning", "Where it comes from", "Llama-3-8B", "Qwen2.5-7B"],
    ["H", "query heads per layer", "num_attention_heads", "32", "28"],
    ["H_kv", "key/value heads per layer", "num_key_value_heads", "8", "4"],
    ["d", "numbers in each query, key or value vector", "head_dim, or hidden_size \u00f7 H", "128", "128"],
    ["n", "tokens already in the cache (context length)", "your scenario", "e.g. 32,768", "e.g. 4,096"],
    ["batch", "conversations decoded together (users)", "your scenario", "e.g. 1", "e.g. 64"],
    ["budget", "how far from exact attention the answer may be", "your decision", "0.02", "0.2"],
], [15, 50, 43, 33, 33])
H2("The program, field by field")
CODE("""target max_rel_err = 0.2                      # accuracy budget: answers may be up to 20% off

decode model(H: 28, H_kv: 4, d: 128, n: 4096, batch: 64) {    # the layer's shape and scenario
  Q: query<H, d, f32>                          # the new token's queries: H vectors of d 32-bit floats
  K: kvcache<n, d, ?, ?, ?>                    # keys: n tokens x d numbers; then format, order, residency
  V: kvcache<n, d, ?, ?, ?>                    # values: same
  O = decode_attn(Q, K, V, scale = auto, splits = ?, gqa_pack = ?)   # the operation, with two more holes
}""")
TABLE([
    ["Position", "Meaning", "If you write a value", "If you write ? (a hole)"],
    ["kvcache field 3: format", "How each number is stored", "f16, int8:128, int4:64 ...", "Compiler tries f16, int8:64, int8:128, int4:32, int4:64, int4:128 (lossy ones only if a budget is given)"],
    ["kvcache field 4: order", "Which data sits next to which", "head_major or token_major", "Compiler tries both"],
    ["kvcache field 5: residency", "One block of memory, or pages", "contiguous or paged:16 ...", "Compiler tries contiguous and the paged sizes (part 6, stage 5)"],
    ["splits", "Into how many pieces each cache scan is cut", "1, 2, 4 ... 64", "Powers of 2 up to 64, dropping pieces shorter than 128 tokens"],
    ["gqa_pack", "One block per KV head serving all its query heads", "true or false", "Both, if H \u00f7 H_kv is 2, 4 or 8; otherwise false only"],
    ["scale = auto", "The softmax scale 1/\u221ad", "a number", "\u2014 (auto computes it)"],
], [32, 40, 34, 68])
P("A question mark is a <b>hole</b>: \u201ccompiler, decide this\u201d. Writing a value <b>pins</b> that choice and removes it from "
  "the search. Two choices, warps (4 or 8) and unroll (2 or 4), are always searched and have no field. The budget line is "
  "optional: without it only lossless f16 is searched.")
H2("Where you type it")
B([M("demo\\try_model.ps1") + " asks the questions (model name from a list, or custom H, H_kv, d; then n, batch, budget) and writes "
   "the program for you into " + M("out\\try\\&lt;shape&gt;\\pick\\model.kv") + ". It also writes a second program with everything "
   "pinned (the naive kernel) for comparison.",
   "Or write a .kv file yourself in Notepad and run " + M("kvf plan") + " on it (part 12).",
   M("demo\\run_demo.ps1") + " asks nothing: its three programs (" + M("demo\\1_baseline.kv, 2_lossless.kv, 3_budget.kv") + ") "
   "already contain Llama-3-8B's numbers."])
H2("Limits of what we built")
B(["<b>d must be 64 or 128.</b> In our kernel each thread takes 8 numbers of a vector, so d = 128 uses 16 threads and d = 64 "
   "uses 8, both dividing a 32-thread warp evenly. d = 96 (Phi-3) would need 12 and is rejected; d = 256 (Gemma) would fit but "
   "was never built or tested. A limit of our kernels, not of the idea.",
   "<b>Packing needs H \u00f7 H_kv = 2, 4 or 8.</b> Qwen2.5-7B has 7, so the compiler searches without packing.",
   "<b>Group size</b> must be 32, 64 or 128 and divide d. <b>Page sizes</b> are 16, 32, 64 or 128 tokens.",
   M("try_model.ps1") + " refuses caches over 2 GB per layer, because the test data must fit in the 8 GB card."])

# =========================================================================== 5 input B and C
H1("5. Inputs B and C: what the tools collect by themselves", new_page=True)
TABLE([
    ["Program", "What it produces", "When it runs", "Needs a GPU?", "Used by"],
    ["bw_probe.exe", "Machine file " + M("machines\\*.gpu") + ": measured GPU numbers", "Once per GPU (about a minute)", "Yes", "kvf.exe (input B)"],
    ["dump_resources.py", "Register table " + M("resources_sm*.csv"), "Once per GPU generation, after building the kernels", "No (needs the CUDA toolkit)", "kvf.exe (input B)"],
    ["sweep.exe", "Every plan timed: " + M("results\\sweep_*.csv") + " (20,928 rows per GPU)", "Once, to build the model (hours)", "Yes", "kvf calibrate"],
    ["kvf.exe calibrate", "Cost constants " + M("model\\constants_rtx5060.cal"), "Once; then frozen", "No", "kvf.exe plan (input C)"],
    ["kvf.exe plan", "The plan and CUDA (output 1)", "Every time you compile", "No", "you, build_plan.ps1"],
    ["bench.exe (built by build_plan.ps1)", "Check and time of the generated kernel (output 2)", "Every time you test", "Yes", "you"],
], [32, 50, 36, 24, 32])
BOX("<b>Important:</b> running the demo or try_model does <b>not</b> measure the GPU again. It reads the machine file measured "
    "earlier. To measure live, run bw_probe yourself (part 12) and pass the new file with " + M("-Machine") + ".", "callout")

H2("5.1 bw_probe and the machine file, line by line")
P("bw_probe runs small test kernels that each stress one part of the GPU and writes the results to a text file. Some values are "
  "<b>asked</b> from the NVIDIA driver (fixed facts of the chip); the rest are <b>measured</b> by timing. Our file "
  + M("machines\\rtx5060-laptop.gpu") + ":")
LINES([
    ["Line in the file", "Asked or measured, how, and what the compiler uses it for"],
    ["# stride test, ns per 4-byte access: 4B=0.017 8B=0.025 16B=0.047 32B=0.091 64B=0.091 128B=0.092",
     "A comment: raw data of the sector test (see sector_bytes). Reading 4-byte values spaced 4, 8, 16 \u2026 bytes apart: the cost "
     "per value grows until the spacing reaches 32 bytes, then stops growing. Not used directly."],
    ["name = rtx5060-laptop", "The label you passed with --name. Shown in reports."],
    ["compute_capability = 12.0", "Asked. The GPU generation: 12.0 is Blackwell (RTX 50), 8.9 is Ada (RTX 40). Recorded for reference; it tells you which register table belongs with this file."],
    ["dram_gb = 8.5", "Asked. Total GPU memory. Recorded for reference; the cost model does not use it."],
    ["sms = 26", "Asked. Number of SMs. Used everywhere: how many blocks run at once, how many SMs are active, compute rate per SM."],
    ["bw_peak_gbs = 341.3", "Measured: every SM reads a buffer far larger than L2 (so it must come from DRAM), with several launch shapes; the best rate is kept. Used as the ceiling on bandwidth in the cost model."],
    ["bw_sm_gbs = 79.11", "Measured: the same read with a single block, so exactly one SM works. Used as the ceiling on what one SM can pull."],
    ["lat_ns = 148", "Measured: one thread follows a random chain of pointers through 256 MB, so each load must wait for the previous one; time per hop is the idle latency. Used in Little's law (multiplied by the constant lat_scale)."],
    ["bw_l2_gbs = 1581", "Measured: repeatedly reading a working set a quarter of L2's size, so it stays on chip. Used for the merge kernel, whose small partial results are read back from L2."],
    ["l2_bytes = 33554432", "Asked: L2 size, 32 MB. Recorded for reference; not used by the cost model."],
    ["sector_bytes = 32", "Measured by the stride test above: the memory system fetches 32 bytes at a time. Used to charge waste when quantization scale factors are scattered (token-major layout)."],
    ["line_bytes = 128", "Written as a fixed value by the probe, not measured. Recorded for reference; not used."],
    ["f32_gflops = 16026", "Measured: threads run eight independent chains of multiply-adds. 16.0 trillion operations per second. Used for the compute rate: \u00f7 26 SMs \u00f7 64 operations per warp instruction = 9.63 warp instructions per ns per SM."],
    ["launch_us = 20.83", "Measured: an empty kernel timed with CUDA events, as the test driver times kernels. The fixed cost of starting a kernel (high on Windows laptops). Used for launch and merge overhead."],
    ["max_warps_per_sm = 48", "Asked. Limit on warps one SM holds. Used to compute how many blocks fit on an SM."],
    ["max_blocks_per_sm = 24", "Asked. Limit on blocks one SM holds. Same use."],
    ["regs_per_sm = 65536", "Asked. Registers per SM. With the register table, decides how many blocks fit."],
    ["resources = resources_sm120.csv", "Added by hand after probing: the name of the register table for this GPU generation. Without it the compiler estimates register use with a rough formula."],
], 70, 104)
P("The RTX 4060's file, measured the same way by your teammate, reads 250.4 GB/s, 85 GB/s per SM, 128 ns, 24 SMs, launch 5.12 "
  "\u00b5s. Those are the only numbers that changed for the transfer test.")

H2("5.2 The register table and the 288 kernels")
P("<b>What it is.</b> A table listing, for every kernel variant we compiled, how many registers each thread uses and how much "
  "shared memory each block uses. nvcc decides these when it compiles; " + M("tools\\dump_resources.py") + " reads them out of the "
  "compiled program with NVIDIA's " + M("cuobjdump") + " tool. So the table is read from the binary, not timed.")
P("<b>Why the compiler needs it.</b> An SM has 65,536 registers shared by everything running on it. A kernel that uses more "
  "registers per thread leaves room for fewer blocks, so fewer bytes are in flight, so less bandwidth. Example from your run: "
  "the int4 kernel needs few enough registers that the warp limit binds first, 48 \u00f7 4 warps = 12 blocks per SM. The fp16 "
  "8-head packing kernel uses 201 to 248 registers per thread, so one 8-warp block takes 248 \u00d7 32 \u00d7 8 \u2248 63,500 "
  "registers and only <b>one</b> block fits: our known weak spot.")
TABLE([
    ["Column", "Meaning", "Values"],
    ["fmt", "storage format", "0 = f16, 1 = int8, 2 = int4"],
    ["d", "head size", "64, 128"],
    ["g", "query heads packed per block", "1 (no packing), 4, 8"],
    ["u", "unroll factor", "2, 4"],
    ["ord", "layout order", "0 = head-major, 1 = token-major"],
    ["paged", "paged layout", "0, 1"],
    ["final", "kernel kind: 1 = single pass writes the answer (splits = 1); 0 = writes partial results to be merged", "0, 1"],
    ["regs", "registers per thread (the important column)", "40 to 250"],
    ["smem", "shared memory per block in bytes", "9,344 or 9,472"],
], [18, 110, 46])
P("<b>Why 288.</b> The kernel is one template with 7 compile-time switches, and the table has every combination: 3 formats "
  "\u00d7 2 head sizes \u00d7 3 packing sizes \u00d7 2 unrolls \u00d7 2 orders \u00d7 2 residencies \u00d7 2 kernel kinds = "
  "<b>288</b>. Group size, split count and warp count are runtime settings, so they do not multiply the count.")
P("<b>Does it change with the GPU?</b> The count stays 288; it comes from our design. The register values change with the GPU "
  "generation, because nvcc compiles differently for each (the 8-pack fp16 kernel: 201 to 248 on Blackwell, 216 to 250 on Ada). "
  "So there are two tables, " + M("resources_sm120.csv") + " and " + M("resources_sm89.csv") + ". When you compile a plan "
  "that is not among the 288 (packing 2, for example), the generated kernel is still built and run; only the prediction falls "
  "back to an estimated register count.")

H2("5.3 The cost constants: what each means and how they were fitted")
P("Some parts of the time formula cannot be derived from hardware numbers alone, for example how much longer memory takes when "
  "the GPU is busy than when idle. Those parts get adjustable numbers, <b>fitted once</b> to real measurements and then frozen in "
  + M("model\\constants_rtx5060.cal") + ".")
TABLE([
    ["Constant", "Value", "Plain meaning", "Where it enters (part 6)"],
    ["lat_scale", "8.44", "Memory latency under load is 8.4\u00d7 the idle 148 ns, about 1.25 \u00b5s, because a busy memory system queues requests", "Step 4: bandwidth from bytes in flight"],
    ["issue_eff", "0.431", "The inner loop achieves 43% of the SM's peak instruction rate (unpacking, shuffles and softmax cost issue slots)", "Step 5: compute time"],
    ["warp_w0", "2.17", "Warps needed on an SM to hide instruction delays: efficiency = 1 \u2212 e<super>\u2212warps/2.17</super>; 8 or more warps \u2248 full", "Step 5: compute time"],
    ["overlap_p", "4.22", "How well memory and compute time overlap: 1 = not at all (add them), very large = perfectly (take the larger). 4.2 = nearly perfect", "Step 6: combine"],
    ["launch_frac", "0.880", "Share of the measured 20.83 \u00b5s launch cost charged to the main kernel (18.33 \u00b5s)", "Step 7: overheads"],
    ["merge_frac", "0.106", "Share charged to the merge kernel; it starts right behind the main kernel, so most of its launch is hidden", "Step 7: overheads"],
    ["c_page_ns", "22.2 ns", "Cost of one page-table lookup in paged layouts", "Step 7: overheads"],
    ["unpack_l2_hit", "0.739", "Without packing, the share of repeated reads of a shared KV head that the on-chip L2 serves (the rest go to DRAM)", "Step 1: bytes"],
    ["r0_bytes", "2", "Penalty for short contiguous reads (layout). Hit its lower limit, so the layout penalty is effectively off", "Step 3: layout efficiency"],
    ["meta_waste", "0", "Penalty for scattered scale factors. Also hit its limit: off", "Step 1: bytes"],
    ["wave_model", "0", "Not fitted: a structural switch choosing how leftover blocks in the last wave are charged (0 = scale the whole run by the wave count). Chosen on the fit shapes", "Step 4: memory time"],
    ["rel_err.int8_128 ...", "0.0084 ...", "Median measured error of each lossy format (int8:64 0.0075, int8:128 0.0084, int4:32 0.114, int4:64 0.129, int4:128 0.144)", "Accuracy gate"],
], [24, 16, 84, 50])
P("That the layout constants ended at their limits is the model telling us layout barely matters on these GPUs, which the "
  "measurements confirm.")
H3("How they were fitted (" + M("kvf calibrate") + ", code in " + M("src/fit.cpp") + ")")
B(["<b>Data.</b> " + M("sweep.exe") + " ran all 20,928 plans for 10 shapes on the RTX 5060, checked each against the reference, and "
   "recorded its median time. Shapes were sorted and every third one held back (3 held out, 7 used for fitting).",
   "<b>What counts as good.</b> For a candidate set of constants: predict every plan's time on the 7 fit shapes and take the "
   "average size of the log error (how far off the times are), then, for each shape and each of the three budgets (fp16 only, "
   "int8 allowed, everything), see how much slower the plan the model would pick is than the truly fastest (regret). "
   "Score = time error + average regret. Lower is better, so the fit rewards both accurate times and good choices.",
   "<b>Search.</b> For each constant in turn, try 41 values spread over its allowed range and keep any that lowers the score. "
   "Repeat 6 rounds, each time narrowing the range around the current best. About 2,500 score evaluations, each over roughly "
   "14,600 measured plans. A simple coordinate grid search, no machine learning.",
   "<b>Format errors.</b> For each lossy format, the median of its measured errors over the fit rows.",
   "<b>Freeze.</b> The file is saved and never changed. Its SHA-256 fingerprint (starting 01E6FEA6) was the same before and after "
   "the RTX 4060 test, which is what makes \u201cno retuning\u201d a checkable claim."])

# =========================================================================== 6 processing
H1("6. Processing: from the three inputs to the output, stage by stage", new_page=True)
P("Stages 1 to 9 happen inside " + M("kvf.exe plan") + " in milliseconds and need no GPU; stage 10 is the separate build-and-test "
  "step. Stages 1 to 4 and 8 to 9 are shown for the Llama-3-8B demo program (" + M("demo\\3_budget.kv") + "); stage 6 is worked "
  "through for your Qwen run, using the compiler's own printed numbers.")
H2("Stage 1. Lexer: characters \u2192 tokens (" + M("src/lexer.cpp") + ")")
P("Reads " + M("K: kvcache&lt;n, d, ?, ?, ?&gt;") + " and cuts it into labelled pieces: name " + M("K") + ", symbol " + M(":") +
  ", keyword " + M("kvcache") + ", " + M("&lt;") + ", name " + M("n") + ", " + M(",") + " \u2026 and the hole " + M("?") +
  ". Spaces and comments are dropped. The same job as in a C compiler.")
H2("Stage 2. Parser: tokens \u2192 syntax tree (" + M("src/parser.cpp") + ")")
P("Checks the grammar (a " + M("decode") + " block has a name, parameters, declarations, then a " + M("decode_attn(...)") +
  " call) and builds a tree: a decode function with a query Q, caches K and V, and an attention call whose " + M("splits") +
  " and " + M("gqa_pack") + " are holes. A missing bracket gives an error with the line number.")
H2("Stage 3. Semantic checks: is the program meaningful?")
P("A grammatically correct program can still be nonsense. Several of the 19 automatic tests check exactly these rejections: "
  "H must be a multiple of H_kv; d must be 64 or 128; a group size must divide d; K and V must leave the same things open; "
  "an undeclared cache name is rejected; a misspelt target key such as " + M("bw_peek_gbs") + " is rejected rather than ignored.")
H2("Stage 4. IR: the program in internal form")
P("The tree becomes a small intermediate representation in static single assignment style (each value defined once). The holes "
  "are part of the cache's <b>type</b>, so the IR itself records that the program is incomplete:")
CODE("""%Q = kvf.query : tensor<32x128xf32>
%K = kvf.kvcache : kvcache<32768x128x?, ?/?>        <- type still has holes: format ?, order/residency ?/?
%V = kvf.kvcache : kvcache<32768x128x?, ?/?>
%O = kvf.decode_attn %Q, %K, %V : tensor<32x128xf32> {scale = 0.0883883}""")
H2("Stage 5. Enumerate: list every way to fill the holes (" + M("src/plan.cpp") + ")")
TABLE([
    ["Dimension", "Options", "Count"],
    ["Format", "f16; int8:64, int8:128; int4:32, int4:64, int4:128 (lossy only with a budget)", "6"],
    ["Layout", "head-major contiguous; token-major contiguous; head-major paged 16, 32, 64, 128; token-major paged 16, 64", "8"],
    ["Splits", "1, 2, 4, 8, 16, 32, 64, keeping only pieces of at least 128 tokens", "up to 7"],
    ["GQA packing", "off; on if H \u00f7 H_kv is 2, 4 or 8", "1 or 2"],
    ["Warps", "4, 8", "2"],
    ["Unroll", "2, 4", "2"],
], [28, 124, 22])
P("Llama-3-8B demo: 6 \u00d7 8 \u00d7 7 \u00d7 2 \u00d7 2 \u00d7 2 = <b>2,688</b>. Your Qwen run: 6 \u00d7 8 \u00d7 6 \u00d7 1 "
  "\u00d7 2 \u00d7 2 = <b>1,152</b> (split 64 dropped because 4,096 \u00f7 64 = 64 tokens; packing impossible because 28 \u00f7 4 "
  "= 7). Without a budget only f16 remains (448 for the demo shape). Pinned values shrink their dimension to one.")
H2("Stage 6. Cost model: predict each plan's time without running it (" + M("src/cost.cpp") + ")")
P("The heart of the project. For every candidate the compiler computes seven things. Below, each step shows which input it uses "
  "(<b>A</b> program, <b>B</b> machine file and register table, <b>C</b> constants) and the actual numbers for the plan chosen in "
  "your Qwen run: int4:128, head-major contiguous, splits 1, no packing, 4 warps, unroll 2. Every result matches what the "
  "compiler printed in " + M("report.txt") + ".")
TABLE([
    ["Step", "What is computed (inputs used)", "Your Qwen run, worked"],
    ["1. Bytes",
     "Cache rows = n \u00d7 H_kv \u00d7 batch (A). Bytes per row from the format: d \u00d7 bits \u00f7 8, plus 4 bytes of scale and zero point per group. "
     "Without packing, the g query heads sharing a KV head each read it, and only the share unpack_l2_hit (C) of the repeats comes from L2, so bytes are multiplied by "
     "1 + (g \u2212 1)(1 \u2212 unpack_l2_hit \u00d7 window), where window is the share of a group's blocks running at the same time. Plus reading Q and writing O.",
     "Rows 4,096 \u00d7 4 \u00d7 64 = 1,048,576. int4 row 64 B \u2192 K + V payload 128 MiB; scales 8 MiB. g = 7, window = 1: repeat factor 1 + 6 \u00d7 (1 \u2212 0.739) = 2.57. "
     "Payload 128 \u00d7 2.57 = <b>328.8 MiB</b>, metadata <b>20.6 MiB</b>, Q + O <b>1.75 MiB</b>, total <b>351.1 MiB</b>."],
    ["2. Blocks and occupancy",
     "Blocks = splits \u00d7 (KV heads if packing, else query heads) \u00d7 batch. Blocks that fit on one SM = the smallest of: block limit 24, warp limit 48 \u00f7 warps, and registers 65,536 \u00f7 (registers per thread \u00d7 32 \u00d7 warps) (B).",
     "1 \u00d7 28 \u00d7 64 = <b>1,792 blocks</b>. Warp limit 48 \u00f7 4 = 12 binds: 12 blocks per SM, 26 \u00d7 12 = 312 at once. Active SMs = <b>26</b>."],
    ["3. Layout efficiency",
     "Length of the unbroken run a block reads; efficiency = run \u00f7 (run + r0_bytes) (C). With r0_bytes = 2 this is \u2248 1 for every layout.",
     "Head-major contiguous: one long run. Efficiency <b>1.000</b>."],
    ["4. Memory time",
     "Bytes in flight per block = warps \u00d7 32 threads \u00d7 bytes per load \u00d7 unroll \u00d7 2 (K and V). Per-SM bandwidth = min(bw_sm, bytes in flight per SM \u00f7 (lat_ns \u00d7 lat_scale)) (B, C); "
     "GPU bandwidth = min(bw_peak, active SMs \u00d7 that). Memory time = bytes \u00f7 bandwidth \u00d7 wave factor (the last wave of blocks is partly empty).",
     "Per block 4 \u00d7 32 \u00d7 4 B \u00d7 2 \u00d7 2 = 2,048 B; 12 blocks = <b>24 KiB per SM</b>. 24,576 \u00f7 (148 \u00d7 8.44 ns) = 19.7 GB/s per SM; \u00d7 26 = 512, capped at <b>341.3 GB/s</b>. "
     "Waves: 1,792 \u00f7 312 \u2192 6 waves, factor 6 \u00d7 312 \u00f7 1,792 = 1.045. 368.1 MB \u00f7 341.3 GB/s \u00d7 1.045 = <b>1,126.7 \u00b5s</b>."],
    ["5. Compute time",
     "Warp instructions counted from the kernel source: per token 10 + unpack (8 for f16, 32 for int8/int4); per token per query head 8 (dot product) + 2 (scale) + 2 log2(d/8) (sum across threads) + 12 (softmax) + 8 or 16 (values). "
     "Divided by the issue rate: active SMs \u00d7 (f32_gflops \u00f7 sms \u00f7 64) \u00d7 issue_eff \u00d7 (1 \u2212 e<super>\u2212warps per SM / warp_w0</super>) (B, C).",
     "Per token 42, per head 8 + 2 + 8 + 12 + 16 = 46; one block handles 2 tokens per warp step. 64 \u00d7 28 \u00d7 4,096 visits \u00d7 88 \u00f7 2 = 323 million warp instructions. "
     "Rate 26 \u00d7 9.63 \u00d7 0.431 \u00d7 1.0 = 107.9 per ns \u2192 <b>2,994.4 \u00b5s</b>. Larger than memory time, so <b>compute bound</b>."],
    ["6. Combine",
     "Memory and compute partly overlap: (T_mem<super>p</super> + T_cmp<super>p</super>)<super>1/p</super> with p = overlap_p (C).",
     "(1,126.7<super>4.22</super> + 2,994.4<super>4.22</super>)<super>1/4.22</super> = <b>3,005.8 \u00b5s</b>."],
    ["7. Overheads",
     "Launch = launch_frac \u00d7 launch_us; merge (if splits &gt; 1) = merge_frac \u00d7 launch_us + partials \u00f7 bw_l2; pages = lookups \u00d7 c_page_ns spread over the parallel warps (B, C).",
     "Launch 0.880 \u00d7 20.83 = <b>18.3 \u00b5s</b>; no merge, no pages. <b>Total 3,005.8 + 18.3 = 3,024.2 \u00b5s</b>, the printed T_total."],
], [22, 82, 70])
H2("Stage 7. Rank and apply the accuracy gate (" + M("src/passes.cpp") + ")")
P("All plans are sorted by predicted time (a stable sort, so equal times keep their listed order). Each lossy plan carries its "
  "format's error from the constants file; if that is above the budget, the plan is marked rejected but kept in the list so the "
  "report shows what the budget cost. The fastest plan not rejected wins. In the Llama-3-8B demo with budget 0.02: all 1,344 "
  "int4 plans (error 0.114 to 0.144) were rejected, and int8:128 (0.0084) won. In your run, budget 0.2 rejected nothing, and "
  "int4:128 won.")
H2("Stage 8. Rewrite the IR: holes become decisions")
P("The pass replaces the generic operation with a planned one and fills in the cache types. The program is now fully specified:")
CODE("""%K = kvf.kvcache : kvcache<32768x128xint8:128, head_major/contiguous>
%O = kvf.decode_attn_split %Q, %K, %V {format = int8:128, layout = head_major/contiguous, splits = 32,
      gqa_pack = true, warps = 8, unroll = 4, blocks = 256, pred_us = 313.484}""")
H2("Stage 9. Code generation: IR \u2192 CUDA (" + M("src/codegen.cpp") + ")")
P("KVForge does not write GPU instructions one by one. " + M("runtime/kvf_kernels.cuh") + " holds one kernel <b>template</b> with "
  "switches for format, head size, packing, unroll, order and paging. Code generation writes a short CUDA file that sets the "
  "switches from the IR, plus a header " + M("plan_info.h") + " describing the plan. From the real " + M("decode_budget.cu") + ":")
CODE("""extern "C" cudaError_t kvf_launch_budget(const kvf::Args *in, cudaStream_t st) {
  kvf::Args a = *in;
  a.splits = 32;  a.warps = 8;  a.group_shift = 7;          // runtime settings: 2^7 = 128-number groups
  return kvf::launch<kvf::FMT_INT8, 128, 4, 4, kvf::ORD_HEAD, false>(a, st);
}                     // template switches: format, d, packed heads, unroll, order, paged""")
H2("Stage 10. nvcc, then check and time (" + M("tools\\build_plan.ps1") + ", " + M("runtime/kvf_driver.cu") + ")")
B(["<b>nvcc</b>, NVIDIA's compiler, compiles that file with the test driver into " + M("bench.exe") + ". Here the template is "
   "specialised: code not needed for this plan is removed and the constants are folded in. nvcc does instruction selection and "
   "register allocation, the low-level back end.",
   "<b>Test data.</b> The driver makes random Q, K and V, rounds K and V to the plan's format and stores them in the plan's layout.",
   "<b>Check.</b> The CPU computes attention in double precision twice: on the rounded data (what the kernel should produce) and "
   "on the original data (exact attention). The GPU result is compared with both.",
   "<b>Time.</b> 5 warm-up runs, then 50 timed runs. Before each, a buffer of at least 96 MB (three times the L2 size) is written, "
   "so the cache cannot be served from L2 left over from the previous run. Each run is timed with CUDA events on the GPU."])

# =========================================================================== 7 compiler
H1("7. Why this is a compiler", new_page=True)
TABLE([
    ["Classic C compiler", "KVForge"],
    ["Source language with a grammar", "The .kv language: decode blocks, typed declarations, holes, target settings (docs/dsl.md)"],
    ["Lexer, parser, type checking", "Stages 1 to 3, with 19 automatic tests including rejections of bad programs"],
    ["Intermediate representation", "Stage 4: an SSA-style IR whose types can contain holes"],
    ["Optimisation passes guided by cost heuristics (inline? unroll? which instructions?)",
     "Stages 5 to 8: a search pass over plans, an analytic cost model in place of rules of thumb, an accuracy-gate pass, and an IR rewrite that lowers the generic operation to a planned one"],
    ["Code generation: instruction selection, register allocation",
     "Stage 9 selects and configures a kernel template and emits CUDA; nvcc then does instruction selection and register allocation"],
    ["Output: an executable", "Output: CUDA source, built into a verified, timed executable"],
], [64, 110])
P("The front end (stages 1 to 4) is a textbook compiler. The research contribution is the middle (stages 5 to 8): deciding "
  "<i>how</i> to run the operation by predicting cost from measured hardware facts instead of timing candidates. The back end is "
  "deliberately thin: KVForge chooses and configures kernels and lets nvcc produce machine code. That places it in the same family "
  "as Halide and TVM, well-known compilers that also separate <i>what</i> to compute from <i>how</i> to schedule it, and whose "
  "main job is choosing the schedule.")
BOX("<b>If asked \u201cis this really a compiler?\u201d:</b> Yes, a domain-specific compiler. It has a language with a grammar "
    "and type rules, an IR transformed by passes, a cost-model-driven optimisation pass, and a code generator, with nvcc as its "
    "back end. What it optimises is the schedule and data representation of one operator, which is what Halide and TVM optimise too. "
    "Its distinctive part is that the optimisation decision comes from a measured-hardware cost model rather than from trials.", "note")
P("<b>Not claimed:</b> KVForge does not do register allocation or instruction selection itself, and it compiles one kind of "
  "operator, not general programs.")

# =========================================================================== 8 output
H1("8. The output: every file and what is in it")
P(M("kvf plan") + " writes five files into the " + M("--out") + " folder; " + M("build_plan.ps1") + " adds the executable and "
  "prints the check and timing. For your run the folder is " + M("out\\try\\H28_4_d128_n4096_b64\\pick\\") + ".")
TABLE([
    ["File", "Contents"],
    ["model.kv", "The program (written by try_model.ps1). Input, kept for the record."],
    ["report.txt", "The compiler's reasoning: the spec, the machine, the search space, the chosen plan, the full predicted cost breakdown, the top candidates, the roofline table, and the IR before and after planning."],
    ["plans.csv", "Every candidate, one row each, with its predicted numbers (columns below). Open in Excel to sort and filter."],
    ["ir.txt", "The IR before and after planning (stage 4 and stage 8)."],
    ["decode_model.cu", "The generated CUDA (stage 9)."],
    ["plan_info.h", "The plan as constants (H, H_kv, d, n, batch, format, group, order, paged, splits, warps, predicted time) for the test driver."],
    ["bench.exe", "The compiled kernel plus test driver (stage 10). Run it again any time to re-check and re-time."],
], [32, 142])
H2("Columns of plans.csv")
TABLE([
    ["Column", "Meaning"],
    ["name, H, H_kv, d, n, batch", "The program's shape"],
    ["fmt, group", "Format and group size (group 0 for f16)"],
    ["order, residency, block_tokens", "Layout; block_tokens is the page size (0 for contiguous)"],
    ["splits, gqa_pack, warps, unroll", "Partition"],
    ["pred_us", "Predicted total time in microseconds (stage 6, step 7)"],
    ["pred_gbs", "Predicted achieved bandwidth: cache bytes \u00f7 predicted time"],
    ["pred_eta", "Layout efficiency (step 3)"],
    ["pred_mem_us, pred_cmp_us", "Predicted memory time and compute time (steps 4 and 5)"],
    ["pred_merge_us, pred_page_us", "Merge and page overheads (step 7)"],
    ["blocks, active_sms", "Blocks launched, and SMs with work (step 2)"],
    ["rel_err", "The format's calibrated error (0 for f16)"],
    ["rejected", "1 if the accuracy gate removed it"],
], [52, 122])
H2("Sections of report.txt")
TABLE([
    ["Section", "What it shows"],
    ["Spec, Machine", "The shape and g = H \u00f7 H_kv; the machine's SMs, bandwidths, latency, ridge point; which constants file was used"],
    ["Search space, Candidates evaluated", "Which dimensions were free, whether lossy formats were included, how many plans"],
    ["Chosen plan", "Format with bits per number, layout, partition with blocks and active SMs, calibrated error"],
    ["Predicted cost", "KV payload (including repeated reads), metadata, Q and O, split partials, total traffic; attention and unpacking FLOPs; intensity (FLOPs per byte); layout eta; bytes in flight per SM; effective bandwidth; T_mem, T_cmp, T_merge, T_page, T_launch, T_total and the bound; achieved bandwidth and % of peak"],
    ["Candidate ranking", "The top candidates with their predicted time, bandwidth, intensity, blocks, eta, bound and status (rejected or not)"],
    ["Roofline position", "FLOPs per byte of each format for packing sizes 1, 4, 8 against the ridge point (47): all far below it, so memory bound"],
    ["IR before / after planning", "Stages 4 and 8"],
], [44, 130])
P("<b>The ridge point</b> (in the roofline section) is the GPU's arithmetic rate \u00f7 memory rate = 16,026 \u00f7 341.3 = 47 "
  "operations per byte. An operation doing fewer operations per byte than that is limited by memory. Decode attention does "
  "2g \u00f7 (bytes per number) operations per byte, independent of n: 4 for Llama-3 in f16, far below 47.", "small")

# =========================================================================== 9 run
H1("9. Your Qwen2.5-7B run, line by line", new_page=True)
P("Command: " + M("powershell -ExecutionPolicy Bypass -File demo\\try_model.ps1") + ", answers: qwen2.5-7b, 4096, 64, 0.2. "
  "Run on the RTX 5060 Laptop. Every printed line, in order:")
LINES([
    ["Printed line", "What it means and where the value comes from"],
    ["Models with known shapes: llama3-8b, ... tinyllama / or type 'custom'",
     "The presets built into try_model.ps1, each holding H, H_kv and d from the model's config.json. 'custom' asks for the three numbers instead."],
    ["Model [llama3-8b]: qwen2.5-7b", "Your choice; the default is in brackets. Qwen2.5-7B: H = 28, H_kv = 4, d = 128."],
    ["Context length n (tokens) [32768]: 4096", "4,096 earlier tokens are in the cache for each conversation."],
    ["Batch (conversations at once) [1]: 64", "64 conversations decoded together, each with its own cache."],
    ["Accuracy budget (...) [0.2]", "You allowed answers up to 20% off exact attention; that admits int4."],
    ["One attention layer: H=28 H_kv=4 d=128 n=4096 batch=64 -> KV cache 512 MB per layer in fp16",
     "Size of one layer's cache: 2 (K, V) \u00d7 4 heads \u00d7 128 numbers \u00d7 4,096 tokens \u00d7 64 conversations \u00d7 2 bytes = 512 MB. "
     "The model has 28 layers, about 14 GB in all, which is why one layer is tested."],
    ["--- the program the compiler gets (out\\try\\...\\pick\\model.kv) ---", "The .kv program try_model.ps1 wrote from your answers (part 4 explains every field)."],
    ["target max_rel_err = 0.2", "Your budget, as a line of the program."],
    ["decode model(H: 28, H_kv: 4, d: 128, n: 4096, batch: 64) {", "The shape and scenario; 'model' is just the program's name."],
    ["Q: query<H, d, f32>", "The new token's queries: 28 vectors of 128 32-bit floats per conversation."],
    ["K: kvcache<n, d, ?, ?, ?>  /  V: ...", "The caches, with format, order and residency left as holes."],
    ["O = decode_attn(Q, K, V, scale = auto, splits = ?, gqa_pack = ?)", "The operation; split count and packing also left to the compiler. scale = 1/\u221a128."],
    ["--- KVForge : compiler decision ---", "Stages 1 to 9 ran inside kvf.exe; these lines are extracts of report.txt."],
    ["Candidates evaluated: 1152",
     "6 formats \u00d7 8 layouts \u00d7 6 split counts \u00d7 1 packing choice \u00d7 2 warps \u00d7 2 unrolls. Split 64 dropped (only 64 tokens per piece); "
     "packing impossible (28 \u00f7 4 = 7 heads per group; kernels exist for 2, 4, 8)."],
    ["format: int4:128 (4.25 bits/element)",
     "Each number in 4 bits; each group of 128 numbers has a 16-bit scale and 16-bit zero point, 32 \u00f7 128 = 0.25 bits more per number. "
     "Chosen because it reads the fewest bytes and its error (0.144) is within 0.2."],
    ["layout: head_major/contiguous",
     "Each conversation's KV heads stored one after another, each head's tokens in one unbroken run (layout table below). The 8 layouts were "
     "predicted within 1.5% of each other (3,024 to 3,069 \u00b5s); this one was lowest."],
    ["partition: splits=1 w4 u2",
     "splits = 1: each scan done by one block; 1,792 blocks already fill all 26 SMs, so splitting would only add merging. No 'pack' in the text: "
     "packing off. w4: 4 warps (128 threads) per block. u2: each thread keeps 2 loads in flight. Warps and unroll tied on predicted time; "
     "the first listed was kept."],
    ["blocks = 1792   active SMs = 26", "28 query heads \u00d7 64 conversations \u00d7 1 split = 1,792 blocks; all 26 SMs get work, 12 blocks each at a time, in 6 waves."],
    ["accuracy: calibrated relative error 0.143969",
     "Not computed in this run: the median error int4:128 showed across the 5060 sweep, stored in the constants file and used by the gate. 0.144 \u2264 0.2: passed."],
    ["T_total 3024.16 us (compute bound)",
     "The prediction, worked in part 6, stage 6: memory 1,127 \u00b5s, compute 2,994 \u00b5s; compute is larger, so 'compute bound'. "
     "int4 is compute bound here because without packing all 7 query heads unpack the same 4-bit data separately."],
    ["--- building, checking and timing the generated kernel ---", "Stage 10 starts: build_plan.ps1 runs nvcc."],
    ["built C:\\Users\\aahav\\KVForge\\out\\try\\...\\pick\\bench.exe", "nvcc compiled decode_model.cu with the test driver into this program."],
    ["device: NVIDIA GeForce RTX 5060 Laptop GPU", "The GPU it ran on, as reported by the driver."],
    ["plan: int4:128 | head_major/contiguous | splits=1 w4 u2", "The plan compiled into bench.exe; it matches the compiler's decision."],
    ["check: relative error vs dequantised reference 6.44e-07 (PASS)",
     "Correctness. Compared with double-precision attention on the same int4-rounded data, the GPU's answer differs by 6.4 in 10 million: "
     "floating-point noise. PASS means below the tolerance: the kernel computes exactly what int4 attention should."],
    ["accuracy: relative error vs exact fp32 attention 0.143",
     "Cost of the format. Compared with attention on the original, unrounded numbers: 14.3% off, matching the 0.144 the gate used. (fp16 gives 0.0003.)"],
    ["time: 7657.79 us median (IQR 7622.78..7676.48, 50 reps)",
     "Measured: 50 timed runs, L2 flushed before each, timed with CUDA events. Median = the middle run, 7.66 ms. IQR = the range of the middle half of runs "
     "(25th to 75th percentile); narrow, so the measurement is stable."],
    ["rate: 18.6 GB/s of KV payload",
     "Cache bytes counted once \u00f7 time: int4 cache = 512 MB \u00d7 4.25 \u00f7 16 = 136 MB; 136 MB \u00f7 7.66 ms = 18.6 GB/s. Low, because "
     "the kernel is busy computing and reads the cache several times (part 10)."],
    ["predicted 3024.16 us, measured 7657.79 us (ratio 2.53)",
     "Measured \u00f7 predicted. 1.0 is perfect; on shapes like those fitted, the average gap is about 15%. 2.53 is a large miss: part 10."],
    ["--- naive kernel (for comparison) : compiler decision ---", "The same steps for the second program, with everything pinned."],
    ["Candidates evaluated: 4", "Format, layout, splits and packing pinned; only warps (4, 8) \u00d7 unroll (2, 4) remain."],
    ["format: f16 (16.00 bits/element) / layout: token_major/contiguous / partition: splits=1 w4 u2",
     "The pinned naive choices; w4 u2 won among the four."],
    ["blocks = 1792   active SMs = 26", "Same block count: no splitting, no packing."],
    ["T_total 4190.62 us (memory bound)", "Predicted: reading 1.3 GB (512 MB \u00d7 2.57 repeat factor) at 339 GB/s = 4,141 \u00b5s, plus launch."],
    ["check: ... 4.58e-07 (PASS)", "The naive kernel is also correct."],
    ["accuracy: ... 0.000303", "fp16's own rounding: 0.03%."],
    ["time: 13067.30 us median (IQR 12820.86..16121.95, 50 reps)", "Measured 13.07 ms. The IQR is wider: some runs were slower (cause not investigated)."],
    ["rate: 41.1 GB/s of KV payload", "512 MB \u00f7 13.07 ms."],
    ["predicted 4190.62 us, measured 13067.30 us (ratio 3.12)", "Also under-predicted, by 3.1\u00d7."],
], 64, 110)
P("The script's last line, " + M("RESULT: naive 13067.3 us, KVForge 7657.8 us -> 1.71x faster") + ", is 13,067 \u00f7 7,658.")
H2("The layout options")
P("Layout decides which numbers sit next to each other in memory. The GPU fetches 32-byte pieces, so what is adjacent decides "
  "how many fetched bytes are useful. A <i>row</i> is one token's d numbers for one KV head.")
TABLE([
    ["Option", "Arrangement in memory", "What a block reading one KV head sees"],
    ["head_major / contiguous", "conversation \u2192 KV head \u2192 token \u2192 numbers", "One long unbroken run"],
    ["token_major / contiguous", "conversation \u2192 token \u2192 KV head \u2192 numbers", "One row, then a jump past the other heads' rows"],
    ["head_major / paged:16, 32, 64, 128", "Cache cut into pages of 16 to 128 tokens placed anywhere in memory and found through a page table (as vLLM does); head-major inside a page",
     "A run as long as the page, then a page-table lookup before the next page"],
    ["token_major / paged:16, 64", "Same pages, token-major inside", "Short runs and page lookups"],
], [40, 70, 64])
P("<b>Basis of the choice:</b> the lowest predicted time, like everything else. The model charges short runs (r0_bytes, fitted "
  "to almost nothing) and page lookups (22 ns each), so contiguous layouts usually win. Paged layouts exist because real serving "
  "systems use them to share memory among many conversations; the compiler shows what that costs.")

# =========================================================================== 10 lessons
H1("10. What that run tells us")
TABLE([
    ["", "Predicted", "Measured"],
    ["KVForge pick (int4, no packing)", "3,024 \u00b5s", "7,658 \u00b5s"],
    ["Naive kernel (f16)", "4,191 \u00b5s", "13,067 \u00b5s"],
    ["Speedup of the pick", "1.39\u00d7", "1.71\u00d7"],
], [64, 55, 55])
B(["<b>The ranking was right.</b> The plan the model called faster was faster, by more than it predicted.",
   "<b>The times were off by 2.5 to 3.1\u00d7.</b>",
   "<b>Most likely reason (consistent with the arithmetic; not proven by a dedicated test):</b> without packing, each of the 7 query "
   "heads sharing a KV head reads that head separately. The model assumed 74% of those repeat reads come from L2 (constant "
   "unpack_l2_hit), so it counted the cache 2.57 times: 1.3 GB for the naive kernel. If instead nearly all 7 reads go to DRAM, "
   "that is 512 MB \u00d7 7 = 3.76 GB, and 3.76 GB in 13.07 ms is 288 GB/s, close to the card's measured 341 GB/s. So the naive "
   "kernel was streaming at near full speed but reading the cache about 7 times.",
   "<b>This shape is outside what the constants were fitted on.</b> The sweep's largest batch was 8 and its head groups were "
   "1, 4 and 8. At batch 64 with 1,792 blocks, the blocks that share a KV head are evidently not close enough in time to share L2.",
   "<b>The budget is the user's decision.</b> 0.2 let in 14% error. With 0.02 the compiler would choose int8 (about 0.8% error)."])
BOX("<b>How to say it:</b> \u201cOn shapes like the ones we fitted on, predictions are within about 15%. Here, at 64 users and a "
    "head ratio we never measured, the times are off by 2.5\u00d7, but the plan it picked was still the faster one. Modelling "
    "repeated reads at large batch is the fix.\u201d", "callout")

# =========================================================================== 11 results
H1("11. Results of the whole project", new_page=True)
TABLE([
    ["Finding", "Result", "Meaning"],
    ["Same bytes, different speed (H1)", "1.8\u00d7 to 6.4\u00d7 among fp16 plans (5060); 1.1\u00d7 to 4.6\u00d7 (4060)", "Reuse-based models cannot see this; ours can"],
    ["Which choices matter", "Split count up to 58%; packing 40%; format 1.8\u00d7; unroll 11%; layout \u2264 8%; warps \u2248 0", "Two levers dominate"],
    ["Model quality, 5060 held-out", "Rank correlation 0.88; time error 15%", "Orders plans well"],
    ["Pick vs naive (5060, 10 shapes)", "1.93\u00d7 / 3.00\u00d7 / 3.64\u00d7 (fp16 / int8 / int4 allowed)", "Regret 11.4 / 5.8 / 11.2%"],
    ["Pick vs libraries (5060, fp16)", "1.06\u00d7 FlashInfer's time; PyTorch SDPA 1.02\u00d7; naive 2.12\u00d7", "Competitive, not faster"],
    ["Transfer to RTX 4060, no refit", "Rank correlation 0.886; regret 6.6 / 11.8 / 16.1%; 1.5\u20133.2\u00d7 over naive", "Targets met for fp16 and int8, narrowly missed for all"],
    ["Controls on the 4060", "Copying the 5060's winner for the same shape: 2.3 / 7.1 / 6.8% regret. Unseen shape: model ties a nearest-shape rule on average, far better worst case (17/42/55% vs 46/61/64%)", "The model's value is for shapes nobody tuned"],
    ["Known failure", "H64/8 shape: predicted tie, measured 200 vs 152 \u00b5s; 8-pack kernel 216\u2013250 registers", "Same kernel trails FlashInfer"],
    ["Correctness", "44,224 runs verified, none failed", "Generated code is correct"],
], [38, 82, 54])
H2("Open items")
B(["Fix the register-heavy 8-head packing kernel.",
   "Model repeated reads at large batch (part 10) and split counts that run slower than their neighbours.",
   "Measure int8 accuracy on a real model's output, not random data.",
   "Test a GPU unlike the two laptops (a server GPU).",
   "fp8 format; the final written report."])

# =========================================================================== 12 run it
H1("12. Running it yourself")
P("Use <b>PowerShell</b>, not Git Bash (Git Bash blocks the built programs). Start in the project folder:")
CODE("""cd C:\\Users\\aahav\\KVForge

# 1. Compiler self-tests, no GPU needed: expect 19 PASS
powershell -ExecutionPolicy Bypass -File tests\\smoke.ps1

# 2. The demo: three Llama-3-8B programs (Enter moves to the next step)
powershell -ExecutionPolicy Bypass -File demo\\run_demo.ps1 -Pause

# 3. Any model, asked interactively (about 1.5 minutes)
powershell -ExecutionPolicy Bypass -File demo\\try_model.ps1
#    or in one line:
powershell -ExecutionPolicy Bypass -File demo\\try_model.ps1 -Model mistral-7b -N 8192 -Batch 4 -MaxErr 0.02
powershell -ExecutionPolicy Bypass -File demo\\try_model.ps1 -H 32 -Hkv 8 -D 128 -N 16384 -Batch 2 -MaxErr 0

# 4. Measure the GPU live (about a minute). Use a NEW name; never overwrite rtx5060-laptop.gpu
.\\build\\cuda\\bw_probe.exe --name live-5060 --out machines\\live-5060.gpu
notepad machines\\live-5060.gpu        # add the line:  resources = resources_sm120.csv
powershell -ExecutionPolicy Bypass -File demo\\try_model.ps1 -Machine machines\\live-5060.gpu

# 5. Compiler only, on your own .kv file, then build + check + time
.\\build\\kvf.exe plan my.kv --machine machines\\rtx5060-laptop.gpu --calib model\\constants_rtx5060.cal --out out\\my
powershell -ExecutionPolicy Bypass -File tools\\build_plan.ps1 -Dir out\\my -Arch 120

# 6. Reproduce the model-quality numbers on the held-out shapes
.\\build\\kvf.exe evaluate --sweep results\\sweep_rtx5060-laptop.csv --machine machines\\rtx5060-laptop.gpu --calib model\\constants_rtx5060.cal --holdout-every 3 --which heldout""")
H2("Things to try")
B(["Budget 0 instead of 0.2: only f16 is searched; the choice becomes slower but exact.",
   "Budget 0.02: int8 is chosen.",
   "Model llama3-8b with batch 64: packing is possible (g = 4); compare with the Qwen run.",
   "Custom d = 96: the compiler rejects it with an error."])
H2("Where things run")
TABLE([
    ["Program", "Runs on"],
    ["kvf.exe (the compiler)", "Any Windows PC; no graphics card needed"],
    ["bw_probe.exe, bench.exe", "A PC with an NVIDIA RTX 50 card (build\\cuda) or RTX 40 card (build\\cuda_89) and its driver; no CUDA toolkit needed"],
    ["Older NVIDIA cards (RTX 30, 20) or server cards (A100, H100)", "Need a one-command rebuild for that generation on a PC with the CUDA toolkit, e.g. tools\\build_cuda.ps1 -Targets probe -Arch 86"],
    ["AMD, Intel, Apple GPUs", "Not supported: the kernels are written in NVIDIA's CUDA"],
], [62, 112])

# =========================================================================== 13 FAQ
H1("13. Questions you may be asked")
TABLE([
    ["Question", "Answer"],
    ["Is it faster than FlashInfer?", "No: 6% slower on average, 6% faster on one shape, 33% slower on one. The claim is choosing well by prediction, without per-GPU tuning."],
    ["Where is the compiler?", "Part 7: a language, lexer, parser, semantic checks, an IR with holes, a cost-model-driven search pass, an accuracy-gate pass, an IR rewrite, and CUDA generation with nvcc as back end."],
    ["Why not just autotune?", "Autotuning times hundreds of candidates on every GPU for every shape. The model predicts in milliseconds after a one-minute probe. Where a shape was already tuned on a similar GPU, copying that winner is better (we measured this); the model is for new shapes and new GPUs."],
    ["Does it depend on the model?", "Only through five numbers in the program (H, H_kv, d, n, batch). It never loads weights."],
    ["Does it measure the GPU every time?", "No. bw_probe measures once and saves a file; the compiler reads that file."],
    ["What is the 288?", "The number of kernel variants compiled from one template: 3 formats \u00d7 2 head sizes \u00d7 3 packing sizes \u00d7 2 unrolls \u00d7 2 orders \u00d7 2 residencies \u00d7 2 kernel kinds."],
    ["What do the constants do?", "Part 5.3: ten numbers for effects that cannot be read off hardware (loaded latency, instruction efficiency, overlap, overheads), fitted once to 7 shapes and frozen; plus each lossy format's error."],
    ["How do you know the kernels are correct?", "Every run is compared with a double-precision reference; 44,224 runs, none failed."],
    ["Is int8 safe?", "0.8% error on random data. On a real model's output it is not yet measured."],
    ["Why only d = 64 or 128?", "Each thread handles 8 numbers; those sizes divide a 32-thread warp evenly. Others need new kernels."],
    ["What is GQA packing?", "When several query heads share one KV head (GQA), one block serves them all and reads the KV head once, instead of once per query head."],
    ["Why was your Qwen prediction 2.5\u00d7 off?", "Part 10: no packing possible, batch 64 far outside the fitted range, and the L2 re-read assumption failed. The ranking was still right."],
    ["Did you test server GPUs?", "No; two laptop GPUs of different generations. A dissimilar GPU is a planned deliverable."],
], [46, 128])

# =========================================================================== 14 glossary
H1("14. Glossary")
TABLE([
    ["Term", "Meaning"],
    ["Token", "A word piece; the unit a model reads and writes"],
    ["Query / key / value", "Per-token vectors: what it looks for / what it offers to be matched on / what it passes on"],
    ["Head", "One of several parallel attention computations in a layer"],
    ["GQA", "Grouped-query attention: several query heads share one KV head; g = H \u00f7 H_kv"],
    ["KV cache", "The stored keys and values of all earlier tokens, one table per layer"],
    ["Prefill / decode", "Reading the prompt all at once / producing the answer one token at a time"],
    ["d (head_dim)", "Length of each query, key and value vector"],
    ["n, batch", "Tokens in the cache; conversations decoded together"],
    ["f16 / int8 / int4", "16-, 8- or 4-bit storage per number"],
    ["Group (int8:128)", "Numbers sharing one scale and zero point"],
    ["Relative error", "Size of the difference from the exact answer, divided by the size of the exact answer"],
    ["Budget (max_rel_err)", "The largest relative error you accept"],
    ["Hole (?)", "A choice left to the compiler"],
    ["Plan / candidate", "One complete set of choices: format, layout, splits, packing, warps, unroll"],
    ["Splits", "Pieces each cache scan is cut into, merged afterwards"],
    ["Packing", "One block serving all query heads of a GQA group"],
    ["Unroll", "Loads each thread issues before waiting"],
    ["Layout: head/token-major, contiguous/paged", "How the cache is arranged in memory (part 9)"],
    ["Cost model", "The formula predicting a plan's time (part 6, stage 6)"],
    ["Accuracy gate", "The pass rejecting formats over the budget"],
    ["Memory / compute bound", "Whether reading or arithmetic takes longer"],
    ["Ridge point", "Arithmetic rate \u00f7 memory rate (47 operations per byte); below it, memory bound"],
    ["Little's law", "Bandwidth = bytes in flight \u00f7 latency"],
    ["Wave", "One round of blocks running at once; the last may be partly empty"],
    ["IR, SSA", "The compiler's internal form; each value defined once"],
    ["Template", "One kernel source with switches, specialised by the C++ compiler for each plan"],
    ["nvcc, cuobjdump", "NVIDIA's CUDA compiler; NVIDIA's tool to inspect compiled kernels"],
    ["Median, IQR", "Middle measurement; range of the middle half of measurements"],
    ["Regret", "How much slower the chosen plan is than the best measured plan"],
    ["Rank correlation (Spearman \u03c1)", "How well the predicted order of plans matches the measured order; 1 = identical"],
    ["MAPE", "Mean absolute percentage error of predicted times"],
    ["Sweep", "Timing every plan for a set of shapes, the ground truth for fitting and testing"],
    ["Held-out shapes", "Shapes not used for fitting, used to test the model honestly"],
    ["Transfer", "Using constants fitted on one GPU, unchanged, on another"],
], [52, 122])


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Body", 7.5)
    canvas.setFillColor(SLATE)
    if doc.page > 1:
        canvas.drawString(18 * mm, 10 * mm, "KVForge | The complete guide | Compiler Design, VIT Vellore")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, str(doc.page))
    canvas.restoreState()


doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
                        title="KVForge: the complete guide", author="Aahav Yadav, Akshat Kapur, Rishab Jajodia")
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print("wrote", OUT)
