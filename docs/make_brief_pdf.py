"""Build the KVForge project brief (for the faculty meeting) as a PDF.

    python docs/make_brief_pdf.py [output.pdf]

Default output: C:/Users/aahav/Downloads/KVForge_Project_Brief.pdf

Every number is from this project's own runs (results/, docs/results.md,
demo/demo_output_recorded.txt). Nothing here is estimated unless it says so.
"""
import os
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.fonts import addMapping
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (CondPageBreak, Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle, XPreformatted)

OUT = sys.argv[1] if len(sys.argv) > 1 else "C:/Users/aahav/Downloads/KVForge_Project_Brief.pdf"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

F = "C:/Windows/Fonts/"
pdfmetrics.registerFont(TTFont("Body", F + "arial.ttf"))
pdfmetrics.registerFont(TTFont("Body-Bold", F + "arialbd.ttf"))
pdfmetrics.registerFont(TTFont("Body-Italic", F + "ariali.ttf"))
pdfmetrics.registerFont(TTFont("Mono", F + "consola.ttf"))
pdfmetrics.registerFont(TTFont("Head", F + "georgiab.ttf"))
addMapping("Body", 0, 0, "Body")
addMapping("Body", 1, 0, "Body-Bold")
addMapping("Body", 0, 1, "Body-Italic")
addMapping("Body", 1, 1, "Body-Bold")

INK = colors.HexColor("#0B1220")
TEAL = colors.HexColor("#0F766E")
TEAL_L = colors.HexColor("#CCFBF1")
AMBER_L = colors.HexColor("#FEF3C7")
ROSE_L = colors.HexColor("#FFE4E6")
SLATE = colors.HexColor("#475569")
PALE = colors.HexColor("#EEF2F7")
GRID = colors.HexColor("#CBD5E1")
GREEN = colors.HexColor("#15803D")
GREEN_L = colors.HexColor("#DCFCE7")

S = {
    "title": ParagraphStyle("title", fontName="Head", fontSize=26, leading=31, textColor=INK, spaceAfter=8),
    "subtitle": ParagraphStyle("sub", fontName="Body", fontSize=12.5, leading=17, textColor=SLATE, spaceAfter=4),
    "h1": ParagraphStyle("h1", fontName="Head", fontSize=18, leading=23, textColor=INK, spaceBefore=4, spaceAfter=7),
    "h2": ParagraphStyle("h2", fontName="Body-Bold", fontSize=12.5, leading=16, textColor=TEAL, spaceBefore=9, spaceAfter=4),
    "body": ParagraphStyle("body", fontName="Body", fontSize=10, leading=14.2, textColor=INK, spaceAfter=6),
    "small": ParagraphStyle("small", fontName="Body", fontSize=8.6, leading=11.5, textColor=SLATE, spaceAfter=4),
    "bullet": ParagraphStyle("bullet", fontName="Body", fontSize=10, leading=14, textColor=INK, leftIndent=12, bulletIndent=2, spaceAfter=2.5),
    "cell": ParagraphStyle("cell", fontName="Body", fontSize=8.6, leading=11.2, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="Body-Bold", fontSize=8.6, leading=11.2, textColor=INK),
    "cellh": ParagraphStyle("cellh", fontName="Body-Bold", fontSize=8.8, leading=11.2, textColor=colors.white),
    "code": ParagraphStyle("code", fontName="Mono", fontSize=8.2, leading=10.6, textColor=INK, backColor=PALE, borderPadding=(5, 6, 5, 6), spaceBefore=4, spaceAfter=8),
    "callout": ParagraphStyle("callout", fontName="Body", fontSize=9.6, leading=13.4, textColor=INK, backColor=AMBER_L, borderPadding=(6, 8, 6, 8), spaceBefore=6, spaceAfter=10),
    "note": ParagraphStyle("note", fontName="Body", fontSize=9.6, leading=13.4, textColor=INK, backColor=TEAL_L, borderPadding=(6, 8, 6, 8), spaceBefore=6, spaceAfter=10),
    "warn": ParagraphStyle("warn", fontName="Body", fontSize=9.6, leading=13.4, textColor=INK, backColor=ROSE_L, borderPadding=(6, 8, 6, 8), spaceBefore=6, spaceAfter=10),
    "caption": ParagraphStyle("caption", fontName="Body-Italic", fontSize=8.6, leading=11, textColor=SLATE, alignment=TA_CENTER, spaceBefore=2, spaceAfter=10),
    "big": ParagraphStyle("big", fontName="Head", fontSize=22, leading=26, textColor=TEAL, alignment=TA_CENTER),
    "bigl": ParagraphStyle("bigl", fontName="Body", fontSize=8.6, leading=11, textColor=SLATE, alignment=TA_CENTER),
}
story = []


