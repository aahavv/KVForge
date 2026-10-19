"""Build the KVForge deep-dive guide as a PDF.

    python docs/make_guide_pdf.py [output.pdf]

Default output: C:/Users/aahav/Downloads/KVForge_Deep_Dive_Guide.pdf

Every number marked "measured" comes from this project's own runs on the RTX 5060
Laptop GPU (machines/rtx5060-laptop.gpu, results/). Numbers marked "typical" are
architecture figures from vendor documentation and were not measured here.
"""
import os
import sys

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping
from reportlab.platypus import (CondPageBreak, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle, XPreformatted)

OUT = sys.argv[1] if len(sys.argv) > 1 else "C:/Users/aahav/Downloads/KVForge_Deep_Dive_Guide.pdf"

# ------------------------------------------------------------------ fonts
F = "C:/Windows/Fonts/"
pdfmetrics.registerFont(TTFont("Body", F + "arial.ttf"))
pdfmetrics.registerFont(TTFont("Body-Bold", F + "arialbd.ttf"))
pdfmetrics.registerFont(TTFont("Body-Italic", F + "ariali.ttf"))
pdfmetrics.registerFont(TTFont("Mono", F + "consola.ttf"))
pdfmetrics.registerFont(TTFont("Mono-Bold", F + "consolab.ttf"))
pdfmetrics.registerFont(TTFont("Head", F + "georgiab.ttf"))
addMapping("Body", 0, 0, "Body")
addMapping("Body", 1, 0, "Body-Bold")
addMapping("Body", 0, 1, "Body-Italic")
addMapping("Body", 1, 1, "Body-Bold")
addMapping("Mono", 0, 0, "Mono")
addMapping("Mono", 1, 0, "Mono-Bold")
addMapping("Mono", 0, 1, "Mono")
addMapping("Mono", 1, 1, "Mono-Bold")

INK = colors.HexColor("#0B1220")
TEAL = colors.HexColor("#0F766E")
TEAL_L = colors.HexColor("#CCFBF1")
AMBER = colors.HexColor("#F59E0B")
AMBER_L = colors.HexColor("#FEF3C7")
INDIGO = colors.HexColor("#4F46E5")
INDIGO_L = colors.HexColor("#E0E7FF")
ROSE = colors.HexColor("#BE123C")
ROSE_L = colors.HexColor("#FFE4E6")
SLATE = colors.HexColor("#475569")
PALE = colors.HexColor("#EEF2F7")
GRID = colors.HexColor("#CBD5E1")
GREEN = colors.HexColor("#15803D")
GREEN_L = colors.HexColor("#DCFCE7")

S = {
    "title": ParagraphStyle("title", fontName="Head", fontSize=26, leading=31, textColor=INK, spaceAfter=10),
    "subtitle": ParagraphStyle("sub", fontName="Body", fontSize=13, leading=18, textColor=SLATE, spaceAfter=6),
    "h1": ParagraphStyle("h1", fontName="Head", fontSize=19, leading=24, textColor=INK, spaceBefore=4, spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName="Body-Bold", fontSize=13, leading=17, textColor=TEAL, spaceBefore=10, spaceAfter=4),
    "h3": ParagraphStyle("h3", fontName="Body-Bold", fontSize=11, leading=14, textColor=INK, spaceBefore=6, spaceAfter=2),
    "body": ParagraphStyle("body", fontName="Body", fontSize=10, leading=14.2, textColor=INK, spaceAfter=6),
    "small": ParagraphStyle("small", fontName="Body", fontSize=8.6, leading=11.5, textColor=SLATE, spaceAfter=4),
    "bullet": ParagraphStyle("bullet", fontName="Body", fontSize=10, leading=14, textColor=INK, leftIndent=12, bulletIndent=2, spaceAfter=2.5),
    "cell": ParagraphStyle("cell", fontName="Body", fontSize=8.6, leading=11.2, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="Body-Bold", fontSize=8.6, leading=11.2, textColor=INK),
    "cellh": ParagraphStyle("cellh", fontName="Body-Bold", fontSize=8.8, leading=11.2, textColor=colors.white),
    "code": ParagraphStyle("code", fontName="Mono", fontSize=8.2, leading=10.6, textColor=INK, backColor=PALE, borderPadding=(5, 6, 5, 6), spaceBefore=4, spaceAfter=8),
    "callout": ParagraphStyle("callout", fontName="Body", fontSize=9.6, leading=13.4, textColor=INK, backColor=AMBER_L, borderPadding=(6, 8, 6, 8), spaceBefore=6, spaceAfter=10),
    "note": ParagraphStyle("note", fontName="Body", fontSize=9.6, leading=13.4, textColor=INK, backColor=TEAL_L, borderPadding=(6, 8, 6, 8), spaceBefore=6, spaceAfter=10),
    "caption": ParagraphStyle("caption", fontName="Body-Italic", fontSize=8.6, leading=11, textColor=SLATE, alignment=TA_CENTER, spaceBefore=2, spaceAfter=10),
}

story = []


def P(t, st="body"):
    story.append(Paragraph(t, S[st]))


def H1(t):
    story.append(CondPageBreak(60 * mm))
    story.append(Paragraph(t, S["h1"]))


def H2(t):
    story.append(CondPageBreak(30 * mm))
    story.append(Paragraph(t, S["h2"]))


def H3(t):
    story.append(Paragraph(t, S["h3"]))


def B(items):
    for it in items:
        story.append(Paragraph(it, S["bullet"], bulletText="\u2022"))
    story.append(Spacer(1, 4))


def CODE(t):
    story.append(XPreformatted(t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), S["code"]))


def CALLOUT(t, kind="callout"):
    story.append(Paragraph(t, S[kind]))


def TABLE(rows, widths, head=True, zebra=True, bold_first=True):
    data = []
    for i, r in enumerate(rows):
        row = []
        for j, c in enumerate(r):
            if head and i == 0:
                row.append(Paragraph(c, S["cellh"]))
            elif bold_first and j == 0:
                row.append(Paragraph(c, S["cellb"]))
            else:
                row.append(Paragraph(c, S["cell"]))
        data.append(row)
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if head else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if head:
        style.append(("BACKGROUND", (0, 0), (-1, 0), INK))
    if zebra:
        for i in range(1 if head else 0, len(rows)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F8FAFC")))
    t.setStyle(TableStyle(style))
    story.append(t)
    story.append(Spacer(1, 8))


def FIG(drawing, caption):
    story.append(KeepTogether([drawing, Paragraph(caption, S["caption"])]))


# ------------------------------------------------------------------ drawing helpers
def arrow(d, x1, y1, x2, y2, color=SLATE, w=1.2):
    d.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=w))
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    L = 6
    p1 = (x2 - L * math.cos(a - 0.4), y2 - L * math.sin(a - 0.4))
    p2 = (x2 - L * math.cos(a + 0.4), y2 - L * math.sin(a + 0.4))
    d.add(Polygon([x2, y2, p1[0], p1[1], p2[0], p2[1]], fillColor=color, strokeColor=color, strokeWidth=0.5))


def box(d, x, y, w, h, fill, title, sub=None, tcolor=colors.white, tsize=9, ssize=7.2, scolor=None):
    d.add(Rect(x, y, w, h, rx=4, ry=4, fillColor=fill, strokeColor=None))
    if sub:
        d.add(String(x + w / 2, y + h / 2 + 2.5, title, fontName="Body-Bold", fontSize=tsize, fillColor=tcolor, textAnchor="middle"))
        d.add(String(x + w / 2, y + h / 2 - 8.5, sub, fontName="Body", fontSize=ssize, fillColor=scolor or tcolor, textAnchor="middle"))
    else:
        d.add(String(x + w / 2, y + h / 2 - 3, title, fontName="Body-Bold", fontSize=tsize, fillColor=tcolor, textAnchor="middle"))


def label(d, x, y, text, size=7.5, color=SLATE, anchor="start", bold=False):
    d.add(String(x, y, text, fontName="Body-Bold" if bold else "Body", fontSize=size, fillColor=color, textAnchor=anchor))


W = 174 * mm  # usable width