def P(t, st="body"):
    story.append(Paragraph(t, S[st]))


def H1(t, new_page=False):
    story.append(PageBreak() if new_page else CondPageBreak(60 * mm))
    story.append(Paragraph(t, S["h1"]))


def H2(t):
    story.append(CondPageBreak(30 * mm))
    story.append(Paragraph(t, S["h2"]))


def B(items):
    for it in items:
        story.append(Paragraph(it, S["bullet"], bulletText="\u2022"))
    story.append(Spacer(1, 4))


def CODE(t):
    story.append(XPreformatted(t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), S["code"]))


def BOX(t, kind="callout"):
    story.append(Paragraph(t, S[kind]))


def TABLE(rows, widths, head=True, shade=None):
    data = []
    for i, r in enumerate(rows):
        data.append([Paragraph(c, S["cellh"] if head and i == 0 else S["cellb"] if j == 0 else S["cell"]) for j, c in enumerate(r)])
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if head else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, GRID), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if head:
        st.append(("BACKGROUND", (0, 0), (-1, 0), INK))
    for i in range(1 if head else 0, len(rows)):
        if i % 2 == 0:
            st.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F8FAFC")))
    for (r, c), col in (shade or {}).items():
        st.append(("BACKGROUND", (c, r), (c, r), col))
    t.setStyle(TableStyle(st))
    story.append(t)
    story.append(Spacer(1, 8))


def FIG(rel, width_mm, caption):
    p = os.path.join(ROOT, rel)
    iw, ih = ImageReader(p).getSize()
    story.append(KeepTogether([Image(p, width=width_mm * mm, height=width_mm * mm * ih / iw), Paragraph(caption, S["caption"])]))


def STATS(items):
    cells = [[Paragraph(a, S["big"]) for a, _ in items], [Paragraph(b, S["bigl"]) for _, b in items]]
    w = 174.0 / len(items)
    t = Table(cells, colWidths=[w * mm] * len(items))
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE), ("LINEAFTER", (0, 0), (-2, -1), 2, colors.white),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.append(t)
    story.append(Spacer(1, 10))


# =========================================================================== title
story.append(Spacer(1, 18 * mm))
P("KVForge", "title")
P("A compiler that picks how to store and split the attention cache on a GPU, by predicting instead of trial-and-error", "subtitle")
P("Project brief for the faculty review: the idea, where it stands, what we found, what comes next, and how it compares", "subtitle")
story.append(Spacer(1, 6))
P("Compiler Design, VIT Vellore &nbsp;|&nbsp; Aahav Yadav (24BKT0138), Akshat Kapur (24BDS0318), Rishab Jajodia (24BDS0268) &nbsp;|&nbsp; 15 October 2026", "small")
story.append(Spacer(1, 8))
STATS([("1.96\u00d7", "faster than a naive kernel, same accuracy (live demo, Llama-3-8B layer)"),
       ("3.09\u00d7", "faster under a 2% error budget (int8 cache, 0.8% error, live demo)"),
       ("1.06\u00d7", "FlashInfer's time: within 6% of a leading library (fp16)"),
       ("0.886", "rank correlation on a second GPU, model not retuned")])
BOX("<b>The short version.</b> When a chatbot writes a reply, each new word requires the GPU to re-read a large memory "
    "structure called the <i>KV cache</i>. That reading, not arithmetic, is the bottleneck. There are thousands of ways to store "
    "and split that read (number formats, memory layouts, how work is divided across the GPU's cores), and the fastest one "
    "depends on the GPU and the model. Normally engineers find it by hand or by timing hundreds of candidates on each machine. "
    "KVForge is a compiler: you write a 10-line description with question marks where you want it to decide; it measures the "
    "GPU once (about a minute), <b>predicts</b> the time of every candidate with a bandwidth model, keeps only candidates "
    "within your accuracy budget, picks the best, and generates CUDA code that is compiled, checked against a reference and timed.", "note")
P("<b>Honest position in one line:</b> the compiler beats a straightforward kernel by 2\u20133\u00d7 and lands within 6% of a "
  "leading hand-tuned library, and its model transfers to a second GPU without retuning; it is <b>not</b> faster than the best "
  "existing library, and it was tested only on two laptop GPUs.", "body")

# =========================================================================== 1 story
H1("1. From the start: the idea and how it developed", new_page=True)
TABLE([
    ["Stage", "What happened"],
    ["Starting point", "A CPU prototype (compiler_kv) with a small language for attention-cache layouts. Its front end (lexer, parser, syntax tree, IR) was kept after inspection; the rest was rewritten for GPUs."],
    ["The observation", "In the decode phase each cached byte is read once and used once (reuse = 1). Classic compiler cost models score schedules by data reuse, so for this operator they rate every schedule the same. Yet measured times differ by up to 6.4\u00d7 for plans that move the same bytes. Something other than reuse decides speed."],
    ["The hypothesis (H1)", "What decides speed is <i>bytes moved</i> (number format), <i>how useful each fetched byte is</i> (layout), and <i>how many bytes are in flight across the GPU</i> (partition). A model built from measured bandwidth, latency and occupancy should rank plans correctly without running them."],
    ["What we built", "A compiler (C++), a language (.kv), 288 CUDA kernel variants, a one-minute GPU probe, a sweep harness that times and verifies every plan, and a cost model with 10 constants fitted once."],
    ["How we tested it", "Measured all 20,928 plans on 10 attention shapes on an RTX 5060 Laptop (fit on 7 shapes, tested on 3 held out). Then shipped a package to a teammate's RTX 4060 (a different GPU generation) and ran it with the constants frozen."],
    ["Where it is now", "All planned items for the 70% review are done, plus 3 of the 4 items deferred to the final 30%. The written final report remains."],
], [34, 140])
H2("What the compiler does, on one example")
CODE("""# demo/3_budget.kv : one Llama-3-8B attention layer, 32k tokens of context
target max_rel_err = 0.02          # accuracy budget: permits int8 / int4

decode budget(H: 32, H_kv: 8, d: 128, n: 32768, batch: 1) {
  Q: query<H, d, f32>
  K: kvcache<n, d, ?, ?, ?>        # format, order, residency: compiler decides
  V: kvcache<n, d, ?, ?, ?>
  O = decode_attn(Q, K, V, scale = auto, splits = ?, gqa_pack = ?)
}""")
P("Pipeline: lexer \u2192 parser \u2192 semantic checks \u2192 IR (<font face='Mono'>kvf.decode_attn</font>) \u2192 enumerate 2,688 candidate plans "
  "\u2192 cost model ranks them \u2192 accuracy gate rejects int4 (error 11\u201314% &gt; 2%) \u2192 IR rewritten to "
  "<font face='Mono'>kvf.decode_attn_split</font> with the chosen plan \u2192 CUDA source \u2192 nvcc \u2192 kernel verified and timed. "
  "Chosen here: int8 with 128-element groups, head-major layout, KV split 32 ways, 4 query heads packed per KV head, 8 warps.")