def fig_whole_system():
    h = 330
    d = Drawing(W, h)
    levels = [
        ("SSD (disk)", "model file lives here; read once at load", SLATE, colors.white),
        ("System RAM", "model staged here by the program", SLATE, colors.white),
        ("PCIe link", "copies weights into the GPU at load time", SLATE, colors.white),
        ("VRAM: 8.5 GB GDDR7", "weights + KV cache. 341 GB/s (measured)", INDIGO, colors.white),
        ("L2 cache: 32 MB", "shared by all 26 SMs. 1,581 GB/s (measured)", INDIGO, colors.white),
        ("SM x 26", "where kernels run; blocks of threads", TEAL, colors.white),
        ("L1 / shared memory", "per SM; our merge step uses shared memory", TEAL, colors.white),
        ("Register file", "64K x 32-bit per SM (measured); fastest storage", TEAL, colors.white),
        ("CUDA cores, SFU, tensor cores", "do the adds, multiplies, exp2", AMBER, INK),
    ]
    bw, bh, gap = 240, 26, 9
    x = 10
    y = h - bh - 6
    for i, (t, s, c, tc) in enumerate(levels):
        box(d, x, y, bw, bh, c, t, s, tcolor=tc, tsize=8.6, ssize=6.8)
        if i < len(levels) - 1:
            arrow(d, x + bw / 2, y, x + bw / 2, y - gap + 1)
        y -= bh + gap
    # right side annotations
    rx = 275
    label(d, rx, h - 20, "LOAD TIME (once)", 8.5, INK, bold=True)
    label(d, rx, h - 33, "disk -> RAM -> PCIe -> VRAM", 7.5)
    label(d, rx, h - 45, "Not touched again while generating.", 7.5)
    d.add(Line(rx - 8, h - 8, rx - 8, h - 105, strokeColor=GRID, strokeWidth=2))
    label(d, rx, h - 125, "EVERY TOKEN (decode loop)", 8.5, INK, bold=True)
    label(d, rx, h - 138, "VRAM -> L2 -> SM -> registers -> cores", 7.5)
    label(d, rx, h - 150, "All weights and the whole KV cache", 7.5)
    label(d, rx, h - 162, "travel this path once per token.", 7.5)
    d.add(Line(rx - 8, h - 112, rx - 8, h - 322, strokeColor=TEAL, strokeWidth=2))
    label(d, rx, h - 190, "KVForge works here:", 8.5, TEAL, bold=True)
    label(d, rx, h - 203, "it decides how the KV cache is stored", 7.5)
    label(d, rx, h - 215, "in VRAM and how it is streamed through", 7.5)
    label(d, rx, h - 227, "L2 into the SMs' registers.", 7.5)
    label(d, rx, h - 255, "Speed limit of decode = this arrow:", 8.5, ROSE, bold=True)
    label(d, rx, h - 268, "VRAM bandwidth (341 GB/s here).", 7.5)
    label(d, rx, h - 280, "The cores are mostly waiting for it.", 7.5)
    return d


def fig_layer():
    h = 360
    d = Drawing(W, h)
    steps = [
        ("x: one token, 4096 numbers", None, PALE, INK),
        ("RMSNorm", "rescale the vector", SLATE, colors.white),
        ("Q, K, V projections", "x times W_Q, W_K, W_V (weights in VRAM)", INDIGO, colors.white),
        ("Split into heads + RoPE", "32 query heads, 8 K/V heads, 128 numbers each", INDIGO, colors.white),
        ("Append k, v to the KV cache", "the cache grows by one token", TEAL, colors.white),
        ("ATTENTION over the cache", "scores, softmax, weighted sum of V  <- KVForge", ROSE, colors.white),
        ("Output projection W_O + residual add", "merge the 32 heads back to 4096", INDIGO, colors.white),
        ("RMSNorm + feed-forward (SwiGLU)", "W_gate, W_up (4096 x 14336), W_down", INDIGO, colors.white),
        ("Residual add -> next layer", "repeat for all 32 layers", SLATE, colors.white),
    ]
    bw, bh, gap = 300, 28, 9
    x = (W - bw) / 2 - 60
    y = h - bh - 4
    for i, (t, s, c, tc) in enumerate(steps):
        box(d, x, y, bw, bh, c, t, s, tcolor=tc, tsize=8.8, ssize=7)
        if i < len(steps) - 1:
            arrow(d, x + bw / 2, y, x + bw / 2, y - gap + 1)
        y -= bh + gap
    rx = x + bw + 16
    label(d, rx, h - 190, "Uses the weights:", 8, INK, bold=True)
    label(d, rx, h - 202, "matrix x vector, reads", 7.3)
    label(d, rx, h - 213, "every weight once per token", 7.3)
    label(d, rx, h - 240, "Uses the KV cache:", 8, ROSE, bold=True)
    label(d, rx, h - 252, "vector x every cached token,", 7.3)
    label(d, rx, h - 263, "reads the whole cache once", 7.3)
    label(d, rx, h - 274, "per token. Grows with context.", 7.3)
    return d


def fig_pipeline():
    h = 175
    d = Drawing(W, h)
    row1 = [("Spec .kv", "your input"), ("Lexer", "src/lexer.cpp"), ("Parser", "src/parser.cpp"), ("Semantics + IR", "src/ir.cpp"), ("Enumerate", "src/plan.cpp")]
    row2 = [("Cost model", "src/cost.cpp"), ("Gate + rewrite", "src/passes.cpp"), ("Codegen", "src/codegen.cpp"), ("nvcc", "tools/nvcc.cmd"), ("GPU run", "runtime/*.cuh")]
    bw, bh = 86, 40
    gx = (W - 5 * bw) / 4
    y1, y2 = h - bh - 10, h - 2 * bh - 55
    cols = [SLATE, INDIGO, INDIGO, INDIGO, TEAL]
    for i, (t, s) in enumerate(row1):
        x = i * (bw + gx)
        box(d, x, y1, bw, bh, cols[i], t, s, tsize=8.6, ssize=6.8)
        if i < 4:
            arrow(d, x + bw, y1 + bh / 2, x + bw + gx - 1, y1 + bh / 2)
    cols2 = [TEAL, TEAL, AMBER, AMBER, ROSE]
    for i, (t, s) in enumerate(row2):
        x = i * (bw + gx)
        box(d, x, y2, bw, bh, cols2[i], t, s, tsize=8.6, ssize=6.8, tcolor=INK if cols2[i] == AMBER else colors.white)
        if i < 4:
            arrow(d, x + bw, y2 + bh / 2, x + bw + gx - 1, y2 + bh / 2)
    # connector from row1 end to row2 start
    xe = 4 * (bw + gx) + bw / 2
    d.add(Line(xe, y1, xe, y1 - 14, strokeColor=SLATE, strokeWidth=1.2))
    d.add(Line(xe, y1 - 14, bw / 2, y1 - 14, strokeColor=SLATE, strokeWidth=1.2))
    arrow(d, bw / 2, y1 - 14, bw / 2, y2 + bh + 1)
    label(d, 0, 8, "FRONT END (blue): reads and checks the program.   MIDDLE (teal): decides the plan.   BACK END (amber/red): makes and runs GPU code.", 7.3)
    return d


def fig_sm():
    h = 250
    d = Drawing(W, h)
    d.add(Rect(0, 30, W, h - 34, rx=6, ry=6, fillColor=PALE, strokeColor=GRID))
    label(d, 8, h - 18, "One SM (Streaming Multiprocessor). Your GPU has 26 of these.", 9, INK, bold=True)
    pw, ph = (W - 50) / 4, 120
    for i in range(4):
        x = 10 + i * (pw + 10)
        y = 95
        d.add(Rect(x, y, pw, ph, rx=4, ry=4, fillColor=colors.white, strokeColor=GRID))
        label(d, x + pw / 2, y + ph - 13, "Partition %d" % i, 8, INK, "middle", True)
        parts = [("L0 instruction cache", SLATE), ("Warp scheduler", INDIGO), ("Register file (1/4)", TEAL), ("32 FP32 lanes", AMBER), ("SFU (exp2)  LD/ST", ROSE), ("Tensor core", GREEN)]
        for k, (t, c) in enumerate(parts):
            box(d, x + 5, y + ph - 31 - k * 16, pw - 10, 13, c, t, tsize=6.8, tcolor=INK if c == AMBER else colors.white)
    box(d, 10, 50, W - 20, 30, INDIGO_L, "L1 data cache + shared memory (per SM, shared by its 4 partitions)", "our kernel's merge step writes partial results here (STS) and reads them back (LDS)", tcolor=INK, tsize=8.4, ssize=7, scolor=SLATE)
    label(d, 8, 12, "Partition layout and the L1/shared size are typical for this GPU family (vendor documentation), not measured. Measured: 48 warps and 65,536 registers per SM.", 7, SLATE)
    return d


def fig_warp():
    h = 150
    d = Drawing(W, h)
    label(d, 0, h - 12, "One warp = 32 lanes. With d = 128 and fp16, 16 lanes cooperate on one token; each lane holds 8 numbers (16 bytes).", 8, INK, bold=True)
    cw = (W - 10) / 32
    for i in range(32):
        c = TEAL if i < 16 else INDIGO
        d.add(Rect(5 + i * cw, h - 50, cw - 2, 24, fillColor=c, strokeColor=None))
        label(d, 5 + i * cw + (cw - 2) / 2, h - 42, str(i), 6.2, colors.white, "middle")
    label(d, 5 + 8 * cw, h - 64, "lanes 0-15: token t", 8, TEAL, "middle", True)
    label(d, 5 + 24 * cw, h - 64, "lanes 16-31: token t+1", 8, INDIGO, "middle", True)
    # a K row
    rw = (W - 10) / 16
    for i in range(16):
        d.add(Rect(5 + i * rw, h - 112, rw - 2, 22, fillColor=TEAL_L, strokeColor=TEAL, strokeWidth=0.5))
        label(d, 5 + i * rw + (rw - 2) / 2, h - 104, "8 nums", 6.3, INK, "middle")
    label(d, 5, h - 128, "One K row of token t: 128 fp16 numbers = 256 bytes = 8 memory sectors of 32 bytes. Lane i loads bytes 16i..16i+15 in ONE instruction (LDG.E.EF.128).", 7.5)
    label(d, 5, h - 140, "Each lane multiplies its 8 numbers by its 8 query numbers, then the 16 lanes add their partial sums with 4 shuffle steps (SHFL.BFLY).", 7.5)
    return d


def fig_grid():
    h = 175
    d = Drawing(W, h)
    label(d, 0, h - 12, "The launch grid for the example plan: 32 splits x 8 KV heads x 1 sequence = 256 blocks of 256 threads (8 warps).", 8, INK, bold=True)
    cw, ch = 9.5, 9.5
    for hk in range(8):
        for sp in range(32):
            c = [TEAL, INDIGO, AMBER, ROSE, GREEN, SLATE, TEAL, INDIGO][hk]
            d.add(Rect(10 + sp * (cw + 1.2), h - 32 - hk * (ch + 1.5), cw, ch, fillColor=c, strokeColor=None))
    label(d, 10, h - 32 - 8 * (ch + 1.5) - 4, "x: split (chunk of 1,024 tokens each)   y: KV head (each block serves its 4 query heads: GQA packing)", 7.3)
    sx = 10 + 32 * (cw + 1.2) + 18
    arrow(d, sx - 12, h - 70, sx + 6, h - 70)
    label(d, sx + 10, h - 40, "Block scheduler", 8.5, INK, bold=True)
    label(d, sx + 10, h - 52, "hands blocks to the 26 SMs.", 7.5)
    label(d, sx + 10, h - 64, "An SM holds only as many", 7.5)
    label(d, sx + 10, h - 76, "blocks as its registers allow;", 7.5)
    label(d, sx + 10, h - 88, "the rest wait for a free slot.", 7.5)
    label(d, sx + 10, h - 100, "Rounds of blocks = 'waves'.", 7.5)
    return d


def fig_load():
    h = 120
    d = Drawing(W, h)
    stops = [("Lane issues LDG", "register gets a request", TEAL), ("LD/ST unit + L1", "miss: data not on the SM", TEAL), ("Crossbar", "on-chip network", SLATE), ("L2 slice", "32 MB, shared", INDIGO), ("Memory controller", "queues requests", INDIGO), ("GDDR7 DRAM", "returns 32 B sectors", ROSE)]
    bw = (W - 5 * 10) / 6
    for i, (t, s, c) in enumerate(stops):
        x = i * (bw + 10)
        box(d, x, 55, bw, 40, c, t, s, tsize=7.6, ssize=6.4)
        if i < 5:
            arrow(d, x + bw, 80, x + bw + 9, 80)
            arrow(d, x + bw + 9, 66, x + bw, 66, color=TEAL)
    label(d, 0, 38, "Request travels right (grey); data comes back left (teal) into the lane's register. Idle round trip: 148 ns (measured). Under load it behaves ~8x longer", 7.4)
    label(d, 0, 26, "(fitted). While one warp waits, the scheduler runs other warps: that is latency hiding, and why bytes in flight matter (Little's law).", 7.4)
    return d


# ================================================================== CONTENT
# ---------------- title
story.append(Spacer(1, 40 * mm))
story.append(Paragraph("From words to silicon", S["title"]))
story.append(Paragraph("A deep-dive reference for KVForge: how a large language model runs on an RTX 5060 Laptop GPU, layer by layer and down to the individual machine instructions, and where every piece of our code fits", S["subtitle"]))
story.append(Spacer(1, 10 * mm))
TABLE([
    ["Project", "KVForge: a bandwidth-model-driven compiler for GPU decode-phase attention"],
    ["Course", "Compiler Design, VIT Vellore"],
    ["Team", "Aahav Yadav (24BKT0138), Akshat Kapur (24BDS0318), Rishab Jajodia (24BDS0268)"],
    ["Hardware", "NVIDIA GeForce RTX 5060 Laptop GPU (Blackwell, compute capability 12.0, 26 SMs, 8.5 GB)"],
    ["Code", "C:\\Users\\aahav\\KVForge"],
    ["Date", "15 October 2026"],
], [32, 142], head=False, zebra=False)
story.append(Spacer(1, 8 * mm))
CALLOUT("<b>How to read this guide.</b> It assumes only that you know an LLM has weights, takes words, turns them into numbers, and produces words. "
        "Part 1 is the whole picture on one page. Part 2 is the model. Part 3 is the hardware. Part 4 is how code reaches the hardware. "
        "Part 5 follows KVForge from its input to the transistors and back. Part 6 lists every command we run and what it captures. "
        "Part 7 maps every file to the layer it controls. Part 8 is the glossary. Numbers marked <b>measured</b> come from our own runs on your laptop; "
        "numbers marked <b>typical</b> are from vendor documentation and were not measured.")
story.append(PageBreak())

# ---------------- contents
H1("Contents")
TABLE([
    ["Part", "What it covers"],
    ["1. The whole picture", "Every layer from disk to the arithmetic units, on one diagram, and where KVForge sits"],
    ["2. The model", "Words to tokens to vectors, one transformer layer in detail, attention heads, the KV cache, prefill and decode"],
    ["3. The hardware", "SSD, RAM, PCIe, VRAM (GDDR7 vs HBM), L2, SMs, partitions, L0/L1, shared memory, registers, CUDA and tensor cores"],
    ["4. Code to silicon", "CUDA, nvcc, PTX, SASS, kernels, grids, blocks, warps, threads, scheduling, occupancy"],
    ["5. KVForge end to end", "Spec, front end, cost model, code generation, then the life of one block down to individual instructions, and back to the output"],
    ["6. What we measure", "Every command, what it captures, and which file it writes"],
    ["7. Code map", "Every source file and the layer of the system it controls"],
    ["8. Glossary", "Every term in this project, A to Z"],
    ["9. Honest limits", "What this project does not cover, and what is not yet measured"],
], [42, 132])
story.append(PageBreak())