# =========================================================================== 2 progress
H1("2. How it is going: progress against the plan")
TABLE([
    ["Item", "Status", "Evidence"],
    ["Toolchain on a Blackwell GPU", "Done", "CUDA 13.4, MSVC; kernels build for sm_89 and sm_120"],
    ["bw_probe: measure the GPU", "Done", "341 GB/s, 148 ns latency, 32 B sector, 26 SMs (5060)"],
    ["Kernels fp16, int8, int4", "Done", "288 variants; every one verified against a double-precision reference"],
    ["Sweep harness and sweeps", "Done", "20,928 plans \u00d7 10 shapes per GPU; 44,224 verified runs, 0 failures"],
    ["Cost model, fitted and held out", "Done", "10 constants, frozen file; held-out rank correlation 0.88"],
    ["Compiler: spec to verified CUDA", "Done", "7 commands; 19 of 19 smoke tests pass"],
    ["Package for a second GPU", "Done", "ran on the RTX 4060"],
    ["Progress deck", "Done", "33 slides, PDF and PPTX"],
    ["Deferred: transfer test", "Done", "RTX 4060, no refit: \u03c1 0.886"],
    ["Deferred: baselines and libraries", "Done (fp16)", "naive kernel, FlashInfer 0.7.1, PyTorch SDPA"],
    ["Deferred: lossy formats behind a gate", "Done", "int8 0.8% error, int4 11\u201314%"],
    ["Deferred: final written report", "Not done", "results write-up exists (docs/results.md); report text to do"],
], [62, 24, 88], shade={(i, 1): GREEN_L for i in range(1, 12)} | {(12, 1): AMBER_L})

# =========================================================================== 3 findings
H1("3. Our findings")
P("All numbers below were measured on our hardware. \u201cRegret\u201d means how much slower the compiler's pick is than the best plan "
  "found by timing all of them; 0% would be perfect.")
TABLE([
    ["Finding", "Result", "What it means"],
    ["H1: same bytes, different speed", "1.8\u00d7 to 6.4\u00d7 spread among fp16 plans moving identical bytes (5060); 1.1\u00d7 to 4.6\u00d7 (4060)",
     "Reuse-based models cannot see this; a bandwidth/latency/occupancy model can."],
    ["Which choices matter", "Splitting the KV read: up to 58% if wrong. GQA packing: 40%. Number format: 1.8\u00d7. Unroll 11%. Layout \u22648%. Warps \u22480.",
     "Two axes dominate (format, partition). Layout barely matters on these GPUs: a negative finding we report."],
    ["Model accuracy (5060)", "Rank correlation 0.88 on held-out shapes; time error 15%",
     "It orders plans well; absolute times are less exact."],
    ["Pick vs naive kernel (5060)", "1.93\u00d7 (fp16), 3.00\u00d7 (int8 allowed), 3.64\u00d7 (int4 allowed)", "Regret 11.4 / 5.8 / 11.2%."],
    ["Pick vs libraries (5060, fp16)", "1.06\u00d7 FlashInfer's time (0.94\u20131.33\u00d7); PyTorch SDPA 1.02\u00d7; naive 2.12\u00d7",
     "Competitive with expert-tuned code, not faster."],
    ["Transfer to RTX 4060, no retuning", "Rank correlation 0.886; regret 6.6% fp16, 11.8% int8, 16.1% all; 1.5\u20133.2\u00d7 over naive",
     "Pre-set targets met for fp16 and int8, narrowly missed for all formats."],
    ["Controls (4060)", "Copying the 5060's measured winner for the same shape beats the model (2.3/7.1/6.8%). For an unseen shape the model ties a nearest-shape heuristic on average, with a much better worst case (17/42/55% vs 46/61/64%).",
     "The model's value is for shapes nobody has tuned."],
    ["Where it fails", "Shape with 8 query heads per KV head (H64/8): model predicts a tie, measured 200 vs 152 \u00b5s",
     "The 8-head-pack kernel uses 216\u2013250 registers per thread; same kernel trails FlashInfer by 33%."],
], [36, 72, 66])
FIG("results/figs/h1_spread.png", 150, "Figure 1. Same bytes, different runtime: best, median and worst fp16 plan per shape (RTX 5060, log scale).")
FIG("results/figs/compare_library.png", 150, "Figure 2. KVForge's pick against FlashInfer, PyTorch SDPA and the naive kernel, fp16, same GPU, same timer.")
FIG("results/figs_rtx4060/pred_vs_meas.png", 105, "Figure 3. Transfer: predicted vs measured for all 20,928 plans on the RTX 4060 using constants fitted on the RTX 5060.")