# ---------------- part 1
H1("1. The whole picture")
P("A language model on your laptop is three things stacked on top of each other: <b>the model</b> (a long list of numbers called weights, plus a recipe for using them), "
  "<b>the software</b> that follows the recipe (Python, PyTorch, CUDA kernels such as ours), and <b>the hardware</b> that physically does the arithmetic (the GPU). "
  "The diagram below shows where data lives and how it moves when the model writes one token.")
FIG(fig_whole_system(), "Figure 1. The storage hierarchy of your laptop, slowest and largest at the top, fastest and smallest at the bottom. Numbers from bw_probe on your GPU.")
P("Two facts carry the whole project:")
B([
    "<b>Generating each new token reads every weight and the whole KV cache once.</b> For an 8-billion-parameter model that is several gigabytes per token.",
    "<b>The GPU can do arithmetic far faster than it can read memory.</b> Your GPU does about 16 trillion floating-point operations per second (measured; 8 trillion multiply-adds) but reads only 341 GB per second (measured). "
    "So while generating, the arithmetic units mostly wait for data. The step is <b>memory-bound</b>.",
])
CALLOUT("KVForge lives in the part of the diagram from VRAM down to the cores, for one specific step: <b>attention over the KV cache during decode</b>. "
        "It chooses how the cache is stored (format and layout) and how the work is cut up (partition), using a model of how fast bytes can move on this GPU, "
        "and it writes the GPU code for its choice.", "note")

H2("1.1 The control flow of one generated token, in one table")
P("Every step a chat program performs to write one token, where it physically runs, and whose code does it. Only one row is ours; the project exists to make that row fast.")
TABLE([
    ["#", "Step", "Runs on", "What physically happens", "Whose code"],
    ["1", "You type a prompt", "CPU", "Text sits in system RAM", "the chat program"],
    ["2", "Tokenize", "CPU", "Text cut into integer token ids", "the tokenizer library"],
    ["3", "Embedding lookup", "GPU", "One 4,096-number row copied from the embedding table in VRAM", "framework kernel"],
    ["4", "Per layer: norm, Q/K/V projections", "GPU (SMs)", "Matrix x vector: every weight streamed from VRAM through L2 into registers once", "framework / cuBLAS kernels"],
    ["5", "Per layer: append k, v to the cache", "GPU", "A few KB written to VRAM", "framework kernel"],
    ["6", "<b>Per layer: attention over the KV cache</b>", "<b>GPU (SMs)</b>", "<b>The whole cache streamed from VRAM; dot products, softmax, weighted sum in registers</b>", "<b>KVForge: plan chosen by kvf (src/), kernel in runtime/kvf_kernels.cuh</b>"],
    ["7", "Per layer: output projection, feed-forward", "GPU (SMs)", "More matrix x vector over weights", "framework / cuBLAS kernels"],
    ["8", "LM head, logits, sampling", "GPU, then CPU", "4,096 x 128,256 matrix x vector; pick one id", "framework"],
    ["9", "Detokenize and print", "CPU", "Id back to text", "the tokenizer, the chat program"],
], [6, 40, 22, 62, 44])
P("In this project we run step 6 on its own, with synthetic data of the right shape, so it can be measured precisely. Steps 1 to 5 and 7 to 9 are described so the step makes sense; we do not run them.", "small")
story.append(PageBreak())

# ---------------- part 2
H1("2. The model: words to numbers to words")
P("We use a model shaped like <b>Llama-3-8B</b> as the example throughout, because the project's shapes come from it: 32 layers, a hidden size of 4,096 numbers, "
  "32 query heads and 8 key/value heads of 128 numbers each, a feed-forward size of 14,336, and a vocabulary of 128,256 tokens. "
  "KVForge itself never loads a real model; it optimises one step that every such model performs.")

H2("2.1 Words to tokens")
P("A <b>tokenizer</b> cuts text into <b>tokens</b>: whole words, parts of words or punctuation, each with an integer <b>token id</b>. "
  "\"The answer is\" might become three ids. The model never sees letters, only these integers.")

H2("2.2 Tokens to vectors: the embedding")
P("The <b>embedding table</b> is a big matrix with one row per vocabulary entry (128,256 rows) and 4,096 numbers per row. "
  "Looking up a token id gives its row: a <b>vector</b> of 4,096 numbers. From now on the token is that vector, written <b>x</b>.")

H2("2.3 One transformer layer, step by step")
FIG(fig_layer(), "Figure 2. One transformer layer during decode. The red step is the one KVForge compiles.")
B([
    "<b>RMSNorm.</b> Rescale x so its numbers have a standard size. Cheap.",
    "<b>Q, K, V projections.</b> Multiply x by three weight matrices: W<sub>Q</sub> (4,096 x 4,096), W<sub>K</sub> and W<sub>V</sub> (4,096 x 1,024 each). "
    "The results are q (4,096 numbers), k and v (1,024 numbers each). These matrices are the model's learned weights for this layer; they sit in VRAM.",
    "<b>Split into heads.</b> q is cut into 32 pieces of 128 numbers: 32 <b>query heads</b>. k and v are cut into 8 pieces of 128: 8 <b>key/value heads</b>. "
    "Each group of g = 32/8 = 4 query heads shares one K/V head. That sharing is <b>grouped-query attention (GQA)</b>.",
    "<b>RoPE.</b> Rotate pairs of numbers in q and k by an angle that depends on the token's position, so attention knows word order.",
    "<b>Append to the KV cache.</b> The new k and v are stored for the future. The cache now holds this token too.",
    "<b>Attention</b> (per query head): compare q with the key of every earlier token (a dot product, divided by the square root of 128), "
    "turn the scores into weights that sum to one (<b>softmax</b>), and take the weighted sum of the earlier tokens' values. Result: 128 numbers per head.",
    "<b>Output projection.</b> Put the 32 heads' results side by side (4,096 numbers) and multiply by W<sub>O</sub> (4,096 x 4,096). Add the result to x: the <b>residual</b> connection.",
    "<b>Feed-forward network (SwiGLU).</b> Normalise again, multiply by W<sub>gate</sub> and W<sub>up</sub> (4,096 x 14,336 each), combine them, multiply by W<sub>down</sub> (14,336 x 4,096), add to x.",
])
CALLOUT("<b>Do the heads store weights?</b> Not separately. Each layer has its four attention matrices (W<sub>Q</sub>, W<sub>K</sub>, W<sub>V</sub>, W<sub>O</sub>). "
        "A head is simply a <b>slice</b> of 128 columns of those matrices, and a slice of 128 numbers of q, k and v. "
        "What each head <b>accumulates while running</b> is its part of the KV cache: the keys and values of every token so far.")

H2("2.4 From the last layer back to words")
B([
    "After 32 layers, a final RMSNorm, then the <b>LM head</b>: multiply x by a 4,096 x 128,256 matrix to get one score per vocabulary entry, the <b>logits</b>.",
    "<b>Sampling</b> turns logits into probabilities (softmax) and picks a token id, either the most likely or a random draw.",
    "The tokenizer turns the id back into text. That token is appended to the input and the loop runs again.",
])

H2("2.5 Prefill and decode")
P("<b>Prefill</b> processes the whole prompt at once: many tokens, so every weight is reused for many tokens and the GPU is busy doing arithmetic (<b>compute-bound</b>). "
  "<b>Decode</b> generates one token at a time: each weight and each cached key and value is read once and used once (<b>reuse = 1</b>), so the GPU waits for memory (<b>memory-bound</b>). "
  "KVForge targets decode.")

H2("2.6 How big things are")
TABLE([
    ["Item", "Size", "How it is computed"],
    ["Weights in fp16", "about 16 GB", "about 8 billion parameters x 2 bytes. Does not fit in your 8.5 GB of VRAM"],
    ["Weights in 4-bit", "about 4.5 to 5 GB", "how a laptop actually runs this model (for example llama.cpp)"],
    ["KV cache per token, one layer", "4 KiB", "K and V x 8 heads x 128 numbers x 2 bytes"],
    ["KV cache per token, all layers", "128 KiB", "x 32 layers"],
    ["KV cache at 32,768 tokens", "4 GiB", "the size our main example reads every token"],
    ["Reading 5 GB of weights", "about 15 ms", "5 GB / 341 GB/s (measured bandwidth), per token"],
], [52, 32, 90])
P("Because every token must read all of this, <b>bytes moved</b>, not arithmetic, decides how fast the model writes. Attention over the KV cache is the part that grows with context length.")
story.append(PageBreak())

# ---------------- part 3
H1("3. The hardware: your RTX 5060 Laptop GPU")
H2("3.1 From disk to the GPU")
B([
    "<b>SSD (disk).</b> The model file is stored here. It is read once when the program starts. The disk does no arithmetic and is not touched while tokens are generated.",
    "<b>System RAM.</b> The program reads the file into ordinary memory first.",
    "<b>PCIe.</b> The link between the CPU side and the GPU. Weights cross it once, at load time, into VRAM.",
    "<b>VRAM.</b> The GPU's own memory: 8.5 GB of <b>GDDR7</b> on your laptop. Weights and the KV cache live here. Measured sustained read bandwidth: <b>341 GB/s</b>; idle latency for one request: <b>148 ns</b>.",
])
CALLOUT("<b>GDDR vs HBM.</b> Datacenter GPUs (H100, B200) use <b>HBM</b>: memory chips stacked next to the GPU die with a very wide connection, giving several TB/s. "
        "Consumer GPUs like yours use <b>GDDR</b> chips on the board: cheaper, narrower, a few hundred GB/s. The role in this project is identical: it is the big, slow memory "
        "the KV cache streams out of. Your notes said HBM; on your laptop it is GDDR7.")

H2("3.2 Inside the GPU")
TABLE([
    ["Level", "Size on your GPU", "Shared by", "Speed", "Source"],
    ["VRAM (GDDR7)", "8.5 GB", "the whole GPU", "341 GB/s read; 148 ns idle latency", "measured"],
    ["L2 cache", "32 MB", "all 26 SMs", "1,581 GB/s", "measured"],
    ["SMs", "26", "-", "16.0 TFLOP/s FP32 total", "measured"],
    ["L1 data cache + shared memory", "about 128 KB per SM", "one SM", "about 30 cycles", "typical"],
    ["Register file", "65,536 x 32-bit per SM (256 KB)", "split among the SM's threads", "about 1 cycle", "count measured"],
    ["L0 instruction cache", "small, per partition", "one partition", "-", "typical"],
    ["Memory sector", "32 bytes", "-", "smallest unit memory moves", "measured (stride test)"],
], [38, 38, 30, 42, 26])

H2("3.3 One SM, the place where code runs")
FIG(fig_sm(), "Figure 3. Anatomy of one SM. Four partitions, each with its own scheduler, registers and arithmetic units, sharing L1 and shared memory.")
B([
    "<b>Partition (sub-core).</b> Each SM has four. Each picks one ready <b>warp</b> per cycle and issues one instruction for all its 32 threads.",
    "<b>Warp scheduler.</b> Chooses which warp runs next. If a warp is waiting for memory, it simply picks another one. That is <b>latency hiding</b>.",
    "<b>Register file.</b> Every thread's private variables live here. Fastest storage on the chip. Our kernel's numbers live in registers almost the whole time.",
    "<b>CUDA cores (FP32 lanes).</b> Do one multiply-add per lane per cycle. In machine code, <b>FFMA</b> = fused multiply-add: a x b + c in one step.",
    "<b>SFU (special function unit).</b> Computes exp2, reciprocal and similar. Our softmax uses it: <b>MUFU.EX2</b>.",
    "<b>LD/ST unit.</b> Sends loads and stores to memory: <b>LDG</b> loads from global memory (VRAM), <b>STG</b> stores, <b>LDS/STS</b> read and write shared memory.",
    "<b>Tensor core.</b> Multiplies small matrices in one instruction. It shines when many numbers reuse each other (prefill, weight multiplies). "
    "Our decode kernel uses the ordinary FP32 lanes, because each cached number is used only g times.",
    "<b>Limits measured on your GPU:</b> at most 48 warps and 24 blocks resident per SM; 65,536 registers per SM.",
])
story.append(PageBreak())

# ---------------- part 4
H1("4. From code to silicon")
H2("4.1 The software stack")
TABLE([
    ["Layer", "Example", "What it does"],
    ["Application", "a chat program, llama.cpp, vLLM", "decides what to generate; loops over tokens"],
    ["Framework", "PyTorch", "turns model steps into calls to GPU kernels"],
    ["Kernel", "our decode_partial, FlashInfer's decode kernel", "one GPU program for one step, such as attention"],
    ["CUDA runtime and driver", "cudart, the NVIDIA driver (WDDM on Windows)", "loads kernels, copies memory, queues launches"],
    ["GPU", "RTX 5060 Laptop", "executes the machine instructions"],
], [32, 62, 80])

H2("4.2 How our C++ and CUDA become machine instructions")
B([
    "<b>CUDA C++ (.cu files).</b> One file holds both CPU code (host) and GPU code (device, marked <font face='Mono'>__global__</font>).",
    "<b>nvcc</b> splits them. The host part is compiled by Microsoft's <b>cl.exe</b> (that is why we installed the Build Tools). The device part is compiled to <b>PTX</b>, "
    "NVIDIA's virtual instruction set, then by <b>ptxas</b> to <b>SASS</b>, the real machine code of one GPU generation: <b>sm_120</b> for your Blackwell GPU, <b>sm_89</b> for the 4060.",
    "The SASS is packed into a <b>cubin</b>, and cubins for several GPUs into a <b>fatbinary</b> inside the .exe. That is why the 4060 package is a separate sm_89 build.",
    "<b>Templates.</b> Our kernel is a template: format, head size, GQA pack size, unroll, order and paging are compile-time parameters. "
    "KVForge's code generator writes the line that instantiates exactly the variant a plan needs. 288 variants exist.",
])
CODE("""// what kvf writes for the chosen plan (out/llama3/decode_llama3_8b.cu)
#include "kvf_kernels.cuh"
extern "C" cudaError_t kvf_launch_llama3_8b(const kvf::Args *in, cudaStream_t st) {
  kvf::Args a = *in;
  a.splits = 32;
  a.warps = 8;
  a.group_shift = 7;                       // int8 groups of 128
  return kvf::launch<kvf::FMT_INT8, 128, 4, 4, kvf::ORD_HEAD, false>(a, st);
}""")

H2("4.3 Grid, blocks, warps, threads")
B([
    "A <b>kernel launch</b> starts a <b>grid</b> of <b>blocks</b>. Each block is a group of <b>threads</b> (we use 128 or 256) that run on one SM and can share memory.",
    "The GPU's <b>block scheduler</b> places blocks on SMs. An SM can hold several blocks at once, limited by registers, warp slots and block slots: this is <b>occupancy</b>.",
    "Inside a block, threads are grouped by 32 into <b>warps</b>. A warp executes one instruction at a time for all 32 threads (<b>SIMT</b>). Each thread is a <b>lane</b>.",
    "If more blocks are launched than fit, they run in rounds: <b>waves</b>. A half-empty last wave wastes time; our cost model accounts for it.",
])
FIG(fig_grid(), "Figure 4. The launch grid of the example plan and how the block scheduler spreads it over the SMs.")

# ---------------- part 5
H1("5. KVForge end to end: input to silicon and back")
P("This part follows one compile and one run of the example: the Llama-3 shape with 32,768 cached tokens, batch 1, on your GPU.")

H2("5.1 The input: a specification with question marks")
CODE("""target machine = "machines/rtx5060-laptop.gpu"     # measured GPU description
target calib   = "model/constants_rtx5060.cal"     # frozen cost-model constants
target max_rel_err = 0.02                           # accuracy budget: allows int8

decode llama3_8b(H: 32, H_kv: 8, d: 128, n: 32768, batch: 1) {
  Q: query<H, d, f32>
  K: kvcache<n, d, ?, ?, ?>        # format, order, residency: compiler chooses
  V: kvcache<n, d, ?, ?, ?>
  O = decode_attn(Q, K, V, scale = auto, splits = ?, gqa_pack = ?)
}""")
P("Each <font face='Mono'>?</font> is a decision left to the compiler. Writing a value instead pins it.")