# =========================================================================== 4 what to show
H1("4. What to show the professor: demo, executable, benchmarks", new_page=True)
P("Yes, there is a live demo and a working executable. <b>build\\kvf.exe</b> is the compiler; the demo script uses it to compile "
  "one Llama-3-8B attention layer three ways, then compiles and runs each generated kernel on the GPU, checks it against a "
  "reference, and times it. It takes about two minutes on the RTX 5060 laptop.")
CODE("""cd C:\\Users\\aahav\\KVForge
powershell -ExecutionPolicy Bypass -File demo\\run_demo.ps1 -Pause     # Enter moves to the next step""")
P("What it printed today (recorded copy: <font face='Mono'>demo\\demo_output_recorded.txt</font>, use it if the laptop misbehaves):")
TABLE([
    ["Program", "Plan the compiler chose", "Check", "Error vs exact", "Predicted", "Measured", "Speedup"],
    ["1_baseline.kv (all pinned)", "f16, token-major, no split", "PASS", "0.03%", "1168 \u00b5s", "845 \u00b5s", "1.00\u00d7"],
    ["2_lossless.kv (? holes)", "f16, head-major, split 32, pack", "PASS", "0.03%", "425 \u00b5s", "430 \u00b5s", "1.96\u00d7"],
    ["3_budget.kv (+2% budget)", "int8:128, head-major, split 32, pack", "PASS", "0.84%", "313 \u00b5s", "273 \u00b5s", "3.09\u00d7"],
], [38, 50, 13, 19, 18, 18, 18])
H2("Suggested 10-minute order")
TABLE([
    ["Min", "Show", "Say"],
    ["0\u20131", "Progress slide (KVForge_Total_Progress_Slide.pdf)", "70% scope done, 3 of 4 deferred items done, 44,224 verified runs."],
    ["1\u20133", "Deck slides: problem, reuse = 1, the three axes", "Why ordinary compiler cost models go blind here; Figure 1 proves the spread."],
    ["3\u20135", "The three .kv files, then run the demo", "Same layer, three programs; the only difference is question marks and one budget line."],
    ["5\u20136", "out\\demo\\3_budget\\report.txt", "The compiler's reasoning: predicted bytes, bandwidth, why int4 was rejected, the IR before and after."],
    ["6\u20138", "Deck: library comparison and transfer slides", "Within 6% of FlashInfer; model moved to a second GPU without retuning."],
    ["8\u201310", "Deck: failure slide and open items", "Where it fails and why; what the final 30% delivers."],
], [12, 66, 96])
H2("Questions to expect, with honest answers")
TABLE([
    ["Question", "Answer"],
    ["Is this faster than FlashInfer?", "No. 6% slower on average, 6% faster on one shape, 33% slower on one. The claim is prediction without per-GPU tuning, not a faster kernel."],
    ["Where is the compiler part?", "Lexer, parser, semantic checks and an SSA-style IR; a search pass over plans driven by a cost model; an accuracy-gate pass; a rewrite of the IR to the chosen plan; CUDA code generation. It is a domain-specific compiler."],
    ["Why not just autotune?", "Autotuning times hundreds of candidates on every GPU and every shape. The model predicts in milliseconds after a one-minute probe. On a GPU where a shape was already tuned, copying that winner is better; the model is for new shapes and new machines."],
    ["Is int8 safe for accuracy?", "Measured error is 0.8% against exact attention on synthetic data. Accuracy on a real model's text output (perplexity) is not yet measured; that is planned."],
    ["Did you test on server GPUs?", "No. Two laptop GPUs (Blackwell and Ada). A dissimilar GPU is a planned deliverable."],
], [44, 130])