H2("5.2 Front end: reading the program")
FIG(fig_pipeline(), "Figure 5. The KVForge pipeline and the source file for each stage.")
B([
    "<b>Lexer</b> (src/lexer.cpp): turns characters into <b>tokens</b> of the language (keywords, names, numbers, symbols). A DFA: it reads one character at a time.",
    "<b>Parser</b> (src/parser.cpp): checks the tokens follow the grammar (docs/dsl.md) and builds an <b>AST</b>, a tree of the program (include/kvf/ast.h). Recursive descent.",
    "<b>Semantic analysis</b> (src/ir.cpp): checks meaning: H is a multiple of H_kv, the group size divides d, K and V agree. Turns each ? into a free dimension of the <b>search space</b>.",
    "<b>IR</b>: an SSA module with one operation, <font face='Mono'>kvf.decode_attn</font>, over two typed values of kind <font face='Mono'>kvcache</font> whose format and layout are still unknown.",
])
CODE("""%K = kvf.kvcache : kvcache<32768x128x?, ?/?>
%O = kvf.decode_attn %Q, %K, %V : tensor<32x128xf32> {scale = 0.0883883}""")

H2("5.3 Middle: choosing the plan")
B([
    "<b>Enumerate</b> (src/plan.cpp): every combination of format (f16, int8:64/128, int4:32/64/128), layout (8 options), splits (1 to 64), GQA packing, warps and unroll. 2,688 plans for this shape.",
    "<b>Cost model</b> (src/cost.cpp, with src/machine.cpp and src/calib.cpp): predicts each plan's time from bytes moved, Little's law, waves, instruction counts and overheads (docs/cost_model.md).",
    "<b>Accuracy gate</b> (src/passes.cpp): drops plans whose format's measured error exceeds the budget. int4 (11 to 14% error) is dropped at 0.02; int8 (0.8%) survives.",
    "<b>Rewrite</b>: the cheapest surviving plan replaces <font face='Mono'>decode_attn</font> by <font face='Mono'>decode_attn_split</font> with every choice attached. "
    "The whole decision, including writing the report files, takes 147 ms (measured).",
])
CODE("""%K = kvf.kvcache : kvcache<32768x128xint8:128, head_major/contiguous>
%O = kvf.decode_attn_split %Q, %K, %V {format = int8:128, layout = head_major/contiguous,
       splits = 32, gqa_pack = true, warps = 8, unroll = 4, blocks = 256, pred_us = ...}""")

H2("5.4 Back end: making GPU code")
B([
    "<b>Code generation</b> (src/codegen.cpp) writes decode_llama3_8b.cu and plan_info.h (section 4.2).",
    "<b>nvcc</b> (tools/nvcc.cmd, tools/build_plan.ps1) compiles it with the kernel templates (runtime/kvf_kernels.cuh) and the driver program (runtime/kvf_driver.cu) into bench.exe.",
    "The driver program creates test data, uploads it to VRAM, launches the kernel, checks the answer and times it.",
])

H2("5.5 On the GPU: the life of one block")
P("Take the lossless (fp16) plan the compiler picks for this shape when no accuracy budget is set: 32 splits, GQA packing, 8 warps, unroll 2. Its launch creates 256 blocks (Figure 4); the int8 plan of section 4.2 has the same grid and adds integer-unpacking instructions. Follow one block: split 5 of KV head 2. It owns tokens 5,120 to 6,143 of KV head 2 and serves query heads 8 to 11. "
  "It has 8 warps. The steps below are what the hardware does, with the actual SASS instructions from our compiled fp16 kernel (cuobjdump of build/cubin/f16_hm_c.cubin).")
FIG(fig_warp(), "Figure 6. How the 32 lanes of a warp split one step's work: two tokens, 16 lanes each, 8 numbers per lane.")
TABLE([
    ["Step", "What happens physically", "SASS instruction"],
    ["1. Load the queries", "Each lane reads its 8 query numbers for each of the 4 query heads from VRAM into registers. Read-only cache path.", "LDG.E.128.CONSTANT (16 bytes per lane)"],
    ["2. Ask for K and V", "Each lane requests 16 bytes of the next tokens' K rows and V rows, before using any of them. "
     "With unroll 2 that is 4 loads in flight per lane. The request travels to L2 and VRAM (Figure 7); "
     "the hint EF means evict first: the data is used once, so it should not push useful data out of the cache.", "LDG.E.EF.128"],
    ["3. Widen fp16 to fp32", "Each 16-bit number is converted to a 32-bit float in a register.", "HADD2.F32"],
    ["4. Dot product", "Each lane multiplies its 8 key numbers by its 8 query numbers and sums them: 8 fused multiply-adds per head.", "FFMA"],
    ["5. Add up the 16 lanes", "Lanes exchange registers directly in 4 butterfly steps (lane i swaps with lane i xor 8, 4, 2, 1), no memory involved.", "SHFL.BFLY + FADD"],
    ["6. Online softmax", "Compare with the running maximum, compute 2^(score - max) on the special function unit, rescale the running sum.", "FMNMX, MUFU.EX2, FMUL, FFMA"],
    ["7. Accumulate V", "Multiply each value number by the softmax weight and add to the running output, held in registers.", "FFMA"],
    ["8. Repeat", "Move to the next tokens of the chunk; loads for the next step are already in flight.", "BRA (branch)"],
    ["9. Combine the warps", "Each lane group writes its partial result to shared memory, the block waits until all have written, then threads read and combine them.", "STS, BAR.SYNC, LDS"],
    ["10. Write the partial", "The block writes its running max, sum and 128-number partial output to VRAM.", "STG"],
    ["11. Merge kernel", "A second, tiny kernel combines the 32 splits' partials for each head (log-sum-exp) and writes the final 128 numbers per head.", "LDG, MUFU.EX2, FFMA, STG"],
], [30, 104, 40])
FIG(fig_load(), "Figure 7. The round trip of one load instruction.")
H3("What the arithmetic units physically do")
P("When the scheduler issues an <b>FFMA</b>, each of the 32 lanes reads three 32-bit registers from the register file, its FP32 unit multiplies two of them and adds the third in one rounding step, "
  "and the result is written back to a register. The 32 lanes do this at the same time. A <b>SHFL</b> moves a register from one lane to another through the SM's data network. "
  "An <b>LDG</b> does not compute anything: it hands an address to the load/store unit and marks the destination register as pending until the data arrives. "
  "None of this touches the disk; the disk is idle the whole time.")
H3("Static instruction counts in this kernel")
TABLE([
    ["Instruction", "Count in the compiled kernel", "Meaning"],
    ["FFMA", "256", "fused multiply-add: dot products and value accumulation"],
    ["FMUL / FADD", "248 / 108", "multiply / add: softmax rescaling, lane reductions"],
    ["FMNMX", "132", "maximum of two floats: the softmax running max"],
    ["MUFU", "78 (76 of them EX2)", "special function unit: exp2 for the softmax, plus 2 reciprocals"],
    ["SHFL", "32", "lane-to-lane register exchange"],
    ["HADD2.F32", "32", "fp16 to fp32 conversion"],
    ["LDG / STG", "12 / 12", "loads: 8 query + 4 K/V (unroll 2 x K and V); stores: the partial results"],
    ["STS / LDS / BAR.SYNC", "16 / 140 / 8", "the block-level merge through shared memory, one barrier pair per head"],
], [32, 42, 100])
P("These are counts in the program text (one kernel variant: fp16, d = 128, GQA pack of 4, unroll 2), not counts per token; loops run the loop body many times.", "small")

H2("5.6 Back to the output")
B([
    "The output is 32 x 128 numbers, one 128-number vector per query head. In a real model they go to the output projection W<sub>O</sub> (Figure 2) and on through the layer.",
    "In our runs, the driver or the sweep copies the output back and compares it with a double-precision reference: <b>verified</b> if the relative error is under 0.002.",
    "Timing uses <b>CUDA events</b> placed before and after the kernel on the GPU's own timeline. The L2 cache is flushed before every repetition so each run reads from VRAM, as a real decode step would.",
])
story.append(PageBreak())

# ---------------- part 6
H1("6. What we measure, with which command")
TABLE([
    ["Command", "What it captures", "Writes", "Code"],
    ["build\\cuda\\bw_probe.exe --out machines\\X.gpu", "Bandwidth (all SMs, one SM, L2), latency, FP32 rate, launch time, sector size (stride test), SM and register counts", "machines/*.gpu", "bench/bw_probe.cu"],
    ["build\\kvf plan spec.kv --out DIR", "The compiler's decision: all candidates ranked, predicted cost, IR before and after", "report.txt, plans.csv, ir.txt, decode_*.cu, plan_info.h", "src/*.cpp"],
    ["tools\\build_plan.ps1 -Dir DIR", "Builds and runs the generated kernel: correctness, time, predicted vs measured", "DIR/bench.exe", "runtime/kvf_driver.cu"],
    ["build\\kvf emit-dispatch; tools\\build_cuda.ps1", "Generates and compiles all 288 kernel variants into the sweep harness", "gen/*.cu, build/cuda/sweep.exe", "src/codegen.cpp"],
    ["build\\cuda\\sweep.exe --plans ... --out X.csv", "Ground truth: every plan verified and timed (median and quartiles of 20 runs)", "results/sweep_*.csv", "bench/sweep.cu"],
    ["python tools\\dump_resources.py exe csv", "Registers each compiled kernel uses (from cuobjdump), for occupancy", "machines/resources_sm*.csv", "tools/dump_resources.py"],
    ["build\\kvf calibrate --sweep ... --out X.cal", "Fits the 10 model constants on fit shapes; scores fit and held-out shapes", "model/constants_rtx5060.cal", "src/fit.cpp"],
    ["build\\kvf predict ...", "Predicted next to measured for every plan", "results/predicted_*.csv", "src/main.cpp"],
    ["build\\kvf evaluate ...", "MAPE, rank correlation, regret, with frozen constants: the transfer test", "console report", "src/fit.cpp"],
    ["python tools\\analyze.py; tools\\speedup.py", "Figures (H1 spread, axis effects, predicted vs measured), speedups vs baseline", "results/figs/*", "tools/*.py"],
    ["powershell tests\\smoke.ps1", "19 compiler tests: examples plan, bad programs rejected", "console", "tests/smoke.ps1"],
    ["cuobjdump -sass file.cubin", "The machine instructions of a kernel (used in section 5.5)", "build/sass_*.txt", "CUDA toolkit"],
    ["bench/wsl/compare.py (in WSL)", "FlashInfer and PyTorch SDPA against our kernels, same process and timer", "results/compare_*.csv", "bench/wsl/compare.py"],
], [48, 58, 38, 30])
CALLOUT("<b>The data flow of the evaluation:</b> bw_probe describes the GPU; kvf plan lists the candidates; sweep.exe times them all; "
        "kvf calibrate fits the model on 7 shapes; kvf evaluate scores it on the 3 held-out shapes, and on the 4060 for the transfer test.")
story.append(PageBreak())

# ---------------- part 7
H1("7. Code map: which file controls which layer")
TABLE([
    ["File", "Layer it controls", "What it does"],
    ["examples/*.kv, shapes/*.kv", "Input", "Specifications: shape and the choices left open"],
    ["src/lexer.cpp, include/kvf/lexer.h", "Compiler front end", "Characters to tokens"],
    ["src/parser.cpp, include/kvf/ast.h", "Compiler front end", "Tokens to a syntax tree; grammar in docs/dsl.md"],
    ["src/ir.cpp, include/kvf/ir.h", "Compiler front end", "Semantic checks, search space, SSA IR, printing"],
    ["src/format.cpp, src/layout.cpp", "Middle (vocabulary)", "Storage formats (effective bits) and memory layouts"],
    ["src/plan.cpp", "Middle", "Enumerates every plan"],
    ["src/machine.cpp, machines/*.gpu", "Model of the hardware", "Measured GPU description and register tables"],
    ["src/calib.cpp, model/*.cal", "Model of the hardware", "The 10 frozen constants and measured format errors"],
    ["src/cost.cpp", "Middle (the core idea)", "Predicts time: bytes, Little's law, waves, issue time, overheads"],
    ["src/passes.cpp", "Middle", "Accuracy gate, plan choice, IR rewrite"],
    ["src/codegen.cpp", "Back end", "Writes CUDA that instantiates the chosen kernel; dispatch tables"],
    ["src/emit.cpp", "Back end", "Report, CSV, roofline table"],
    ["src/fit.cpp", "Evaluation", "Reads sweeps, fits constants, computes MAPE, rank correlation, regret"],
    ["src/main.cpp", "Command line", "plan, roofline, machine, emit-dispatch, calibrate, predict, evaluate"],
    ["runtime/kvf_kernels.cuh", "GPU (the silicon)", "The kernel templates: loads, dot products, shuffles, online softmax, merge"],
    ["runtime/kvf_host.h", "CPU side of a run", "Test data, quantisation, layout placement, reference, timing"],
    ["runtime/kvf_registry.h, runtime/kvf_driver.cu", "CPU side of a run", "Variant lookup; driver for one generated kernel"],
    ["bench/bw_probe.cu", "Measurement", "Measures the machine file"],
    ["bench/sweep.cu", "Measurement", "Times every plan; ground truth"],
    ["bench/wsl/*.py, *.sh", "Measurement", "Library comparison in Linux (WSL2)"],
    ["tools/*.ps1, tools/nvcc.cmd", "Build", "Compiler wrapper, CUDA build, plan build, 4060 package"],
    ["tools/*.py", "Analysis", "Figures, speedups, resource tables, evaluation summaries"],
    ["tests/smoke.ps1, tests/edge/*.kv", "Tests", "Compiler tests; awkward shapes for kernel correctness"],
    ["docs/*.md", "Documentation", "Language, cost model, results"],
], [52, 34, 88])
story.append(PageBreak())