# =========================================================================== 5 deliverables
H1("5. Planned deliverables and how feasible they are")
P("Effort figures are our estimates for a team of three, not measurements.")
TABLE([
    ["Deliverable", "Why", "Effort", "Feasibility", "Risk"],
    ["Final written report", "Course requirement; the results exist", "3\u20135 days", "High", "None technical"],
    ["Fix the 8-head-pack kernel", "Only failing shape; trails FlashInfer there", "2\u20134 days", "Medium-high", "Fix may cut registers but not time"],
    ["Model the slow split counts", "Some split counts run slower than neighbours", "about 1 week", "Medium", "Cause not yet isolated"],
    ["int8 accuracy on a real model", "Synthetic error is not model quality", "about 1 week", "Medium-high", "Needs a small open model (1\u20133 GB) in WSL"],
    ["Test on a dissimilar GPU", "Transfer shown only on two similar cards", "2\u20133 days + access", "Medium", "Needs rented or lab GPU time; a server GPU needs a new build target"],
    ["fp8 cache format", "Native on Ada and Blackwell", "1\u20132 weeks", "Medium", "New kernels and accuracy data"],
    ["Plug into a real serving engine", "End-to-end tokens/s", "several weeks", "Low this semester", "Engineering, not research"],
], [40, 46, 26, 24, 38])
BOX("<b>Our view:</b> the first four are realistic within the semester; they turn the project from \u201cworks on two laptops\u201d "
    "into a complete study. Testing a server GPU depends on access. fp8 and engine integration are stretch goals.", "note")

# =========================================================================== 6 distinct
H1("6. What makes it different from existing work and products")
P("We searched arXiv (titles and abstracts, keyword queries up to October 2026) and checked 30 papers; full texts and patent "
  "databases were not searched. Products in use today, such as vLLM, SGLang and TensorRT-LLM, rely on hand-written attention "
  "kernels (FlashAttention, FlashInfer) chosen by built-in heuristics, or on autotuning.")
TABLE([
    ["Approach", "Example", "How it picks a configuration", "Difference from KVForge"],
    ["Hand-tuned kernels", "FlashInfer, FlashDecoding++", "Experts tune per GPU; heuristic selection", "Fixed menu; new GPU means new tuning. Faster than us today."],
    ["Measured autotuning", "AutoTVM, Ansor, Triton autotune", "Time many candidates on each machine", "Accurate but costs trials per GPU and per shape; does not explain why."],
    ["Reuse-based compiler models", "Halide, TVM tiling, TileLang", "Score schedules by data reuse", "Blind here: reuse is 1 for every decode schedule."],
    ["Calibrated decode policy", "PersistentKV (2026, arXiv 2606.26666)", "Roofline-style model, one RTX 3060, fp16", "Closest prior art. Partition only, one GPU; we add format and layout, an accuracy gate, code generation and a cross-GPU test."],
    ["Tuning-free compilation", "Loom (2026, arXiv 2609.29219)", "Solves schedules symbolically", "Shows transfer across hardware generations, but on Tenstorrent chips and not for attention."],
    ["Low-bit KV caches", "KIVI, KVQuant, QServe, BitDecoding", "Fixed format chosen by authors", "We choose the format per shape and GPU, behind an accuracy budget."],
], [30, 34, 46, 64])
P("<b>What is distinct:</b> (1) one analytic model that scores number format, layout and partition together and picks without "
  "running candidates; (2) an accuracy budget written in the program that decides which lossy formats are allowed; "
  "(3) a compiler that emits verified CUDA for the pick; (4) a measured test that the model, fitted on one GPU generation, "
  "ranks plans on another without retuning.")
P("<b>What is not distinct:</b> each ingredient exists separately: bandwidth roofline models, split-KV decoding, GQA packing, "
  "group-wise int8/int4 caches. Our novelty is the combination and the transfer evidence; we rate it as moderate.")

# =========================================================================== 7 patent
H1("7. Is it patentable?")
BOX("<b>Short answer: possibly in a narrow form, but we do not recommend making a patent the goal.</b> This is our reading of the "
    "general rules, not legal advice; the university's IPR or patent cell should be asked before anything is filed.", "warn")