# ---------------- part 8 glossary
H1("8. Glossary")
G = [
    ("Accuracy gate", "Rejects a plan whose format's measured relative error exceeds the budget max_rel_err."),
    ("Activation", "A number computed while running the model (as opposed to a stored weight)."),
    ("AST", "Abstract syntax tree: the parser's tree form of the program."),
    ("Attention", "Each query compares itself with every cached key, turns the scores into weights (softmax) and takes the weighted sum of the values."),
    ("Bandwidth", "Bytes per second a memory can deliver. VRAM: 341 GB/s measured."),
    ("Baseline", "The plain plan we compare against: fp16, token-major, contiguous, no splitting, no packing, 4 warps, unroll 2. Not a tuned library."),
    ("Batch", "Several sequences decoded together."),
    ("b_eff", "Effective bits per stored number including the scale and zero point: bits + 32/G."),
    ("BAR.SYNC", "Machine instruction: every thread of the block waits here until all arrive."),
    ("Block", "A group of threads (128 or 256 here) that runs on one SM and shares its shared memory."),
    ("Block table", "In a paged layout, the list telling where each page of the cache is."),
    ("bw_probe", "Our program that measures the GPU's machine parameters."),
    ("Bytes in flight", "Data requested but not yet arrived. More in flight gives more bandwidth, up to the limit (Little's law)."),
    ("Cache line, sector", "Memory moves in 32-byte sectors (measured), grouped in 128-byte lines."),
    ("Calibration", "Fitting the 10 model constants to measured times, once, on one GPU."),
    ("Codegen", "Code generation: writing the CUDA source for the chosen plan."),
    ("Coalescing", "Neighbouring lanes reading neighbouring addresses, so each sector fetched is fully used."),
    ("Compute-bound", "Limited by arithmetic speed. Prefill is; decode is not."),
    ("Compute capability", "The GPU generation number: 12.0 (sm_120) for yours, 8.9 (sm_89) for the 4060."),
    ("Cost model", "Formulas that predict a plan's run time without running it."),
    ("cubin, fatbinary", "Compiled GPU machine code for one GPU type; several cubins bundled together."),
    ("CUDA", "NVIDIA's platform and C++ dialect for GPU programs."),
    ("CUDA core", "One FP32 arithmetic lane of an SM."),
    ("CUDA event", "A timestamp recorded on the GPU's timeline; we time kernels between two events."),
    ("d (head dimension)", "Numbers per head per token: 128 (or 64)."),
    ("Decode", "Generating one token at a time. Memory-bound; reuse = 1."),
    ("Dequantise", "Turn a stored integer back into a real number: raw x scale + zero."),
    ("DRAM, VRAM", "The GPU's main memory: GDDR7 on your laptop, HBM on datacenter GPUs."),
    ("Embedding", "The table turning a token id into a vector of 4,096 numbers."),
    ("Enumerate", "List every candidate plan."),
    ("eta (η)", "Layout efficiency: fraction of fetched bytes actually used."),
    ("FFMA", "Fused multiply-add instruction: a x b + c."),
    ("FlashInfer", "A library of expert-tuned attention kernels (Linux), our comparison target."),
    ("fp16, int8, int4", "Storage formats: 16-bit floats (lossless here), 8-bit and 4-bit integers with group scales (lossy)."),
    ("g (GQA group)", "Query heads per key/value head: 32/8 = 4 in the example."),
    ("Geometric mean", "The right average for ratios: the n-th root of their product."),
    ("GQA", "Grouped-query attention: several query heads share one K/V head."),
    ("GQA packing", "One block serves all g query heads of a group, so the K/V head is read once."),
    ("Grid", "All blocks of one kernel launch."),
    ("Group (quantisation)", "G numbers sharing one scale and zero point (32, 64 or 128)."),
    ("H, H_kv", "Number of query heads (32) and key/value heads (8)."),
    ("H1", "Our hypothesis: plans moving the same bytes run at very different speeds. Held: 1.8x to 6.4x."),
    ("HBM", "High Bandwidth Memory: stacked DRAM on datacenter GPUs."),
    ("Head", "One independent attention computation over a 128-number slice."),
    ("Head-major, token-major", "Memory orders: all tokens of one head together, or all heads of one token together."),
    ("Held-out shape", "A shape not used to fit the constants; the honest test."),
    ("Imbalance, waves", "Blocks run in rounds; a nearly empty last round wastes time."),
    ("Intensity (arithmetic)", "FLOPs per byte moved. Decode: 2g/b_eff, about 4 for fp16 with g = 4."),
    ("IR", "Intermediate representation: the compiler's internal program form."),
    ("Kendall tau (τ)", "Fraction of plan pairs the model orders correctly, minus the fraction it orders wrongly."),
    ("Kernel", "One GPU program, launched as a grid of blocks."),
    ("KV cache", "Stored keys and values of every earlier token, per layer and head."),
    ("L0, L1, L2", "Caches: L0 instruction cache per partition, L1/shared per SM, L2 (32 MB) shared by all SMs."),
    ("Lane", "One thread within a warp."),
    ("Latency", "Time for one request to come back. 148 ns idle (measured); about 8x longer under load (fitted)."),
    ("Launch overhead", "Time to start a kernel: 20.8 microseconds measured on Windows."),
    ("Layout", "How the cache is arranged in memory: order and residency."),
    ("LDG, STG, LDS, STS", "Load/store global memory (VRAM) and shared memory instructions."),
    ("Lexer, parser", "Front-end stages: characters to tokens, tokens to tree."),
    ("Little's law", "Bandwidth = bytes in flight / latency."),
    ("Logits", "One score per vocabulary entry at the end of the model."),
    ("Lossless, lossy", "Stores numbers exactly (fp16) or rounded (int8, int4)."),
    ("MAPE", "Mean absolute percentage error of predicted vs measured time."),
    ("Memory-bound", "Limited by how fast memory delivers bytes. Decode is."),
    ("Merge (log-sum-exp)", "Combining split partial results correctly using their running maxima."),
    ("MUFU.EX2", "Instruction computing 2^x on the special function unit."),
    ("n", "Context length: tokens in the cache."),
    ("nvcc, PTX, SASS", "CUDA compiler; virtual instruction set; real machine code."),
    ("Occupancy", "How many warps an SM holds at once, limited by registers and slots."),
    ("Online softmax", "Softmax computed in one pass with a running maximum and sum."),
    ("Oracle", "The best plan found by timing everything."),
    ("Paged layout", "The cache split into fixed-size pages reached through a block table (as in vLLM)."),
    ("Partition (of the work)", "How work is cut into blocks: splits, packing, warps, unroll."),
    ("Partition (of an SM)", "One of four sub-cores, each with a scheduler, registers and lanes."),
    ("Plan", "One full choice of format, layout and partition."),
    ("Prefill", "Processing the whole prompt at once. Compute-bound."),
    ("Regret", "How much slower the compiler's pick is than the oracle: T(pick)/T(best) - 1."),
    ("Registers", "Fastest per-thread storage; 65,536 per SM (measured)."),
    ("Relative error (L2)", "Size of the difference divided by the size of the correct answer."),
    ("Residual", "Adding a layer's input to its output."),
    ("Reuse", "How many times each loaded number is used. Decode: 1."),
    ("Ridge point", "The intensity where a GPU switches from memory- to compute-bound: 47 FLOP/byte here."),
    ("RMSNorm, RoPE", "Vector normalisation; position-dependent rotation of q and k."),
    ("Roofline", "Performance <= min(peak compute, bandwidth x intensity)."),
    ("SFU", "Special function unit: exp2, reciprocal and similar."),
    ("SHFL.BFLY", "Butterfly shuffle: lanes exchange registers directly."),
    ("SIMT", "Single instruction, multiple threads: a warp runs one instruction for 32 lanes."),
    ("SM", "Streaming multiprocessor: the GPU's processing unit. Yours has 26."),
    ("Smart App Control", "A Windows security feature that blocked one large unsigned program; we did not change it."),
    ("Softmax", "Turns scores into positive weights that sum to one."),
    ("Spearman rho (ρ)", "Correlation of the predicted and measured rankings."),
    ("Speedup", "Baseline time / chosen time."),
    ("Split-KV (splits)", "Cutting a head's tokens into chunks processed by separate blocks, then merging."),
    ("Sweep", "Timing every plan on the real GPU: ground truth."),
    ("Tensor core", "Unit that multiplies small matrices in one instruction; useful when numbers are reused."),
    ("Token", "A piece of text with an integer id."),
    ("Transfer test", "Using constants fitted on one GPU to predict on another, with no refit."),
    ("Unroll", "How many tokens' loads a lane keeps in flight per step."),
    ("Warp", "32 threads executing together."),
    ("Weights", "The model's learned numbers, stored in VRAM."),
    ("WSL2", "Linux running inside Windows; used for FlashInfer, which needs Linux."),
]
TABLE([["Term", "Meaning"]] + [[a, b] for a, b in G], [40, 134])
story.append(PageBreak())

# ---------------- part 9
H1("9. Honest limits")
B([
    "<b>One step, not a whole model.</b> KVForge compiles attention over the KV cache for one layer. It does not run tokenisation, weights, the feed-forward network or sampling.",
    "<b>Measured on one GPU so far.</b> Every result is from the RTX 5060 Laptop. The transfer test needs the RTX 4060 run.",
    "<b>The baseline is naive.</b> The 1.9x to 3.6x speedups are over a plain kernel in our own family. The FlashInfer and PyTorch comparison is in progress.",
    "<b>Typical figures.</b> SM partition layout, L1 size, tensor-core details and cycle counts in Part 3 are from vendor documentation for this GPU family, not measured here.",
    "<b>Accuracy figures use random data.</b> Real KV caches have outliers; int8 and int4 errors would need re-measuring on real model activations.",
    "<b>Known model gap.</b> Some split counts run slower than both smaller and larger ones; the model does not capture it (suspected memory-channel conflicts).",
])


# ------------------------------------------------------------------ page decoration
def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Body", 7.5)
    canvas.setFillColor(SLATE)
    if doc.page > 1:
        canvas.drawString(18 * mm, 10 * mm, "KVForge | From words to silicon | Compiler Design")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, str(doc.page))
    canvas.restoreState()


doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
                        title="From words to silicon: KVForge deep-dive guide", author="Aahav Yadav, Akshat Kapur, Rishab Jajodia")
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print("wrote", OUT)