B(["<b>Indian law excludes software and algorithms as such.</b> Section 3(k) of the Patents Act, 1970 excludes \u201ca mathematical or "
   "business method or a computer programme per se or algorithms\u201d. A claim would have to be framed as a technical method that "
   "improves the hardware's operation (less memory traffic, lower latency on the GPU), not as a cost model.",
   "<b>Inventive step is the weak point.</b> PersistentKV (calibrated decode policy), autotuning compilers and group-wise KV "
   "quantization already exist. An examiner could see our method as an obvious combination of them. The strongest candidate "
   "claim is the narrow one: selecting format and partition jointly from a short hardware probe, under a declared accuracy "
   "budget, without per-device trials.",
   "<b>Prior art not yet searched:</b> we have not searched patent databases (Google Patents, Indian Patent Office, WIPO). "
   "That search is needed before any decision.",
   "<b>Timing matters.</b> Publishing a paper, an arXiv preprint or a public talk before filing can count against novelty. "
   "If the team wants to keep the patent option open, a provisional application must be filed <i>before</i> any public "
   "disclosure. A course presentation to faculty is usually not treated as public, but confirm this with the IPR cell.",
   "<b>Cost and value.</b> Filing and prosecution cost money and years; for a student research result a publication usually "
   "gives more value (credit, citations, a record for higher studies) for less effort."])

# =========================================================================== 8 publication
H1("8. Can it become a conference or journal paper?")
P("<b>Yes, with clear limits on where.</b> As it stands (two laptop GPUs, synthetic data, not faster than the best library) it is "
  "a solid workshop or student-research paper. A main-track compiler or systems venue would need the planned deliverables.")
TABLE([
    ["Level", "Examples", "What we would need"],
    ["Now (after the report)", "Student research competitions (ACM SRC at compiler or PL conferences); workshops on compilers for ML or ML systems held with CGO, ASPLOS, MLSys or ISCA; student symposia such as the one at IEEE HiPC (India)",
     "The report, cleaned figures, the honest comparison with FlashInfer, and the transfer result."],
    ["With the semester's deliverables", "Mid-tier conferences and journals: ACM CC (Compiler Construction), LCTES, Journal of Systems Architecture, Concurrency and Computation: Practice and Experience",
     "Real-model accuracy, the fixed 8-head kernel, a third, dissimilar GPU, and ablation of the model's terms."],
    ["Stretch", "CGO, PACT main track; ACM TACO",
     "Several GPU classes including a server GPU, end-to-end tokens per second in a serving engine, and a clear win over autotuning cost."],
], [36, 76, 62])
P("Deadlines and calls for papers change every year; check each venue's current call before planning. Note the interaction with "
  "section 7: submitting a paper is a public disclosure for patent purposes.", "small")

# =========================================================================== 9 files
H1("9. What to bring and where it is")
TABLE([
    ["File", "Use"],
    ["Downloads\\KVForge_Total_Progress_Slide.pdf", "One slide: progress against the plan"],
    ["Downloads\\KVForge_Progress_Review_Deck.pdf / ..._v3.pptx", "Full 33-slide deck with all results"],
    ["Downloads\\KVForge_Project_Brief.pdf", "This document"],
    ["Downloads\\KVForge_Deep_Dive_Guide.pdf", "19-page reference: how every part works, glossary"],
    ["KVForge\\demo\\run_demo.ps1", "Live demo: plan, compile, verify, time three programs"],
    ["KVForge\\demo\\demo_output_recorded.txt", "Recorded demo output, if the live run fails"],
    ["KVForge\\build\\kvf.exe", "The compiler (plan, roofline, machine, calibrate, predict, evaluate)"],
    ["KVForge\\docs\\results.md", "All measured results with method notes"],
    ["KVForge\\results\\", "Raw sweeps (both GPUs), predictions, figures"],
], [86, 88])


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Body", 7.5)
    canvas.setFillColor(SLATE)
    if doc.page > 1:
        canvas.drawString(18 * mm, 10 * mm, "KVForge | Project brief | Compiler Design, VIT Vellore")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, str(doc.page))
    canvas.restoreState()


doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
                        title="KVForge project brief", author="Aahav Yadav, Akshat Kapur, Rishab Jajodia")
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print("wrote", OUT)
