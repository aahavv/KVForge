const pptxgen = require("pptxgenjs");
const SKILL = "C:/Users/aahav/.claude/skills/synced/b4521919-1949-4b13-b972-ca514308941f_c939ef9e-118f-4a13-8daf-3273f8d454f0/pptx";
const { applyTheme } = require(SKILL + "/scripts/apply_theme.js");

const OUT = "C:/Users/aahav/Downloads/KVForge_Compiler_Design_Progress_Review_v3.pptx";
const FIGS = "C:/Users/aahav/KVForge/results/figs/";

// ---------------------------------------------------------------- theme
const THEME = {
  name: "KVForge",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "0B1220", lt1: "FFFFFF", dk2: "1F2A44", lt2: "EEF2F7",
    accent1: "0F766E", // teal  - data / bytes
    accent2: "F59E0B", // amber - the bottleneck
    accent3: "4F46E5", // indigo
    accent4: "BE123C", // rose
    accent5: "15803D", // green
    accent6: "475569", // slate
    hlink: "0F766E", folHlink: "475569",
  },
};
const HEX = { teal: "0F766E", tealL: "5EEAD4", amber: "F59E0B", ink: "0B1220", slate: "475569", grid: "E2E8F0", pale: "EEF2F7" };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "KVForge - Compiler Design Project Proposal";
pres.author = "Aahav Yadav, Akshat Kapur, Rishab Jajodia";
const C = pres.SchemeColor;

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: "FFFFFF" },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.3, w: 12.13, h: 0.9, fontSize: 30, bold: true, color: C.text1, align: "left", valign: "middle", margin: 0 }, text: "" } },
    { text: { text: "KVForge  |  Compiler Design", options: { x: 0.6, y: 7.08, w: 6, h: 0.3, fontSize: 10, color: C.accent6, margin: 0 } } },
  ],
  slideNumber: { x: 12.13, y: 7.08, w: 0.6, h: 0.3, fontSize: 10, color: C.accent6, align: "right" },
});
pres.defineSlideMaster({ title: "DARK", background: { color: "0B1220" }, objects: [] });

// ---------------------------------------------------------------- references (30)
const REFS = [
  // A. compilers, scheduling languages, cost models
  ["tvm", "TVM: An Automated End-to-End Optimizing Compiler for Deep Learning", "1802.04799", 2018],
  ["autotvm", "Learning to Optimize Tensor Programs (AutoTVM)", "1805.08166", 2018],
  ["ansor", "Ansor: Generating High-Performance Tensor Programs for Deep Learning", "2006.06762", 2020],
  ["mlir", "MLIR: A Compiler Infrastructure for the End of Moore's Law", "2002.11054", 2020],
  ["taco", "Format Abstraction for Sparse Tensor Algebra Compilers", "1804.10112", 2018],
  ["tilelang", "TileLang: A Composable Tiled Programming Model for AI Systems", "2504.17577", 2025],
  ["loom", "Schedules Are Solvable Symbols: Tuning-Free Compilation of Tile Programs on Dataflow Architectures (Loom)", "2609.29219", 2026],
  ["tpu", "A Learned Performance Model for Tensor Processing Units", "2008.01040", 2020],
  // B. attention kernels
  ["osm", "Online normalizer calculation for softmax", "1805.02867", 2018],
  ["fa1", "FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness", "2205.14135", 2022],
  ["fa2", "FlashAttention-2: Faster Attention with Better Parallelism and Work Partitioning", "2307.08691", 2023],
  ["fa3", "FlashAttention-3: Fast and Accurate Attention with Asynchrony and Low-precision", "2407.08608", 2024],
  ["fdpp", "FlashDecoding++: Faster Large Language Model Inference on GPUs", "2311.01282", 2023],
  ["lean", "Lean Attention: Hardware-Aware Scalable Attention Mechanism for the Decode-Phase of Transformers", "2405.10480", 2024],
  ["flashinfer", "FlashInfer: Efficient and Customizable Attention Engine for LLM Inference Serving", "2501.01005", 2025],
  ["flex", "Flex Attention: A Programming Model for Generating Optimized Attention Kernels", "2412.05496", 2024],
  ["pkv", "PersistentKV: Page-Aware Decode Scheduling for Long-Context LLM Serving on Commodity GPUs", "2606.26666", 2026],
  ["fold", "FoldAttention: Declared-Reference Softmax for Fast Decode and Deterministic Backward", "2609.33410", 2026],
  // C. KV representation and layout
  ["paged", "Efficient Memory Management for LLM Serving with PagedAttention (vLLM)", "2309.06180", 2023],
  ["gqa", "GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints", "2305.13245", 2023],
  ["mla", "DeepSeek-V2 (introduces Multi-head Latent Attention)", "2405.04434", 2024],
  ["kivi", "KIVI: A Tuning-Free Asymmetric 2bit Quantization for KV Cache", "2402.02750", 2024],
  ["kvquant", "KVQuant: Towards 10 Million Context Length LLM Inference with KV Cache Quantization", "2401.18079", 2024],
  ["qserve", "QServe: W4A8KV4 Quantization and System Co-design for Efficient LLM Serving", "2405.04532", 2024],
  ["bitdec", "BitDecoding: Unlocking Tensor Cores for Long-Context LLMs with Low-Bit KV Cache", "2503.18773", 2025],
  ["minima", "Minima-KV: Retention-Preserving KV Cache Compression with Mixed-Format Paged Attention", "2608.23834", 2026],
  // D. bandwidth analysis
  ["memwall", "AI and Memory Wall", "2403.14123", 2024],
  ["unveil", "LLM Inference Unveiled: Survey and Roofline Model Insights", "2402.16363", 2024],
  ["gap", "Mind the Memory Gap: Unveiling GPU Bottlenecks in Large-Batch LLM Inference", "2503.08311", 2025],
  ["budget", "Budgeting Bytes: A Windowed Storage Roofline for Storage-Bound LLM Decoding", "2609.04238", 2026],
];
const R = (k) => { const i = REFS.findIndex((r) => r[0] === k); if (i < 0) throw new Error("ref " + k); return i + 1; };
const cite = (...ks) => "[" + ks.map(R).join(", ") + "]";

// ---------------------------------------------------------------- helpers
const T = (s, text, o = {}) => s.addText(text, Object.assign({ isTextBox: true, margin: 0, fontSize: 14, color: C.text1, valign: "top" }, o));
const rect = (s, x, y, w, h, fill, o = {}) => s.addShape(pres.ShapeType.rect, Object.assign({ x, y, w, h, fill: { color: fill }, line: { type: "none" } }, o));
const rrect = (s, x, y, w, h, fill, o = {}) => s.addShape(pres.ShapeType.roundRect, Object.assign({ x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { type: "none" } }, o));
const box = (s, x, y, w, h, fill, text, o = {}) =>
  s.addText(text, Object.assign({ shape: pres.ShapeType.roundRect, rectRadius: 0.08, x, y, w, h, fill: { color: fill }, line: { type: "none" }, align: "center", valign: "middle", fontSize: 13, color: C.background1, margin: 4 }, o));
const arrowR = (s, x, y, w, h, fill) => s.addShape(pres.ShapeType.rightArrow, { x, y, w, h, fill: { color: fill }, line: { type: "none" } });
const line = (s, x1, y1, x2, y2, color, width = 1.5, extra = {}) =>
  s.addShape(pres.ShapeType.line, Object.assign({ x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1), flipH: x2 < x1, flipV: y2 < y1, line: Object.assign({ color, width }, extra.line || {}) }, {}));
const badge = (s, x, y, n, fill = C.accent1) =>
  s.addText(String(n), { shape: pres.ShapeType.ellipse, x, y, w: 0.44, h: 0.44, fill: { color: fill }, line: { type: "none" }, align: "center", valign: "middle", fontSize: 14, bold: true, color: C.background1, margin: 0 });

const declared = new Set();
function slide(title, section, notes) {
  if (section && !declared.has(section)) { pres.addSection({ title: section }); declared.add(section); }
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  if (notes) s.addNotes(notes);
  return s;
}
const PAL = { teal: C.accent1, amber: C.accent2, indigo: C.accent3, rose: C.accent4, green: C.accent5, slate: C.accent6 };

// =================================================================== 1. title
{
  pres.addSection({ title: "Opening" }); declared.add("Opening");
  const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Opening" });
  T(s, "COMPILER DESIGN  |  PROPOSAL AND PROGRESS REVIEW",{ x: 0.8, y: 0.8, w: 8, h: 0.4, fontSize: 14, bold: true, color: C.accent2, charSpacing: 3 });
  T(s, "KVForge", { x: 0.8, y: 1.5, w: 8, h: 1.1, fontSize: 60, bold: true, color: C.background1, fontFace: "Cambria" });
  T(s, "A bandwidth-model-driven compiler for GPU decode-phase attention", { x: 0.8, y: 2.7, w: 7.4, h: 1.2, fontSize: 24, color: C.background2 });
  T(s, [
    { text: "Aahav Yadav  -  24BKT0138", options: { breakLine: true } },
    { text: "Akshat Kapur  -  24BDS0318", options: { breakLine: true } },
    { text: "Rishab Jajodia  -  24BDS0268" },
  ], { x: 0.8, y: 4.6, w: 7, h: 1.1, fontSize: 18, color: C.background1, paraSpaceAfter: 6 });
  T(s, "Course: Compiler Design  |  VIT Vellore", { x: 0.8, y: 6.3, w: 7, h: 0.4, fontSize: 14, color: C.background2 });
  // motif: KV cache blocks streaming into a compute unit
  for (let r = 0; r < 6; r++) for (let c = 0; c < 4; c++) {
    const shade = (r + c) % 2 ? "0F766E" : "14B8A6";
    rect(s, 9.0 + c * 0.42, 1.6 + r * 0.42, 0.36, 0.36, shade);
  }
  rect(s, 9.0 + 3 * 0.42, 1.6 + 5 * 0.42, 0.36, 0.36, "F59E0B");
  arrowR(s, 10.85, 2.55, 0.9, 0.5, "F59E0B");
  box(s, 11.85, 2.0, 1.1, 1.6, "4F46E5", "SMs", { fontSize: 18, bold: true });
  T(s, "KV cache (memory)", { x: 9.0, y: 4.25, w: 1.9, h: 0.3, fontSize: 12, color: C.background2 });
  T(s, "every byte read once per token", { x: 9.0, y: 4.6, w: 3.9, h: 0.3, fontSize: 12, color: C.accent2 });
  s.addNotes("Title. KVForge is our working name. One-line pitch: decode attention is limited by how many bytes move and how well they move; we build a compiler that chooses the storage format, memory layout and work partitioning with an analytic bandwidth model.");
}

// =================================================================== 2. summary
{
  const s = slide("The idea in one slide", "Problem",
    "Pyramid summary. Problem, insight, approach, then the evidence standard we hold ourselves to.");
  const cards = [
    ["1", "Problem", "Decode reads the entire KV cache for every generated token and uses each byte once. The GPU waits on memory; compute sits idle.", PAL.rose],
    ["2", "Insight", "With data reuse fixed at 1, tiling cannot rank schedules. What still matters: bytes per element, memory layout, and how work is split across SMs.", PAL.amber],
    ["3", "Approach", "KVForge enumerates format x layout x partition, scores each with an analytic bandwidth model, and emits a CUDA kernel for the predicted best.", PAL.teal],
  ];
  cards.forEach((c, i) => {
    const x = 0.6 + i * 4.1;
    rrect(s, x, 1.5, 3.93, 3.7, C.background2);
    badge(s, x + 0.3, 1.8, c[0], c[3]);
    T(s, c[1], { x: x + 0.9, y: 1.8, w: 2.8, h: 0.44, fontSize: 22, bold: true, valign: "middle" });
    T(s, c[2], { x: x + 0.3, y: 2.55, w: 3.35, h: 2.5, fontSize: 18 });
  });
  rrect(s, 0.6, 5.5, 12.13, 1.3, THEME.colors.dk1);
  T(s, "Evidence standard", { x: 0.9, y: 5.65, w: 3, h: 0.35, fontSize: 14, bold: true, color: C.accent2 });
  T(s, "Calibrate the model on one GPU (RTX 5060 Laptop, Blackwell), then check that it still picks good configurations on a different one (RTX 4060, Ada) without re-tuning. Result: on the RTX 4060 with no refit, rank correlation 0.886 and regret 6.6% (fp16) to 16.1% (all formats); 1.9× to 3.6× over a naive baseline and within 6% of FlashInfer on the 5060.",
    { x: 0.9, y: 6.0, w: 11.5, h: 0.7, fontSize: 15, color: C.background1 });
}

// =================================================================== P. total progress
{
  const s = slide("Total progress against the plan", "Problem",
    "Status of the whole project against the plan agreed for the first 70 percent. The 70 percent scope was eight items; all eight are done. Three of the four items originally deferred to the last 30 percent are also done: the transfer test on the second GPU, the baseline and library comparison, and the lossy formats behind an accuracy gate. What remains is the written final report and the known gaps listed at the bottom. Numbers: 44,224 plan runs were verified against a double-precision reference with none failing: 20,928 plus 2,368 on the RTX 5060 and 20,928 on the RTX 4060. fp8 was not built. The library comparison is fp16 only.");
  const stats = [["8 of 8", "items in the 70% scope are done"], ["3 of 4", "items deferred to the last 30% are done"], ["44,224", "plan runs verified on two GPUs, none failed"]];
  stats.forEach((st, i) => {
    const x = 0.6 + i * 4.1;
    rrect(s, x, 1.35, 3.93, 1.35, C.background2);
    T(s, st[0], { x: x + 0.25, y: 1.4, w: 3.45, h: 0.75, fontSize: 38, bold: true, color: C.accent1, fontFace: "Cambria" });
    T(s, st[1], { x: x + 0.25, y: 2.15, w: 3.45, h: 0.5, fontSize: 13, color: C.accent6 });
  });
  // progress bar: 70% scope (done) + deferred 30% (3 of 4 done)
  const bx = 0.6, bw = 12.13, by = 2.95;
  T(s, "The plan, as a bar: first 70% (all done) and the remaining 30% (3 of 4 items done)", { x: bx, y: by - 0.02, w: bw, h: 0.3, fontSize: 12, bold: true });
  const w70 = bw * 0.7, w30 = bw * 0.3;
  rect(s, bx, by + 0.32, w70, 0.34, "15803D");
  T(s, "70% scope: 8 of 8 done", { x: bx + 0.15, y: by + 0.33, w: w70 - 0.3, h: 0.32, fontSize: 12, bold: true, color: C.background1, valign: "middle" });
  const seg = w30 / 4;
  [["transfer", "15803D", "FFFFFF"], ["baselines", "15803D", "FFFFFF"], ["lossy fmts", "15803D", "FFFFFF"], ["final report", "CBD5E1", "0B1220"]].forEach((sg, i) => {
    rect(s, bx + w70 + i * seg, by + 0.32, seg - 0.03, 0.34, sg[1]);
    T(s, sg[0], { x: bx + w70 + i * seg, y: by + 0.33, w: seg - 0.03, h: 0.32, fontSize: 10.5, bold: true, color: sg[2], align: "center", valign: "middle" });
  });
  // checklists
  const done = [
    ["Toolchain on a Blackwell GPU", "CUDA 13.4, MSVC build tools"],
    ["bw_probe: the machine, measured", "341 GB/s, 148 ns, 32 B sector"],
    ["Kernels: fp16, int8, int4", "288 variants, all verified"],
    ["Sweep harness and sweeps", "20,928 plans per GPU, 10 shapes"],
    ["Cost model, fitted and held out", "ρ 0.88, regret 1.9% to 15%"],
    ["Compiler: spec to verified CUDA", "19 of 19 tests pass"],
    ["Package for the second GPU", "ran on the RTX 4060"],
    ["Deck with real numbers", "33 slides, docs/results.md"],
  ];
  T(s, "In the 70% scope", { x: 0.6, y: 4.0, w: 6, h: 0.3, fontSize: 13, bold: true, color: C.accent5 });
  done.forEach((d, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.6 + col * 3.75, y = 4.35 + row * 0.5;
    s.addText("✓", { shape: pres.ShapeType.ellipse, x, y: y + 0.03, w: 0.3, h: 0.3, fill: { color: "15803D" }, line: { type: "none" }, align: "center", valign: "middle", fontSize: 11, bold: true, color: C.background1, margin: 0 });
    T(s, d[0], { x: x + 0.4, y, w: 3.25, h: 0.25, fontSize: 11, bold: true });
    T(s, d[1], { x: x + 0.4, y: y + 0.22, w: 3.25, h: 0.25, fontSize: 10, color: C.accent6 });
  });
  const deferred = [
    ["Transfer test on a second GPU", "RTX 4060: ρ 0.886, no refit", true],
    ["Baselines and libraries (fp16)", "within 6% of FlashInfer", true],
    ["Lossy formats behind a gate", "int8 0.8%, int4 11 to 14% error", true],
    ["Final written report", "deck and docs exist; report text to do", false],
  ];
  T(s, "Deferred to the last 30%", { x: 8.3, y: 4.0, w: 4.4, h: 0.3, fontSize: 13, bold: true, color: C.accent1 });
  deferred.forEach((d, i) => {
    const y = 4.35 + i * 0.5;
    s.addText(d[2] ? "✓" : "–", { shape: pres.ShapeType.ellipse, x: 8.3, y: y + 0.03, w: 0.3, h: 0.3, fill: { color: d[2] ? "15803D" : "94A3B8" }, line: { type: "none" }, align: "center", valign: "middle", fontSize: 11, bold: true, color: C.background1, margin: 0 });
    T(s, d[0], { x: 8.7, y, w: 4.0, h: 0.25, fontSize: 11, bold: true });
    T(s, d[1], { x: 8.7, y: y + 0.22, w: 4.0, h: 0.25, fontSize: 10, color: C.accent6 });
  });
  rrect(s, 0.6, 6.4, 12.13, 0.6, "FDE68A");
  T(s, "Open: split counts that run slower than their neighbours (not modelled); the 8-head-pack kernel (trails FlashInfer, fails one 4060 shape); lossy accuracy on real model data; a GPU unlike the two consumer cards. fp8 not built.", { x: 0.8, y: 6.42, w: 11.75, h: 0.56, fontSize: 11, valign: "middle" });
}

// =================================================================== 3. prefill vs decode
{
  const s = slide("Attention in one screen: prefill vs decode", "Problem",
    "Attention(Q,K,V) = softmax(QK^T/sqrt(d)) V. In prefill there are N queries, so every K row is used N times: there is reuse to exploit by tiling. In decode there is one new query, so each cached K and V row is used once and discarded.");
  T(s, "Attention(Q, K, V) = softmax( Q Kᵀ / sqrt(d) ) V", { x: 0.6, y: 1.3, w: 12.1, h: 0.4, fontSize: 18, fontFace: "Courier New", color: C.accent6 });
  // panels
  rrect(s, 0.6, 1.9, 5.95, 3.4, C.background2);
  rrect(s, 6.78, 1.9, 5.95, 3.4, C.background2);
  T(s, "PREFILL  -  N prompt tokens at once", { x: 0.85, y: 2.0, w: 5.4, h: 0.35, fontSize: 15, bold: true, color: C.accent3 });
  T(s, "DECODE  -  one new token per step", { x: 7.03, y: 2.0, w: 5.4, h: 0.35, fontSize: 15, bold: true, color: C.accent4 });
  const cy = 3.4;
  // prefill: Q (N x d) x K^T (d x N) = N x N
  box(s, 0.85, cy - 0.8, 0.9, 1.6, PAL.indigo, "Q\nN × d", { fontSize: 12 });
  T(s, "×", { x: 1.8, y: cy - 0.2, w: 0.3, h: 0.4, fontSize: 20, align: "center", valign: "middle" });
  box(s, 2.15, cy - 0.45, 1.6, 0.9, PAL.teal, "Kᵀ  (d × N)", { fontSize: 12 });
  T(s, "=", { x: 3.8, y: cy - 0.2, w: 0.3, h: 0.4, fontSize: 20, align: "center", valign: "middle" });
  for (let r = 0; r < 5; r++) for (let c = 0; c < 5; c++) rect(s, 4.25 + c * 0.32, cy - 0.8 + r * 0.32, 0.29, 0.29, "F59E0B");
  T(s, "N × N scores", { x: 4.1, y: cy + 0.92, w: 1.9, h: 0.3, fontSize: 12, align: "center" });
  T(s, "Each K row is used by all N queries. Reuse is high, so tile for it. Compute-bound.", { x: 0.85, y: 4.7, w: 5.45, h: 0.55, fontSize: 14 });
  // decode: q (1 x d) x K^T (d x n) = 1 x n
  box(s, 7.03, cy - 0.15, 0.9, 0.3, PAL.rose, "q  1 × d", { fontSize: 11 });
  T(s, "×", { x: 7.98, y: cy - 0.2, w: 0.3, h: 0.4, fontSize: 20, align: "center", valign: "middle" });
  box(s, 8.33, cy - 0.45, 1.6, 0.9, PAL.teal, "Kᵀ  (d × n)", { fontSize: 12 });
  T(s, "=", { x: 9.98, y: cy - 0.2, w: 0.3, h: 0.4, fontSize: 20, align: "center", valign: "middle" });
  box(s, 10.43, cy - 0.15, 1.6, 0.3, PAL.amber, "n scores", { fontSize: 11, color: C.text1 });
  T(s, "A matrix-vector product, not matrix-matrix.", { x: 7.03, y: cy + 0.92, w: 5.4, h: 0.3, fontSize: 12, align: "center" });
  T(s, "Each cached K and V row is read once, used once, discarded. Reuse = 1. Memory-bound.", { x: 7.03, y: 4.7, w: 5.45, h: 0.55, fontSize: 14 });
  // bottom takeaway
  box(s, 0.6, 5.65, 12.13, 1.0, THEME.colors.dk1, "", {});
  T(s, "Why this matters for a compiler: classical schedulers score a schedule by how much reuse it captures in fast memory. For decode that number is 1 for every schedule.",
    { x: 0.9, y: 5.75, w: 11.5, h: 0.8, fontSize: 16, color: C.background1, valign: "middle" });
}

// =================================================================== 4. one decode step
{
  const s = slide("One decode step, end to end", "Problem",
    "Walk through generating one token. Only the newest token is embedded and projected. Everything older lives in the KV cache and must be read in full. Numbers: Llama-3-8B shape, H_kv=8, d=128, n=32768, fp16: 2*n*d*H_kv*2 bytes = 128 MiB per layer, times 32 layers = 4 GiB per token. At an assumed 300 GB/s that is about 14 ms just to read the cache.");
  const steps = ["Embed the last token", "Compute its q, k, v (fresh, cheap)", "Append k, v to the cache", "Read the whole cache, attend, emit the next token"];
  steps.forEach((t, i) => {
    const x = 0.6 + i * 3.08;
    badge(s, x, 1.45, i + 1, i === 3 ? PAL.amber : PAL.teal);
    T(s, t, { x: x + 0.55, y: 1.4, w: 2.4, h: 0.6, fontSize: 14, valign: "middle" });
  });
  // memory card
  rrect(s, 0.6, 2.35, 4.6, 2.5, C.background2);
  T(s, "GPU memory", { x: 0.85, y: 2.45, w: 3, h: 0.3, fontSize: 14, bold: true });
  for (let i = 0; i < 13; i++) rect(s, 0.85 + i * 0.3, 2.95, 0.26, 0.5, i === 12 ? "F59E0B" : "0F766E");
  T(s, "n cached tokens", { x: 0.85, y: 3.5, w: 2.2, h: 0.28, fontSize: 12, color: C.accent6 });
  T(s, "+1 per step", { x: 3.4, y: 3.5, w: 1.6, h: 0.28, fontSize: 12, color: C.accent2, bold: true, align: "right" });
  T(s, "bytes = 2 · n · d · H_kv · b", { x: 0.85, y: 4.0, w: 4.1, h: 0.35, fontSize: 14, fontFace: "Courier New" });
  T(s, "K and V, b bytes per element", { x: 0.85, y: 4.38, w: 4.1, h: 0.3, fontSize: 12, color: C.accent6 });
  // arrow
  arrowR(s, 5.35, 3.1, 2.2, 0.7, "F59E0B");
  T(s, "ALL n entries,\nevery step", { x: 5.35, y: 3.85, w: 2.2, h: 0.6, fontSize: 13, bold: true, align: "center", color: C.accent4 });
  // compute card
  rrect(s, 7.7, 2.35, 5.03, 2.5, C.background2);
  T(s, "Compute units (SMs)", { x: 7.95, y: 2.45, w: 4, h: 0.3, fontSize: 14, bold: true });
  box(s, 7.95, 3.0, 1.4, 0.7, PAL.indigo, "q · Kᵀ", { fontSize: 13 });
  box(s, 9.5, 3.0, 1.4, 0.7, PAL.indigo, "softmax", { fontSize: 13 });
  box(s, 11.05, 3.0, 1.4, 0.7, PAL.indigo, "weights · V", { fontSize: 13 });
  T(s, "about 4 · n · d FLOPs per head: tiny next to the bytes", { x: 7.95, y: 3.95, w: 4.6, h: 0.6, fontSize: 13, color: C.accent6 });
  // stats
  const stats = [["4 GiB", "read per generated token\n(Llama-3-8B shape, 32k context,\nfp16, 32 layers)"], ["1 FLOP/byte", "arithmetic intensity of\nmulti-head attention in fp16"], ["~14 ms", "per token just to read the cache,\nassuming 300 GB/s (illustrative)"]];
  stats.forEach((st, i) => {
    const x = 0.6 + i * 4.1;
    T(s, st[0], { x, y: 5.1, w: 3.9, h: 0.75, fontSize: 38, bold: true, color: C.accent1, fontFace: "Cambria" });
    T(s, st[1], { x, y: 5.85, w: 3.9, h: 0.95, fontSize: 13, color: C.accent6 });
  });
}

// =================================================================== 5. roofline
{
  const s = slide("Why decode is memory-bound: the roofline", "Problem",
    "Roofline: performance <= min(peak compute, bandwidth x arithmetic intensity). The chart uses the numbers bw_probe measured on the RTX 5060 Laptop (341 GB/s, 16.0 TFLOP/s). Derivation of intensity: per KV head we move 2*n*d*b bytes (K and V); per query head we do 4*n*d FLOPs; with g query heads per KV head that is 4*n*d*g / (2*n*d*b) = 2g/b FLOP per byte. n and d cancel, so context length cannot fix it.");
  const AI = [0.5, 1, 2, 4, 8, 16, 32, 64, 128];
  s.addChart(pres.charts.LINE, [{ name: "Attainable GFLOP/s", labels: AI.map(String), values: AI.map((a) => Math.min(16026, 341.3 * a)) }], {
    x: 0.6, y: 1.45, w: 7.2, h: 4.5, chartColors: [HEX.teal], lineSize: 3, lineDataSymbolSize: 8,
    showTitle: true, title: "Attainable GFLOP/s vs intensity (RTX 5060 Laptop, measured)", titleFontSize: 14, titleColor: HEX.ink, titleFontFace: "+mn-lt",
    showCatAxisTitle: true, catAxisTitle: "Arithmetic intensity (FLOP/byte)", catAxisTitleFontSize: 12, catAxisTitleColor: HEX.slate, catAxisTitleFontFace: "+mn-lt",
    showValAxisTitle: true, valAxisTitle: "GFLOP/s", valAxisTitleFontSize: 12, valAxisTitleColor: HEX.slate, valAxisTitleFontFace: "+mn-lt",
    catAxisLabelColor: HEX.slate, valAxisLabelColor: HEX.slate, catAxisLabelFontSize: 12, valAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
    valGridLine: { color: HEX.grid, size: 0.75 }, catGridLine: { style: "none" }, showLegend: false,
  });
  T(s, "Measured by bw_probe on the RTX 5060 Laptop: 341 GB/s sustained DRAM read, 16.0 TFLOP/s FP32, ridge at 47 FLOP/byte.", { x: 0.6, y: 6.05, w: 7.2, h: 0.5, fontSize: 11, color: C.accent6 });
  T(s, "Decode intensity  I = 2g / b_eff", { x: 8.1, y: 1.45, w: 4.6, h: 0.4, fontSize: 15, bold: true, fontFace: "Courier New" });
  T(s, "FLOP/byte; g = query heads per KV head, b_eff = bytes per element", { x: 8.1, y: 1.9, w: 4.6, h: 0.5, fontSize: 12, color: C.accent6 });
  const hd = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.ink }, align: "center", fontSize: 12 } });
  const cell = (t, hl) => ({ text: t, options: { align: "center", fontSize: 13, fill: { color: hl ? "FDE68A" : "FFFFFF" } } });
  s.addTable([
    [hd("format"), hd("bits"), hd("g=1"), hd("g=4"), hd("g=8")],
    [cell("fp16"), cell("16"), cell("1.00", 1), cell("4.00"), cell("8.00")],
    [cell("int8:128"), cell("8.25"), cell("1.94"), cell("7.76"), cell("15.5")],
    [cell("int4:128"), cell("4.25"), cell("3.76"), cell("15.1"), cell("30.1")],
    [cell("int4:32"), cell("5.00"), cell("3.20"), cell("12.8"), cell("25.6")],
  ], { x: 8.1, y: 2.5, w: 4.63, colW: [1.2, 0.8, 0.88, 0.88, 0.87], rowH: 0.42, border: { type: "solid", pt: 0.75, color: HEX.grid }, fontFace: "Calibri", color: HEX.ink });
  rrect(s, 8.1, 4.8, 4.63, 1.75, C.background2);
  T(s, "Every entry is far below the ridge. Bytes, not FLOPs, set the speed. n and d cancel, so a longer context does not help.", { x: 8.3, y: 4.9, w: 4.25, h: 1.55, fontSize: 14, valign: "middle" });
}

// =================================================================== 6. existing problem
{
  const s = slide("The existing problem: three approaches, three limits", "Problem",
    "Honest framing: reuse-based analytic cost models go flat for decode, but measured autotuners (AutoTVM, Ansor) do not, because they time candidates on real hardware. Their limit is cost and machine-specificity, not blindness. Hand-written kernels are fast but cover a fixed menu. The gap is a model that explains and predicts without trials.");
  const cols = [
    ["Reuse-based cost models", `Halide, TVM tiling, TileLang ${cite("tvm", "tilelang")}`, "Score a schedule by the data it reuses in fast memory. For decode, reuse is 1 for every schedule, so every tiling scores the same.", "Blind for this operator", PAL.rose],
    ["Measured autotuning", `AutoTVM, Ansor ${cite("autotvm", "ansor")}`, "Time many candidates on the real GPU and keep the best. It works, but it costs trials on every machine and does not explain why a choice wins.", "Slow, per-machine", PAL.amber],
    ["Hand-written kernels", `FlashDecoding++, LeanAttention, FlashInfer ${cite("fdpp", "lean", "flashinfer")}`, "Expert-tuned for known shapes and hardware. Fast, but a fixed menu of formats and layouts; new hardware means new tuning.", "Fast, not general", PAL.slate],
  ];
  cols.forEach((c, i) => {
    const x = 0.6 + i * 4.1;
    rrect(s, x, 1.5, 3.93, 3.55, C.background2);
    T(s, c[0], { x: x + 0.25, y: 1.65, w: 3.45, h: 0.4, fontSize: 18, bold: true });
    T(s, c[1], { x: x + 0.25, y: 2.1, w: 3.45, h: 0.6, fontSize: 12, color: C.accent6 });
    T(s, c[2], { x: x + 0.25, y: 2.75, w: 3.45, h: 1.5, fontSize: 14 });
    box(s, x + 0.25, 4.4, 3.45, 0.45, c[4], c[3], { fontSize: 13, bold: true });
  });
  rrect(s, 0.6, 5.3, 12.13, 1.5, THEME.colors.dk1);
  T(s, "Open question", { x: 0.9, y: 5.4, w: 3, h: 0.3, fontSize: 13, bold: true, color: C.accent2 });
  T(s, "Can an analytic model of bandwidth, not reuse, choose the storage format, layout and partitioning without trials, and keep choosing well on a different GPU?", { x: 0.9, y: 5.72, w: 11.5, h: 0.55, fontSize: 16, color: C.background1 });
  T(s, "Hypothesis H1 (we will measure it first): configurations that move the same bytes can differ by 2x or more in runtime through layout and partition alone.", { x: 0.9, y: 6.28, w: 11.5, h: 0.45, fontSize: 13, color: C.background2 });
}

// =================================================================== 7. three axes overview + representation
{
  const s = slide("Axis 1 - Representation: fewer bytes per element", "Idea",
    "Three axes carry the signal once reuse is gone: representation (what is stored), placement (where it sits), partition (who reads which part). Representation changes bytes per element. Quantized formats pay for metadata: one fp16 scale and one fp16 zero point per group, so int4 with group 128 costs 4 + 32/128 = 4.25 bits, not 4. Because quantization is lossy, the compiler needs an accuracy gate.");
  s.addChart(pres.charts.BAR, [{ name: "Effective bits per element", labels: ["fp16", "fp8", "int8:128", "int4:128"], values: [16, 8, 8.25, 4.25] }], {
    x: 0.6, y: 1.45, w: 6.2, h: 4.3, barDir: "col", chartColors: [HEX.teal], barGapWidthPct: 60,
    showTitle: true, title: "Effective bits per cached element", titleFontSize: 14, titleColor: HEX.ink, titleFontFace: "+mn-lt",
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00", dataLabelColor: HEX.ink, dataLabelFontSize: 12, dataLabelFontFace: "+mn-lt",
    catAxisLabelColor: HEX.slate, valAxisLabelColor: HEX.slate, catAxisLabelFontSize: 12, valAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
    valGridLine: { color: HEX.grid, size: 0.75 }, catGridLine: { style: "none" }, showLegend: false, valAxisMaxVal: 18,
  });
  T(s, "Quantization group, int4 with group size 128", { x: 7.1, y: 1.45, w: 5.6, h: 0.35, fontSize: 15, bold: true });
  for (let i = 0; i < 16; i++) rect(s, 7.1 + i * 0.27, 1.95, 0.24, 0.5, "0F766E");
  T(s, "128 elements × 4 bits = 512 bits", { x: 7.1, y: 2.5, w: 4.4, h: 0.3, fontSize: 12, color: C.accent6 });
  box(s, 7.1, 2.95, 1.3, 0.5, PAL.indigo, "scale 16b", { fontSize: 12 });
  box(s, 8.55, 2.95, 1.5, 0.5, PAL.indigo, "zero point 16b", { fontSize: 12 });
  T(s, "metadata = 32 bits per group", { x: 10.2, y: 2.95, w: 2.5, h: 0.5, fontSize: 12, color: C.accent6, valign: "middle" });
  T(s, "b_eff = bits + 32/G = 4 + 32/128 = 4.25", { x: 7.1, y: 3.7, w: 5.6, h: 0.4, fontSize: 14, fontFace: "Courier New", bold: true });
  T(s, `Group-wise scale and zero point is the scheme in KIVI, KVQuant and QServe ${cite("kivi", "kvquant", "qserve")}.`, { x: 7.1, y: 4.15, w: 5.6, h: 0.6, fontSize: 13, color: C.accent6 });
  rrect(s, 7.1, 4.95, 5.63, 1.85, "FDE68A");
  T(s, "Not semantics-preserving", { x: 7.3, y: 5.05, w: 5.2, h: 0.3, fontSize: 14, bold: true });
  T(s, "Quantizing changes the numbers. KVForge adds an accuracy gate: a plan is rejected if its error against an fp16 reference exceeds a user-set limit.", { x: 7.3, y: 5.4, w: 5.25, h: 1.3, fontSize: 14 });
  T(s, "Lossy formats are opt-in; the default search is lossless (fp16/bf16 plus placement and partition).", { x: 0.6, y: 5.9, w: 6.2, h: 0.7, fontSize: 13, color: C.accent6 });
}

// =================================================================== 8. placement: layouts
{
  const s = slide("Axis 2 - Placement: how the cache is laid out in memory", "Idea",
    "Placement decides which bytes sit next to each other. Token-major keeps one token's d channels contiguous: a long sequential run per KV head. Paged layouts (vLLM-style) split the cache into fixed-size blocks reached through a block table: one extra pointer load per block, and run length equals block size. Channel-major keeps one channel across tokens contiguous, which per-channel key quantization (KIVI) wants, but a warp then has to follow many separate streams.");
  const panelW = 3.93;
  const xs = [0.6, 4.7, 8.8];
  xs.forEach((x) => rrect(s, x, 1.45, panelW, 3.6, C.background2));
  // A token-major
  T(s, "Token-major, contiguous", { x: 0.8, y: 1.55, w: 3.6, h: 0.3, fontSize: 14, bold: true });
  for (let r = 0; r < 4; r++) {
    T(s, "t" + r, { x: 0.8, y: 2.05 + r * 0.42, w: 0.3, h: 0.38, fontSize: 11, color: C.accent6, valign: "middle" });
    for (let c = 0; c < 8; c++) rect(s, 1.15 + c * 0.4, 2.05 + r * 0.42, 0.37, 0.38, r % 2 ? "14B8A6" : "0F766E");
  }
  T(s, "address order  →  (row by row)", { x: 1.15, y: 3.8, w: 3.2, h: 0.28, fontSize: 12, color: C.accent2, bold: true });
  T(s, "K[token][channel]", { x: 0.8, y: 4.2, w: 3.6, h: 0.3, fontSize: 13, fontFace: "Courier New" });
  T(s, "one token = d channels in a row", { x: 0.8, y: 4.55, w: 3.6, h: 0.3, fontSize: 12, color: C.accent6 });
  // B paged
  T(s, "Paged, block table", { x: 4.9, y: 1.55, w: 3.6, h: 0.3, fontSize: 14, bold: true });
  const px = [4.9, 6.15, 7.4];
  const perm = [2, 0, 1];
  ["table[0]", "table[1]", "table[2]"].forEach((t, i) => box(s, px[i], 2.05, 1.1, 0.4, PAL.indigo, t, { fontSize: 11 }));
  const pcol = ["14B8A6", "0F766E", "5EEAD4"];
  for (let p = 0; p < 3; p++) box(s, px[p], 3.2, 1.1, 0.8, pcol[p], "physical " + p + "\nB tokens × d", { fontSize: 11, color: C.text1 });
  for (let i = 0; i < 3; i++) line(s, px[i] + 0.55, 2.45, px[perm[i]] + 0.55, 3.2, "475569", 1.5, { line: { endArrowType: "triangle" } });
  T(s, "table entry to physical block", { x: 4.9, y: 4.2, w: 3.6, h: 0.3, fontSize: 13, fontFace: "Courier New" });
  T(s, "run = block × d × b bytes; +1 pointer load per page", { x: 4.9, y: 4.55, w: 3.65, h: 0.45, fontSize: 12, color: C.accent6 });
  // C channel-major
  T(s, "Channel-major", { x: 9.0, y: 1.55, w: 3.6, h: 0.3, fontSize: 14, bold: true });
  for (let c = 0; c < 8; c++) {
    for (let r = 0; r < 4; r++) rect(s, 9.0 + c * 0.4, 2.05 + r * 0.42, 0.37, 0.38, c % 2 ? "14B8A6" : "0F766E");
  }
  T(s, "address order  ↓  (column by column)", { x: 9.0, y: 3.8, w: 3.6, h: 0.28, fontSize: 12, color: C.accent2, bold: true });
  T(s, "K[channel][token]", { x: 9.0, y: 4.2, w: 3.6, h: 0.3, fontSize: 13, fontFace: "Courier New" });
  T(s, "one channel = n tokens in a row", { x: 9.0, y: 4.55, w: 3.6, h: 0.3, fontSize: 12, color: C.accent6 });
  // takeaways
  const tk = [
    ["Fast path", "Long sequential runs per KV head. One stream, ideal for coalesced loads."],
    ["Cost of paging", `Capacity win ${cite("paged")}; pays a pointer chase per block and shorter runs.`],
    ["Cost of channel-major", `Wanted by per-channel key quantization ${cite("kivi")}; a warp follows many streams.`],
  ];
  tk.forEach((t, i) => {
    const x = xs[i];
    T(s, t[0], { x: x + 0.1, y: 5.3, w: panelW - 0.2, h: 0.35, fontSize: 15, bold: true, color: C.accent1 });
    T(s, t[1], { x: x + 0.1, y: 5.7, w: panelW - 0.2, h: 1.2, fontSize: 14 });
  });
}

// =================================================================== 9. coalescing
{
  const s = slide("Placement matters because memory moves in sectors", "Idea",
    "On NVIDIA GPUs global memory is served in 32-byte sectors (CUDA programming guide). If a warp's 32 threads read 16 contiguous bytes each, 512 bytes are fully used. If each thread reads 16 bytes but from a different place, each touch still fetches a whole 32-byte sector, so half the fetched bytes are wasted; with 4-byte strided reads only one eighth is useful. The 32-byte sector was confirmed on the RTX 5060 with bw_probe: time per 4-byte read grows with stride until 32 B, then stays flat.");
  const bars = [
    ["Coalesced: 32 threads × 16 B, contiguous", 1.0, "η = 1.00"],
    ["Scattered: 16 B per thread, one sector each", 0.5, "η = 0.50"],
    ["Strided 4 B reads, one sector each", 0.125, "η = 0.125"],
  ];
  T(s, "A warp's reads against 16 sectors of 32 B (512 B)", { x: 0.6, y: 1.4, w: 7.6, h: 0.35, fontSize: 15, bold: true });
  bars.forEach((b, i) => {
    const y = 2.0 + i * 1.35;
    T(s, b[0], { x: 0.6, y, w: 7.6, h: 0.3, fontSize: 13 });
    for (let k = 0; k < 16; k++) {
      const x = 0.6 + k * 0.42;
      rect(s, x, y + 0.4, 0.39, 0.5, "E2E8F0");
      rect(s, x, y + 0.4, 0.39 * b[1], 0.5, "0F766E");
    }
    T(s, b[2], { x: 7.45, y: y + 0.4, w: 1.2, h: 0.5, fontSize: 15, bold: true, fontFace: "Courier New", valign: "middle", color: b[1] < 1 ? C.accent4 : C.accent1 });
  });
  T(s, "teal = bytes the kernel uses     grey = bytes fetched and wasted", { x: 0.6, y: 6.1, w: 8, h: 0.3, fontSize: 12, color: C.accent6 });
  rrect(s, 8.95, 1.4, 3.78, 5.4, C.background2);
  s.addChart(pres.charts.BAR, [{ name: "ns per 4-byte read", labels: ["4", "8", "16", "32", "64", "128"], values: [0.017, 0.025, 0.047, 0.091, 0.091, 0.092] }], {
    x: 9.0, y: 1.5, w: 3.68, h: 2.9, barDir: "col", chartColors: [HEX.teal], barGapWidthPct: 40,
    showTitle: true, title: "Measured: time per 4 B read vs stride", titleFontSize: 12, titleColor: HEX.ink, titleFontFace: "+mn-lt",
    showCatAxisTitle: true, catAxisTitle: "stride (bytes)", catAxisTitleFontSize: 11, catAxisTitleColor: HEX.slate, catAxisTitleFontFace: "+mn-lt",
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.000", dataLabelColor: HEX.ink, dataLabelFontSize: 10, dataLabelFontFace: "+mn-lt",
    catAxisLabelColor: HEX.slate, valAxisLabelColor: HEX.slate, catAxisLabelFontSize: 11, valAxisLabelFontSize: 10, catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
    valGridLine: { color: HEX.grid, size: 0.75 }, catGridLine: { style: "none" }, showLegend: false, valAxisMaxVal: 0.11, valAxisMinVal: 0,
  });
  T(s, "Time stops growing at a 32-byte stride: that is the memory sector, confirmed on the RTX 5060 by bw_probe.", { x: 9.15, y: 4.45, w: 3.45, h: 0.85, fontSize: 13 });
  T(s, "η = useful bytes / (32 B × sectors touched)", { x: 9.15, y: 5.35, w: 3.45, h: 0.55, fontSize: 12, fontFace: "Courier New", bold: true });
  T(s, "On this GPU a fp16 row is 256 B, a whole number of sectors, so layout changes cost little (next results slides).", { x: 9.15, y: 5.95, w: 3.45, h: 0.8, fontSize: 12, color: C.accent6 });
}

// =================================================================== 10. partition
{
  const s = slide("Axis 3 - Partition: keeping every SM busy", "Idea",
    "At batch 1 with H_kv = 8 there are only 8 independent work items, far fewer than the SMs on a GPU. Split-KV cuts each head's sequence into chunks processed in parallel, then merges the partial softmaxes with a log-sum-exp rescale (online softmax, Milakov and Gimelshein). Splitting costs partial-result traffic and a merge, so there is an optimum. GQA packing lets the g query heads that share a K/V head read it once instead of g times.");
  rrect(s, 0.6, 1.4, 7.55, 3.55, C.background2);
  rrect(s, 8.35, 1.4, 4.38, 3.55, C.background2);
  T(s, `Split-KV across SMs ${cite("fa2", "lean")}`, { x: 0.8, y: 1.5, w: 7, h: 0.35, fontSize: 15, bold: true });
  const chunkC = ["0F766E", "14B8A6", "0F766E", "14B8A6"];
  T(s, "one head's KV sequence (n tokens)", { x: 0.8, y: 1.9, w: 4, h: 0.28, fontSize: 12, color: C.accent6 });
  for (let i = 0; i < 4; i++) box(s, 0.8 + i * 1.7, 2.25, 1.65, 0.5, chunkC[i], "chunk " + (i + 1), { fontSize: 12, color: i % 2 ? C.text1 : C.background1 });
  for (let i = 0; i < 4; i++) {
    line(s, 0.8 + i * 1.7 + 0.82, 2.75, 0.8 + i * 1.7 + 0.82, 3.1, "475569", 1.5, { line: { endArrowType: "triangle" } });
    box(s, 0.8 + i * 1.7, 3.1, 1.65, 0.55, PAL.indigo, "SM " + i, { fontSize: 12 });
    line(s, 0.8 + i * 1.7 + 0.82, 3.65, 0.8 + i * 1.7 + 0.82, 3.95, "475569", 1.5, { line: { endArrowType: "triangle" } });
  }
  T(s, "each SM emits a partial (m, l, o)", { x: 0.8, y: 3.97, w: 3.5, h: 0.28, fontSize: 12, color: C.accent6 });
  box(s, 0.8, 4.3, 6.75, 0.5, PAL.amber, "merge: rescale by e^(m_i − m) and sum  →  one output", { fontSize: 13, color: C.text1 });
  T(s, `GQA packing ${cite("gqa")}`, { x: 8.55, y: 1.5, w: 4, h: 0.35, fontSize: 15, bold: true });
  ["q1", "q2", "q3", "q4"].forEach((q, i) => {
    box(s, 8.55 + i * 0.95, 2.0, 0.85, 0.42, PAL.rose, q, { fontSize: 12 });
    line(s, 8.55 + i * 0.95 + 0.42, 2.42, 10.35, 3.0, "475569", 1.5);
  });
  box(s, 9.45, 3.0, 1.8, 0.55, PAL.teal, "one K/V head", { fontSize: 13 });
  T(s, "load once, use g times: KV bytes ÷ g", { x: 8.55, y: 3.7, w: 4.0, h: 0.3, fontSize: 13, bold: true, color: C.accent1 });
  T(s, "without packing the same bytes cross the bus g times", { x: 8.55, y: 4.1, w: 4.0, h: 0.6, fontSize: 12, color: C.accent6 });
  const eq = [
    ["work units", "u = H_load · splits · batch"],
    ["load imbalance (S = SM count)", "imb = ceil(u / S) · S / u      "],
    ["merge cost", "T_merge = B_partial / BW_L2 + c_sync"],
  ];
  eq.forEach((e, i) => {
    const x = 0.6 + i * 4.1;
    T(s, e[0], { x, y: 5.2, w: 3.9, h: 0.3, fontSize: 13, bold: true, color: C.accent1 });
    T(s, e[1], { x, y: 5.55, w: 3.95, h: 0.9, fontSize: 12, fontFace: "Courier New" });
  });
  T(s, "More splits fill the SMs but add partial-result traffic and a merge. That trade-off is what the cost model prices.", { x: 0.6, y: 6.35, w: 12.1, h: 0.5, fontSize: 14, color: C.accent6 });
}

// =================================================================== 11. techniques
{
  const s = slide("The techniques we will use, and what each changes", "Approach",
    "This table connects the standard memory-bandwidth techniques (fusion, overlap, coalescing, tiling for access, split-KV) to the three axes and to the exact term in the cost model that each one changes. Note on fusion: round-tripping fp32 scores costs 8n bytes per query head. Against KV bytes of 512n per KV head (fp16, d=128) that is g/64: 1.6 percent at g=1, 6 percent at g=4. At int4 the KV bytes shrink to about 136n, so the same traffic is about 24 percent at g=4. Fusion matters more as the cache gets smaller.");
  const h = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.ink }, fontSize: 13 } });
  const c = (t, o = {}) => ({ text: t, options: Object.assign({ fontSize: 12, valign: "middle" }, o) });
  const rows = [
    [h("Technique"), h("Axis"), h("What it changes in the model"), h("Basis")],
    [c("Fused QK → softmax → PV in one kernel", { bold: true }), c("baseline"), c("Removes the score round-trip. Worth g/64 of KV bytes in fp16 but ~24% at int4, g=4"), c(cite("fa1", "osm"))],
    [c("Online softmax (single pass)", { bold: true }), c("partition"), c("Enables fusion and the split-KV merge; adds the (m, l) partials"), c(cite("osm"))],
    [c("Vectorized, coalesced loads", { bold: true }), c("placement"), c("Drives layout efficiency η toward 1"), c("CUDA rule; measured")],
    [c("Async copy and double buffering", { bold: true }), c("partition"), c("Keeps bytes in flight so one SM sustains more bandwidth (BW per SM = bytes in flight / latency)"), c(cite("fa3") + " + Little's law")],
    [c("Split-KV and GQA packing", { bold: true }), c("partition"), c("Fills SMs (imbalance) and divides KV bytes by g; costs merge traffic"), c(cite("fa2", "lean", "gqa"))],
    [c("Paged blocks", { bold: true }), c("placement"), c("Run length = block size; +1 pointer load per page"), c(cite("paged"))],
    [c("Group-wise low-bit KV", { bold: true }), c("representation"), c("Bytes per element b_eff; adds dequantization FLOPs and an accuracy gate"), c(cite("kivi", "kvquant", "bitdec"))],
  ];
  s.addTable(rows, { x: 0.6, y: 1.4, w: 12.13, colW: [3.3, 1.45, 5.58, 1.8], rowH: [0.4, 0.62, 0.55, 0.5, 0.7, 0.62, 0.5, 0.62], border: { type: "solid", pt: 0.75, color: HEX.grid }, fontFace: "Calibri", color: HEX.ink });
  T(s, "Tiling for reuse is deliberately absent: with reuse = 1 it cannot change the byte count. Tiling for access pattern is covered by placement.", { x: 0.6, y: 6.2, w: 12.13, h: 0.6, fontSize: 14, color: C.accent6 });
}

// =================================================================== 12. architecture
{
  const s = slide("Compiler architecture: from spec to CUDA kernel", "Approach",
    "Pipeline: a small DSL where a question mark marks a choice the compiler may make; a front end and semantic analysis; an IR with a typed KV-cache value that carries format and layout; a plan enumerator over format x layout x partition; the analytic cost model driven by a machine description; a selector with an accuracy gate; CUDA code generation via templated kernels compiled by nvcc; and validation plus measurement. A bandwidth probe measures the machine description on each GPU.");
  const row1 = [["1  Spec (.kv)", "decode attention with ? holes", PAL.slate], ["2  Frontend", "lexer, parser, semantic checks", PAL.slate], ["3  IR", "decode_attn over a typed kvcache", PAL.indigo], ["4  Plan space", "format × layout × partition", PAL.indigo]];
  const row2 = [["5  Cost model", "predicts bytes, BW_eff, time", PAL.teal], ["6  Selector", "cheapest plan that passes the accuracy gate", PAL.teal], ["7  CUDA codegen", "templated kernels, nvcc", PAL.amber], ["8  Validate + measure", "vs reference, timing, regret", PAL.rose]];
  row1.forEach((b, i) => { const x = 0.6 + i * 3.18; box(s, x, 1.4, 2.65, 1.05, b[2], [{ text: b[0], options: { bold: true, fontSize: 14, breakLine: true } }, { text: b[1], options: { fontSize: 12 } }], b[2] === PAL.amber ? { color: C.text1 } : {}); if (i < 3) arrowR(s, x + 2.68, 1.78, 0.42, 0.3, "475569"); });
  line(s, 0.6 + 3 * 3.18 + 1.32, 2.45, 0.6 + 3 * 3.18 + 1.32, 2.8, "475569", 1.5);
  line(s, 0.6 + 3 * 3.18 + 1.32, 2.8, 0.6 + 1.32, 2.8, "475569", 1.5);
  line(s, 0.6 + 1.32, 2.8, 0.6 + 1.32, 3.1, "475569", 1.5, { line: { endArrowType: "triangle" } });
  row2.forEach((b, i) => { const x = 0.6 + i * 3.18; box(s, x, 3.1, 2.65, 1.05, b[2], [{ text: b[0], options: { bold: true, fontSize: 14, breakLine: true } }, { text: b[1], options: { fontSize: 12 } }], b[2] === PAL.amber ? { color: C.text1 } : {}); if (i < 3) arrowR(s, x + 2.68, 3.48, 0.42, 0.3, "475569"); });
  // IR panel
  rrect(s, 0.6, 4.45, 7.4, 2.4, HEX.ink);
  T(s, "IR before and after planning", { x: 0.85, y: 4.52, w: 5, h: 0.3, fontSize: 12, bold: true, color: C.accent2 });
  T(s, [
    { text: "%K = kvc.kvcache<n, d, ?, ?/?>", options: { breakLine: true } },
    { text: "%O = kvc.decode_attn %Q, %K, %V", options: { breakLine: true } },
    { text: "        ↓  plan (cheapest predicted)", options: { breakLine: true, color: C.accent2 } },
    { text: "%K = kvc.kvcache<n, d, fp16, token_major/contig>", options: { breakLine: true } },
    { text: "%O = kvc.decode_attn_split %Q, %K, %V", options: { breakLine: true } },
    { text: "        {splits = 8, gqa_pack, pred_us = ...}" },
  ], { x: 0.85, y: 4.85, w: 7.0, h: 1.9, fontSize: 12, fontFace: "Courier New", color: C.background1 });
  rrect(s, 8.2, 4.45, 4.53, 2.4, C.background2);
  T(s, "bw_probe: one machine description per GPU", { x: 8.4, y: 4.55, w: 4.15, h: 0.3, fontSize: 14, bold: true, color: C.accent1 });
  T(s, "Measures the constants the model needs, instead of assuming them: peak bandwidth, bytes in flight per SM, memory latency, sector efficiency, kernel launch cost, L2 bandwidth.", { x: 8.4, y: 4.95, w: 4.15, h: 1.8, fontSize: 13 });
}

// =================================================================== 13. related work map
{
  const s = slide("Related work: 30 papers in four groups", "Evidence",
    "Thirty papers selected after keyword sweeps of arXiv (titles and abstracts) through October 2026. Group A is how compilers schedule and cost-model tensor programs; B is attention kernels, including decode-specific ones; C is how the KV cache is represented and laid out; D is bandwidth analysis. The two papers that matter most for novelty are PersistentKV and Loom.");
  const groups = [
    ["A. Compilers and cost models", PAL.indigo, ["tvm", "autotvm", "ansor", "mlir", "taco", "tilelang", "loom", "tpu"], ["TVM", "AutoTVM", "Ansor", "MLIR", "TACO formats", "TileLang", "Loom (tuning-free)", "TPU learned model"]],
    ["B. Attention kernels", PAL.teal, ["osm", "fa1", "fa2", "fa3", "fdpp", "lean", "flashinfer", "flex", "pkv", "fold"], ["Online softmax", "FlashAttention", "FlashAttention-2", "FlashAttention-3", "FlashDecoding++", "LeanAttention", "FlashInfer", "FlexAttention", "PersistentKV", "FoldAttention"]],
    ["C. KV representation and layout", PAL.amber, ["paged", "gqa", "mla", "kivi", "kvquant", "qserve", "bitdec", "minima"], ["PagedAttention", "GQA", "DeepSeek-V2 / MLA", "KIVI", "KVQuant", "QServe", "BitDecoding", "Minima-KV"]],
    ["D. Bandwidth analysis", PAL.rose, ["memwall", "unveil", "gap", "budget"], ["AI and Memory Wall", "LLM Inference Unveiled", "Mind the Memory Gap", "Budgeting Bytes"]],
  ];
  const widths = [2.95, 3.1, 3.1, 2.62];
  let x = 0.6;
  groups.forEach((g, gi) => {
    const w = widths[gi];
    rrect(s, x, 1.4, w - 0.12, 5.4, C.background2);
    box(s, x + 0.12, 1.52, w - 0.36, 0.55, g[1], g[0], { fontSize: 13, bold: true, color: g[1] === PAL.amber ? C.text1 : C.background1 });
    const runs = g[2].map((k, i) => ({ text: `[${R(k)}] ${g[3][i]}`, options: { breakLine: i < g[2].length - 1 } }));
    T(s, runs, { x: x + 0.2, y: 2.3, w: w - 0.5, h: 4.4, fontSize: 15, paraSpaceAfter: 10 });
    x += w;
  });
}

// =================================================================== 14. prior-art matrix
{
  const s = slide("Closest prior art and what is left for us", "Evidence",
    "Read from abstracts and our knowledge of each paper; verify against full texts before the final submission. PersistentKV (June 2026) is the closest: a calibrated roofline-style policy that picks decode kernels on one RTX 3060, fp16 only, page size 16, focused on partition and scheduling. Loom shows tuning-free compilation with transfer across two hardware generations, but on Tenstorrent dataflow chips and not specific to attention. FlashInfer offers composable layouts and a scheduler but heuristic selection.");
  const hd = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.ink }, fontSize: 12, align: "center", valign: "middle" } });
  const nm = (t) => ({ text: t, options: { bold: true, fontSize: 12, valign: "middle" } });
  const Y = { text: "Yes", options: { align: "center", fontSize: 12, bold: true, color: "FFFFFF", fill: { color: "15803D" }, valign: "middle" } };
  const P = { text: "Partial", options: { align: "center", fontSize: 12, color: HEX.ink, fill: { color: "FDE68A" }, valign: "middle" } };
  const N = { text: "-", options: { align: "center", fontSize: 12, color: HEX.slate, fill: { color: "F1F5F9" }, valign: "middle" } };
  const Pl = { text: "Pending", options: { align: "center", fontSize: 12, bold: true, color: "FFFFFF", fill: { color: "4F46E5" }, valign: "middle" } };
  const rows = [
    [hd("System"), hd("Format axis"), hd("Layout axis"), hd("Partition axis"), hd("Analytic model"), hd("Cross-GPU transfer"), hd("Codegen")],
    [nm(`FlashInfer ${cite("flashinfer")}`), P, Y, Y, P, N, Y],
    [nm(`PersistentKV ${cite("pkv")}`), N, P, Y, Y, N, N],
    [nm(`LeanAttention ${cite("lean")}`), N, N, Y, N, N, N],
    [nm(`BitDecoding ${cite("bitdec")} / Minima-KV ${cite("minima")}`), Y, P, N, N, N, N],
    [nm(`Ansor ${cite("ansor")}`), N, N, N, P, N, Y],
    [nm(`Loom ${cite("loom")} (dataflow chips)`), N, N, N, Y, Y, Y],
    [nm("KVForge (this project)"), Y, Y, Y, Y, P, Y],
  ];
  s.addTable(rows, { x: 0.6, y: 1.4, w: 12.13, colW: [3.9, 1.3, 1.3, 1.4, 1.5, 1.6, 1.13], rowH: 0.52, border: { type: "solid", pt: 0.75, color: HEX.grid }, fontFace: "Calibri", color: HEX.ink });
  T(s, "Reading the table: Yes = a core feature, Partial = supported by heuristics or hand-built paths, - = not found. KVForge's transfer entry is Partial: tested on one second GPU, a similar consumer card. Prior art is judged from abstracts; full texts still to be checked.", { x: 0.6, y: 5.75, w: 12.13, h: 0.5, fontSize: 12, color: C.accent6 });
  rrect(s, 0.6, 6.2, 12.13, 0.7, "FDE68A");
  T(s, "No system in our sweep covers all three axes under one analytic model and tests it across GPU generations.", { x: 0.85, y: 6.2, w: 11.6, h: 0.7, fontSize: 15, bold: true, valign: "middle" });
}

// =================================================================== 15. gap
{
  const s = slide("The gap, in plain words", "Evidence",
    "Two gaps. First, nobody combines format, layout and partition under one analytic bandwidth model. Second, transfer across GPU generations is rarely tested. Be honest in the viva: novelty is moderate, PersistentKV is close for the partition axis, and our delta is the joint model, code generation, and the Ada to Blackwell transfer test. The sweep was keyword searches on arXiv; non-arXiv venues and full texts are not yet covered.");
  const g = [
    ["1", "No joint, analytic bandwidth model", `Existing work tunes one axis by hand: partition (LeanAttention, PersistentKV), representation (KIVI, BitDecoding, QServe), layout (PagedAttention, FlashInfer). Or it searches by measuring (Ansor). We found no model that scores all three together and picks without trials.`, PAL.indigo],
    ["2", "Transfer is rarely tested", `PersistentKV calibrates on one RTX 3060 and checks held-out workloads on that GPU. Loom shows cross-generation transfer, but on Tenstorrent chips. Predicting the right decode configuration on a different GPU generation (Ada → Blackwell) is not in our sweep.`, PAL.teal],
  ];
  g.forEach((c, i) => {
    const x = 0.6 + i * 6.15;
    rrect(s, x, 1.45, 5.98, 3.55, C.background2);
    badge(s, x + 0.3, 1.7, c[0], c[3]);
    T(s, c[1], { x: x + 0.9, y: 1.7, w: 4.9, h: 0.5, fontSize: 18, bold: true, valign: "middle" });
    T(s, c[2], { x: x + 0.3, y: 2.45, w: 5.4, h: 2.4, fontSize: 17 });
  });
  rrect(s, 0.6, 5.25, 12.13, 1.6, THEME.colors.dk1);
  T(s, "Honest verdict on novelty: moderate", { x: 0.9, y: 5.35, w: 6, h: 0.35, fontSize: 15, bold: true, color: C.accent2 });
  T(s, "PersistentKV (Jun 2026) is close prior art for the partition axis. Our defensible contribution is the three-axis model, code generation, and a two-GPU transfer test. The sweep covered arXiv keyword queries; non-arXiv venues and full texts are not yet checked.", { x: 0.9, y: 5.75, w: 11.5, h: 1.0, fontSize: 14, color: C.background1 });
}

// =================================================================== 16. cost model equations
{
  const s = slide("The cost model: the formulas", "Approach",
    "These are the equations the compiler evaluates for every candidate; docs/cost_model.md in the repo has the full table. H_load is H_kv with GQA packing and H without. cap is the number of blocks the whole GPU can hold at once: SMs times the blocks per SM allowed by block slots, warp slots and registers; the register count of each generated kernel is read back from the compiled binary. kappa is the ratio of loaded to idle memory latency, fitted once. The compute term counts warp instructions in the kernel's inner loop, not FLOPs, because the quantised kernels are limited by instruction issue, not by arithmetic.");
  const eqs = [
    ["1  Bytes moved", "B = 2·rows·(data + meta)·reread + B_qo", "reread = 1 when packed, else 1 + (g-1)(1 - hit·window)"],
    ["2  Effective element size", "b_eff = (bits + 32/G) / 8", "scale + zero point per group of G; G = 0 for fp16"],
    ["3  Arithmetic intensity", "I = 2g / b_eff   [FLOP/byte]", "n and d cancel; far below the ridge for every format"],
    ["4  Bandwidth (Little's law)", "BW = min( BW_peak , SMs·min( BW_sm , B_if/(κ·L) ) )", "bytes in flight per SM over loaded latency κ·L"],
    ["5  Waves", "imb = ceil(blocks/cap)·cap / blocks", "cap = SMs · min(block slots, warp slots, registers)"],
    ["6  Issue time", "T_cmp = warp_instr / (SMs·rate·issue_eff·occ)", "occ = 1 - exp(-warps_per_SM / w0); instructions counted"],
    ["7  Time", "T = ( T_mem^p + T_cmp^p )^(1/p) + T_merge + T_page + T_launch", "T_mem = B / (η·BW) · imb;  p-norm = imperfect overlap"],
    ["8  Overheads", "T_merge = f_m·launch + B_part/BW_L2;  T_launch = f_l·launch", "launch is measured; f_m and f_l are fitted fractions"],
  ];
  eqs.forEach((e, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.6 + col * 6.15, y = 1.4 + row * 1.37;
    rrect(s, x, y, 5.98, 1.25, i === 6 ? "FDE68A" : C.background2);
    T(s, e[0], { x: x + 0.2, y: y + 0.08, w: 5.6, h: 0.28, fontSize: 13, bold: true, color: C.accent1 });
    T(s, e[1], { x: x + 0.2, y: y + 0.38, w: 5.6, h: 0.55, fontSize: 11, fontFace: "Courier New", bold: true });
    T(s, e[2], { x: x + 0.2, y: y + 0.93, w: 5.6, h: 0.28, fontSize: 11, color: C.accent6 });
  });
}

// =================================================================== 17. formula basis
{
  const s = slide("Where each formula comes from", "Approach",
    "Every term is derived by counting, follows from a physical law, comes from a research result, is read from the compiled binary, or is a fitted constant. Ten constants are fitted, once, on the RTX 5060 and then frozen in model/constants_rtx5060.cal. The fit minimises log error plus selection regret on the fit shapes only; three shapes are held out. One of the fitted constants, r0, came out at its lower bound: the layout term is effectively switched off on this GPU, which matches the measurement that layout barely matters for fp16.");
  const h = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.ink }, fontSize: 13 } });
  const c = (t, o = {}) => ({ text: t, options: Object.assign({ fontSize: 12, valign: "middle" }, o) });
  const tag = (t, col) => ({ text: t, options: { fontSize: 12, bold: true, color: "FFFFFF", fill: { color: col }, align: "center", valign: "middle" } });
  const rows = [
    [h("Term"), h("Basis"), h("Why we trust it")],
    [c("Bytes, b_eff (1, 2)", { bold: true }), tag("Derived", "0F766E"), c(`Count: with reuse = 1 every row is read once per step; GQA packing divides loads by g ${cite("gqa")}; group-wise scale and zero ${cite("kivi", "kvquant", "qserve")}.`)],
    [c("Intensity (3)", { bold: true }), tag("Derived", "0F766E"), c(`Roofline (Williams, Waterman, Patterson, CACM 2009); same result in roofline analyses of decode ${cite("unveil")}.`)],
    [c("Bandwidth (4)", { bold: true }), tag("Physical law", "15803D"), c("Little's law: throughput = bytes in flight / latency. Peak, per-SM rate and idle latency are measured by bw_probe; the loaded-latency ratio κ is fitted (6-10x).")],
    [c("Waves (5)", { bold: true }), tag("Read from binary", "4F46E5"), c(`Wave quantisation on the resident capacity; registers per kernel come from cuobjdump of the compiled kernels (40 to 254, and different on Ada and Blackwell). Motivates stream-K decode ${cite("lean")}.`)],
    [c("Issue time (6)", { bold: true }), tag("Counted", "4F46E5"), c("Warp instructions counted from the kernel's inner loop; issue rate from the measured FMA throughput; one fitted efficiency and an occupancy term.")],
    [c("Overlap, overheads (7, 8)", { bold: true }), tag("Fitted", "BE123C"), c(`Log-sum-exp merge ${cite("osm")}; p-norm overlap, merge and launch fractions, page-stall time fitted on the fit shapes and then frozen.`)],
    [c("Sector size η", { bold: true }), tag("Measured", "475569"), c("32 B sectors confirmed by the bw_probe stride test; fp16 rows (256 B) are whole sectors, so η is about 1 on this GPU.")],
  ];
  s.addTable(rows, { x: 0.6, y: 1.4, w: 12.13, colW: [2.2, 1.9, 8.03], rowH: [0.4, 0.78, 0.62, 0.78, 0.9, 0.7, 0.78, 0.62], border: { type: "solid", pt: 0.75, color: HEX.grid }, fontFace: "Calibri", color: HEX.ink });
}

// =================================================================== 18. metrics
{
  const s = slide("Metrics: what we set out to measure, and what we got", "Evidence",
    "Targets were fixed before measuring. Prediction error and rank correlation are on the three held-out shapes, over all formats; the rank correlation of 0.88 narrowly misses the 0.9 target. Regret is on the held-out shapes: 1.9 percent when int8 is allowed, 13.9 percent over all formats, 15.3 percent for fp16 only; the fp16-only case misses the 10 percent target. Achieved bandwidth: the best fp16 plans reach about 347 GB/s, equal to the measured streaming peak. Selection cost: the compiler evaluates 2,688 candidates and writes its outputs in 147 ms, against about 30 minutes to time the same space.");
  const m = [
    ["Achieved bandwidth", "useful KV bytes / measured time, against the measured peak", "target: near peak", "result: best fp16 plan about 347 GB/s, at the 341 GB/s peak", PAL.teal],
    ["Prediction error (MAPE)", "mean |T_pred − T_meas| / T_meas over all candidates", "target: < 15%", "result: 15.2% held-out (17.4% fit); fp16 only 25%", PAL.indigo],
    ["Rank correlation", "Spearman ρ and Kendall τ between predicted and measured order", "target: ρ > 0.9", "result: ρ 0.88, τ 0.70 held-out: just short", PAL.indigo],
    ["Selection regret", "T_meas(chosen) / T_meas(best) − 1 over a shape suite", "target: < 10%", "result: 1.9% with int8, 13.9% all formats, 15.3% fp16 only", PAL.amber],
    ["Transfer error", "fit on the 5060, report MAPE and regret on the 4060 with no refit", "the headline result", "result: ρ 0.89, MAPE 23%, regret 6.6% (fp16) to 16.1% (all)", PAL.rose],
    ["Speedup vs baselines", "geometric mean over shapes against a baseline kernel", "context, not the claim", "result: 1.9× to 3.6× over a naive kernel; within 6% of FlashInfer (fp16)", PAL.slate],
    ["Numerical error", "relative L2 error against exact fp32 attention", "gate for lossy formats", "result: int8 0.8%, int4 11 to 14%, fp16 0.03%", PAL.green],
    ["Selection cost", "time to choose a plan against timing the space on the GPU", "target: ms vs minutes", "result: 147 ms vs about 30 minutes", PAL.slate],
  ];
  m.forEach((c, i) => {
    const col = i % 4, row = Math.floor(i / 4);
    const x = 0.6 + col * 3.06, y = 1.45 + row * 2.62;
    rrect(s, x, y, 2.93, 2.45, C.background2);
    box(s, x + 0.15, y + 0.15, 2.63, 0.5, c[4], c[0], { fontSize: 13, bold: true, color: c[4] === PAL.amber ? C.text1 : C.background1 });
    T(s, c[1], { x: x + 0.15, y: y + 0.75, w: 2.65, h: 0.7, fontSize: 11, color: C.accent6 });
    T(s, c[2], { x: x + 0.15, y: y + 1.45, w: 2.65, h: 0.3, fontSize: 11, bold: true });
    T(s, c[3], { x: x + 0.15, y: y + 1.75, w: 2.65, h: 0.65, fontSize: 12, bold: true, color: C.accent1 });
  });
  T(s, "Targets were fixed before measuring. Two are missed narrowly (rank correlation 0.88, fp16-only regret 15%).", { x: 0.6, y: 6.75, w: 12.13, h: 0.3, fontSize: 12, color: C.accent6 });
}

// =================================================================== R1. what we built
{
  const s = slide("What is built and verified", "Results",
    "Status against the plan. The compiler front end is a reuse of the earlier CPU prototype with a rewritten machine model, cost model and a new back end. The kernel library is the new work. Verification: every plan in the sweep is checked against a double-precision reference before it is timed; none failed.");
  const items = [
    ["Compiler", "Lexer, parser, IR, enumerator, accuracy gate, planner and CUDA code generation. 19 of 19 compiler tests pass.", PAL.indigo],
    ["Kernels", "One template library, 288 compiled kernels: 3 formats × 2 orders × 2 residencies × 3 pack sizes × 2 unrolls × 2 head sizes × 2 (final or partial).", PAL.teal],
    ["Machine probe", "bw_probe measures bandwidth, latency, L2, FMA rate, launch cost and the sector size on any NVIDIA GPU.", PAL.green],
    ["Ground truth", "20,928 plans timed on 10 shapes, plus 2,368 plans on awkward shapes. 0 failed verification.", PAL.amber],
    ["Model", "10 fitted constants, frozen. Scored on 3 held-out shapes it never saw.", PAL.rose],
    ["Second GPU", "Ran on an RTX 4060 Laptop: all 20,928 plans verified, constants unchanged, no refit.", PAL.slate],
  ];
  items.forEach((it, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = 0.6 + col * 4.1, y = 1.5 + row * 2.55;
    rrect(s, x, y, 3.93, 2.35, C.background2);
    box(s, x + 0.2, y + 0.2, 3.53, 0.5, it[2], it[0], { fontSize: 15, bold: true, color: it[2] === PAL.amber ? C.text1 : C.background1 });
    T(s, it[1], { x: x + 0.2, y: y + 0.85, w: 3.53, h: 1.4, fontSize: 14 });
  });
}

// =================================================================== R2. measured machine
{
  const s = slide("The machine, measured: RTX 5060 Laptop", "Results",
    "bw_probe output for the first GPU. These are the constants the model reads from the machine file; nothing is taken from a datasheet. The idle DRAM latency of 148 ns is much lower than the effective latency under load: the fit finds a loaded-to-idle ratio near 8, which is why bytes in flight matter so much. The 20.8 microsecond launch figure is the event-measured duration of an empty kernel on Windows, which is large enough to matter for the shortest kernels.");
  const h = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.ink }, fontSize: 13 } });
  const c = (t, o = {}) => ({ text: t, options: Object.assign({ fontSize: 13, valign: "middle" }, o) });
  const rows = [
    [h("Parameter"), h("Measured"), h("What it means")],
    [c("Compute capability, SMs", { bold: true }), c("12.0 (Blackwell), 26"), c("sm_120; 8.5 GB of memory")],
    [c("DRAM read bandwidth", { bold: true }), c("341 GB/s"), c("sustained, all SMs; the ceiling for decode")],
    [c("One SM", { bold: true }), c("79 GB/s"), c("one SM alone cannot reach the device ceiling")],
    [c("DRAM latency (idle)", { bold: true }), c("148 ns"), c("under load it behaves 6 to 10× longer")],
    [c("L2 bandwidth, L2 size", { bold: true }), c("1,581 GB/s, 32 MB"), c("where split partials are merged")],
    [c("FP32 throughput", { bold: true }), c("16.0 TFLOP/s"), c("ridge point at 47 FLOP/byte")],
    [c("Sector size", { bold: true }), c("32 B"), c("from the stride test, not assumed")],
    [c("Empty-kernel launch", { bold: true }), c("20.8 µs"), c("event-measured, WDDM")],
  ];
  s.addTable(rows, { x: 0.6, y: 1.45, w: 7.7, colW: [2.6, 2.1, 3.0], rowH: 0.52, border: { type: "solid", pt: 0.75, color: HEX.grid }, fontFace: "Calibri", color: HEX.ink });
  rrect(s, 8.6, 1.45, 4.13, 4.68, C.background2);
  T(s, "Why measured, not looked up", { x: 8.8, y: 1.6, w: 3.8, h: 0.4, fontSize: 16, bold: true, color: C.accent1 });
  T(s, "A datasheet quotes a peak no kernel reaches. The model needs the sustained rate, the latency, and the issue rate, and they differ per card.", { x: 8.8, y: 2.1, w: 3.75, h: 1.6, fontSize: 14 });
  T(s, "The same probe runs on the second GPU. That machine file is the only thing the transfer test changes.", { x: 8.8, y: 3.8, w: 3.75, h: 1.2, fontSize: 14 });
}

// =================================================================== R3. H1 result
{
  const s = slide("Hypothesis H1 holds: same bytes, up to 6.4× apart", "Results",
    "Among fp16 plans, which all move exactly the same number of KV bytes, the best and worst measured times differ by 1.8x to 6.4x depending on the shape. The big spreads are batch-1 grouped-query shapes, where there are few independent blocks and the split count, GQA packing and bytes in flight decide how many SMs stay busy. This is the evidence the original deck said was missing: reuse is 1 for all of these plans, so a reuse-based scheduler cannot tell them apart.");
  s.addImage({ path: FIGS + "h1_spread.png", x: 0.6, y: 1.4, w: 8.4, h: 8.4 / 1.957 });
  const stats = [["1.8×–6.4×", "best vs worst fp16 plan, per shape"], ["20,928", "plans timed, none failed verification"], ["6.4×", "worst case: batch 1, long context, GQA"]];
  stats.forEach((st, i) => {
    const y = 1.4 + i * 1.55;
    T(s, st[0], { x: 9.35, y, w: 3.4, h: 0.75, fontSize: 36, bold: true, color: C.accent1, fontFace: "Cambria" });
    T(s, st[1], { x: 9.35, y: y + 0.75, w: 3.4, h: 0.6, fontSize: 13, color: C.accent6 });
  });
  T(s, "Every bar is a plan that reads the same bytes, so the gap is entirely layout, partitioning and scheduling. On the RTX 4060 the spread is 1.1× to 4.6×.", { x: 0.6, y: 5.75, w: 8.4, h: 0.7, fontSize: 14 });
}

// =================================================================== R4. axes
{
  const s = slide("Which axes matter, and which do not", "Results",
    "Each bar is the best time achievable when one axis is forced to a given value, divided by the best time overall, as the median over the ten shapes. Teal is within 5 percent of optimal. Splitting and GQA packing are the large effects for fp16; layout is below 8 percent because a fp16 row is a whole number of memory sectors. The format axis is a large effect because fewer bytes move; the lossy formats pay an accuracy cost. Warps barely matter; unroll matters by about 11 percent. A negative result worth stating: placement, one of the three axes in the proposal, is nearly flat on this GPU.");
  s.addImage({ path: FIGS + "axis_effect.png", x: 0.6, y: 1.4, w: 8.3, h: 8.3 / 1.935 });
  const pts = [
    ["Matters a lot", "Splitting (up to 58%), GQA packing (40%), format (fp16 is 1.8× slower than the best lossy format)"],
    ["Matters a little", "Unroll (11%), layout (up to 8%)"],
    ["Does not matter", "Warps per block"],
  ];
  pts.forEach((p, i) => {
    const y = 1.4 + i * 1.5;
    T(s, p[0], { x: 9.2, y, w: 3.5, h: 0.4, fontSize: 16, bold: true, color: i === 0 ? C.accent4 : i === 1 ? C.accent2 : C.accent1 });
    T(s, p[1], { x: 9.2, y: y + 0.45, w: 3.5, h: 0.95, fontSize: 13 });
  });
  T(s, "Placement is nearly flat for fp16 on this GPU. We report that rather than hide it.", { x: 0.6, y: 5.55, w: 8.3, h: 0.7, fontSize: 14, bold: true });
}

// =================================================================== R5. model accuracy
{
  const s = slide("Does the model predict? Predicted against measured", "Results",
    "Each dot is one plan; the diagonal is a perfect prediction. Colours are the formats: teal fp16, amber int8, rose int4. Left are the seven shapes the constants were fitted on, right are the three held-out shapes. Over all formats the mean absolute percentage error is 17 percent on fitted shapes and 15 percent on held-out ones, so the model does not overfit; for fp16 alone it is 26 and 25 percent, because the fp16 plans are packed closer together in time. The staircase pattern is the wave quantisation: runtime jumps when the block count crosses a multiple of the resident capacity. Known gap: the model cannot predict that some split counts (16 and 32 on the 32k shape) run slower than both smaller and larger ones; we believe this is memory-channel conflicts, which are not modelled.");
  s.addImage({ path: FIGS + "pred_vs_meas.png", x: 0.6, y: 1.4, w: 8.1, h: 8.1 / 2.29 });
  const h = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.ink }, fontSize: 12, align: "center" } });
  const c = (t, o = {}) => ({ text: t, options: Object.assign({ fontSize: 12, align: "center" }, o) });
  s.addTable([
    [h("metric"), h("fit"), h("held-out")],
    [c("MAPE, all formats"), c("17.4%"), c("15.2%")],
    [c("MAPE, fp16 only"), c("26.4%"), c("25.1%")],
    [c("Spearman ρ, all"), c("0.88"), c("0.88")],
    [c("Kendall τ, all"), c("0.71"), c("0.70")],
    [c("Regret, fp16 only"), c("8.9%"), c("15.3%")],
    [c("Regret, int8 allowed"), c("4.0%"), c("1.9%")],
    [c("Regret, all formats"), c("10.1%"), c("13.9%")],
  ], { x: 9.0, y: 1.45, w: 3.73, colW: [1.85, 0.9, 0.98], rowH: 0.4, border: { type: "solid", pt: 0.75, color: HEX.grid }, fontFace: "Calibri", color: HEX.ink });
  T(s, "Regret = how much slower the model's pick is than the best plan in the sweep. With int8 allowed it is 1.9% on shapes the fit never saw.", { x: 9.0, y: 4.85, w: 3.73, h: 1.1, fontSize: 12 });
  T(s, "Not captured: non-monotone split counts (suspected memory-channel conflicts).", { x: 9.0, y: 6.0, w: 3.73, h: 0.7, fontSize: 11, color: C.accent6 });
}

// =================================================================== R6. compiler pick vs baseline
{
  const s = slide("What the compiler's pick buys: measured speedup", "Results",
    "For every shape the compiler picks the plan with the smallest predicted time and nothing is run. This slide reports how that plan actually measured. The baseline is a plain first kernel in our own family: fp16, token-major, contiguous, no splitting, no GQA packing, four warps, unroll two. It is NOT FlashInfer or another tuned library, so these speedups are over a naive kernel; the next slide gives the comparison with the libraries. Regret is how much slower the pick is than the best plan an exhaustive search of the sweep would have found. Lossless means fp16 only; int8 allowed uses the 0.02 accuracy limit; all formats includes int4, whose measured relative error is 11 to 14 percent.");
  const h = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.ink }, fontSize: 13, align: "center" } });
  const c = (t, o = {}) => ({ text: t, options: Object.assign({ fontSize: 13, align: "center", valign: "middle" }, o) });
  s.addTable([
    [h("Eligible formats"), h("Geomean speedup over baseline"), h("Mean regret (all 10 shapes)"), h("Best shape")],
    [c("lossless (fp16 only)", { align: "left", bold: true }), c("1.93×", { bold: true }), c("11.4%"), c("3.7× (batch 1, 64k)")],
    [c("int8 allowed (error ≤ 0.02)", { align: "left", bold: true }), c("3.00×", { bold: true }), c("5.8%"), c("6.2× (batch 1, 64k)")],
    [c("all formats (incl. int4)", { align: "left", bold: true }), c("3.64×", { bold: true }), c("11.2%"), c("7.0× (batch 1, 64k)")],
  ], { x: 0.6, y: 1.5, w: 12.13, colW: [3.6, 3.3, 2.9, 2.33], rowH: 0.62, border: { type: "solid", pt: 0.75, color: HEX.grid }, fontFace: "Calibri", color: HEX.ink });
  const cards = [
    ["Honest baseline", "A naive first kernel in our own family, not a tuned library. The next slide compares against FlashInfer and PyTorch."],
    ["Chosen without running", "The plan is picked from the model alone: zero trials on the GPU, in milliseconds."],
    ["Lossy has a price", "int8 error is 0.8%; int4 is 11 to 14%. The accuracy gate lets the user decide."],
  ];
  cards.forEach((cd, i) => {
    const x = 0.6 + i * 4.1;
    rrect(s, x, 4.45, 3.93, 2.3, C.background2);
    T(s, cd[0], { x: x + 0.25, y: 4.6, w: 3.45, h: 0.4, fontSize: 16, bold: true, color: C.accent1 });
    T(s, cd[1], { x: x + 0.25, y: 5.1, w: 3.45, h: 1.55, fontSize: 14 });
  });
}

// =================================================================== R6b. library comparison
{
  const s = slide("Against FlashInfer and PyTorch: within 6% on average", "Results",
    "All methods ran in one process under WSL2 on the same GPU, with the same K and V, the same timer (CUDA events) and an L2 flush before every repetition; every output was checked against an fp32 reference. FlashInfer used its batch decode kernel with a paged cache (page size 16) from its pre-built kernel package; its single-request kernel needs a CUDA compiler we do not have in WSL. PyTorch SDPA is shown as its fastest working backend (cuDNN or flash); the efficient backend is 5 to 10 times slower and is ignored. KVForge kernels were compiled on Windows and loaded in WSL, so they are the same kernels the sweep timed. Only fp16 is compared, because that is what all three support. At large contexts every method sits at the 341 GB/s memory limit, which is why the bars converge; the differences appear on the smaller shapes. Where we lose: the group-size-8 shape (H64/8). The 8-head-pack kernel uses 201 to 248 registers per thread, so only one 8-warp block fits per SM; this is a plausible cause, not proven.");
  s.addImage({ path: FIGS + "compare_library.png", x: 0.6, y: 1.35, w: 8.4, h: 8.4 / 2.083 });
  const stats = [["1.06×", "KVForge's pick, vs FlashInfer's time (0.94× to 1.33×)"], ["1.02×", "PyTorch SDPA, vs FlashInfer's time"], ["2.12×", "naive baseline, vs FlashInfer's time"]];
  stats.forEach((st, i) => {
    const y = 1.35 + i * 1.4;
    T(s, st[0], { x: 9.35, y, w: 3.4, h: 0.7, fontSize: 34, bold: true, color: i === 0 ? C.accent1 : i === 1 ? C.accent6 : C.accent4, fontFamily: "Cambria" });
    T(s, st[1], { x: 9.35, y: y + 0.7, w: 3.4, h: 0.6, fontSize: 12, color: C.accent6 });
  });
  const cards = [
    ["Same footing", "One process, GPU, data, timer and cache flush. Outputs checked against fp32. FlashInfer ran its pre-built paged batch-decode kernels.", C.accent1],
    ["Where we lose", "Group size 8 (H64/8): 33% slower; even the best plan in our sweep is 31% slower. That kernel needs 201 to 248 registers per thread, so one block per SM fits.", C.accent4],
    ["What it means", "A compiler-chosen kernel from one template reaches library speed on this GPU, without beating it. Large contexts all hit the 341 GB/s limit.", C.accent2],
  ];
  cards.forEach((cd, i) => {
    const x = 0.6 + i * 4.1;
    rrect(s, x, 5.75, 3.93, 1.2, C.background2);
    T(s, cd[0], { x: x + 0.2, y: 5.8, w: 3.55, h: 0.3, fontSize: 13, bold: true, color: cd[2] === C.accent2 ? C.text1 : cd[2] });
    T(s, cd[1], { x: x + 0.2, y: 6.1, w: 3.55, h: 0.85, fontSize: 11 });
  });
}

// =================================================================== T1. transfer result
{
  const s = slide("Transfer test: frozen constants on the RTX 4060", "Results",
    "The experiment the project was built for. The constants were fitted once on the RTX 5060 (SHA-256 of the file unchanged by this test); the only inputs from the 4060 are its own bw_probe machine file and the Ada register table of the compiled kernels. No refit. The 4060 sweep covered the same 20,928 plans on the same ten shapes and every plan verified. Rank correlation is 0.886 against 0.88 on the 5060's held-out shapes: the model orders plans as well on a different GPU. Absolute time error is larger (22.6 percent against 15.2), mostly because some fitted constants, launch and merge overheads and L2 reuse, are GPU or driver dependent. Success criteria were written before the run: rank correlation near 0.88 was met; the pick within 10 to 15 percent of the best plan was met for fp16 (6.6) and int8 (11.8) and narrowly missed for all formats (16.1). H1 also holds on the 4060: equal-byte fp16 plans differ by 1.1 to 4.6 times.");
  s.addImage({ path: "C:/Users/aahav/KVForge/results/figs_rtx4060/pred_vs_meas.png", x: 0.6, y: 1.4, w: 4.9, h: 4.9 / 1.25 });
  T(s, "Predicted against measured on the 4060, all 20,928 plans. Colours: teal fp16, amber int8, rose int4.", { x: 0.6, y: 5.4, w: 4.9, h: 0.6, fontSize: 11, color: C.accent6 });
  const h = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.ink }, fontSize: 12, align: "center" } });
  const c = (t, o = {}) => ({ text: t, options: Object.assign({ fontSize: 12, align: "center", valign: "middle" }, o) });
  s.addTable([
    [h("metric"), h("5060 held-out"), h("4060 transfer")],
    [c("Spearman ρ, all formats"), c("0.88"), c("0.89", { bold: true })],
    [c("Kendall τ, all formats"), c("0.70"), c("0.71", { bold: true })],
    [c("MAPE, all / fp16 only"), c("15.2% / 25.1%"), c("22.6% / 35.2%")],
    [c("Regret, fp16 only"), c("15.3%"), c("6.6%", { bold: true })],
    [c("Regret, int8 allowed"), c("1.9%"), c("11.8%")],
    [c("Regret, all formats"), c("13.9%"), c("16.1%")],
    [c("Speedup vs naive baseline\n(fp16 / int8 / all)"), c("1.9× / 3.0× / 3.6×"), c("1.5× / 2.3× / 3.2×")],
  ], { x: 5.8, y: 1.4, w: 6.93, colW: [2.9, 2.0, 2.03], rowH: [0.38, 0.38, 0.38, 0.38, 0.38, 0.38, 0.38, 0.6], border: { type: "solid", pt: 0.75, color: HEX.grid }, fontFace: "Calibri", color: HEX.ink });
  const cards = [
    ["Met", "Rank correlation stays near 0.88: got 0.886.", PAL.green],
    ["Mostly met", "Pick within 10 to 15% of best: fp16 6.6%, int8 11.8%, all formats 16.1%.", PAL.amber],
    ["What differs by GPU", "A refit on the 4060 moves launch, merge and L2-reuse constants most; it cuts time error, not regret.", PAL.slate],
  ];
  cards.forEach((cd, i) => {
    const x = 0.6 + i * 4.1;
    rrect(s, x, 6.0, 3.93, 0.98, C.background2);
    T(s, cd[0], { x: x + 0.2, y: 6.05, w: 3.55, h: 0.28, fontSize: 12, bold: true, color: cd[2] === PAL.amber ? C.text1 : cd[2] });
    T(s, cd[1], { x: x + 0.2, y: 6.33, w: 3.55, h: 0.65, fontSize: 11 });
  });
}

// =================================================================== T2. controls and failure
{
  const s = slide("Against the alternatives, and where it fails", "Results",
    "Controls added so the transfer number has context. Reuse the 5060's measured winner is the practical alternative to a model: tune once, copy the plan. For a shape that was already tuned on a sibling GPU it beats the model (2.3 / 7.1 / 6.8 percent regret against 6.6 / 11.8 / 16.1); the two GPUs rank plans alike (measured plan-by-plan rank correlation 0.85), so copying works. The new-shape test reuses the nearest other shape's winner (our own simple donor rule, same head size, nearest context length and batch): the mean regret matches the model, the worst case is much worse (46 / 61 / 64 percent against 17 / 42 / 55). The refit control (separate file, not the transfer result) scored on three shapes held out from the refit: it cuts MAPE (fp16 32 to 16 percent) but not regret (3.9 against 3.7; 12.0 against 12.0; 19.5 against 12.5). The failure: shape H64/8, n 8192. The model predicts fp16 157 us and int8 161 us, a near tie; measured 200 and 152. The fp16 8-head-pack kernel uses 216 to 250 registers per thread on Ada and runs slower than the model expects. Nothing was tuned to hide it.");
  const h = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.ink }, fontSize: 12, align: "center" } });
  const c = (t, o = {}) => ({ text: t, options: Object.assign({ fontSize: 12, align: "center", valign: "middle" }, o) });
  s.addTable([
    [h("Mean regret on the 4060 (worst shape)"), h("fp16 only"), h("int8 allowed"), h("all formats")],
    [c("KVForge model, frozen 5060 constants", { align: "left", bold: true }), c("6.6% (17%)"), c("11.8% (42%)"), c("16.1% (55%)")],
    [c("Reuse the 5060's winner, same shape", { align: "left", bold: true }), c("2.3% (8%)"), c("7.1% (22%)"), c("6.8% (18%)")],
    [c("Reuse nearest other shape's winner (unseen shape)", { align: "left", bold: true }), c("8.1% (46%)"), c("12.5% (61%)"), c("16.2% (64%)")],
  ], { x: 0.6, y: 1.4, w: 12.13, colW: [5.2, 2.2, 2.4, 2.33], rowH: 0.5, border: { type: "solid", pt: 0.75, color: HEX.grid }, fontFace: "Calibri", color: HEX.ink });
  const cards = [
    ["What this says", "Ranking transfers (ρ 0.89). For a shape already tuned on a sibling GPU, copying its winner is better than the model; the two GPUs rank plans alike (0.85). For an unseen shape the model matches the heuristic on average with a far better worst case.", PAL.teal],
    ["Where it fails", "H64/8 (8-head packing): the model sees fp16 and int8 as a tie (157 vs 161 us); measured 200 vs 152 us. The fp16 pack-8 kernel needs 216 to 250 registers per thread on Ada. Same kernel that trails FlashInfer.", PAL.rose],
    ["Refit control", "Refitting on 4060 data cuts time error (fp16 MAPE 32% to 16%) but not regret. The frozen constants mis-predict absolute time more than they mis-rank plans.", PAL.slate],
  ];
  cards.forEach((cd, i) => {
    const x = 0.6 + i * 4.1;
    rrect(s, x, 3.75, 3.93, 3.05, C.background2);
    box(s, x + 0.2, 3.9, 3.53, 0.45, cd[2], cd[0], { fontSize: 14, bold: true });
    T(s, cd[1], { x: x + 0.2, y: 4.5, w: 3.55, h: 2.2, fontSize: 13 });
  });
}

// =================================================================== 19. plan
{
  const s = slide("Plan and status", "Plan",
    "Where each phase stands. Weeks are indicative and assume a 13-week semester; the first three phases were compressed into a day of build time because the kernels, probe and harness could be written together. The baseline comparison covers a naive kernel, FlashInfer and PyTorch SDPA; both the transfer test and the library comparison are done.");
  const ph = [
    ["Weeks 1-3", "Setup and evidence", "Done: CUDA 13.4 toolchain, bw_probe, 20,928-plan sweep. H1 holds (1.8 to 6.4×).", PAL.green],
    ["Weeks 4-6", "Fit the model", "Done: 10 constants fitted on 7 shapes, scored on 3 held-out.", PAL.green],
    ["Weeks 7-9", "Build the compiler", "Done: parser to CUDA codegen, accuracy gate, kernels verified.", PAL.green],
    ["Weeks 10-11", "Transfer test", "Done: RTX 4060, no refit. ρ 0.89; regret 6.6% to 16.1%; one shape fails.", PAL.green],
    ["Weeks 12-13", "Baselines and report", "Done: naive baseline, FlashInfer and PyTorch SDPA (fp16). Report text remains.", PAL.green],
  ];
  ph.forEach((p, i) => {
    const x = 0.6 + i * 2.45;
    s.addText(p[0], { shape: pres.ShapeType.homePlate, x, y: 1.45, w: 2.4, h: 0.75, fill: { color: p[3] }, line: { type: "none" }, align: "center", valign: "middle", fontSize: 14, bold: true, color: p[3] === PAL.amber ? C.text1 : C.background1, margin: 2 });
    T(s, p[1], { x, y: 2.4, w: 2.3, h: 0.4, fontSize: 15, bold: true });
    T(s, p[2], { x, y: 2.85, w: 2.3, h: 1.5, fontSize: 13 });
  });
  rrect(s, 0.6, 4.55, 12.13, 2.25, C.background2);
  T(s, "Hardware", { x: 0.85, y: 4.7, w: 5, h: 0.3, fontSize: 14, bold: true, color: C.accent1 });
  T(s, [
    { text: "RTX 5060 Laptop GPU: Blackwell, compute capability 12.0, 26 SMs, 8.5 GB (all measurements so far)", options: { bullet: true, breakLine: true } },
    { text: "RTX 4060 Laptop (a friend's): Ada, compute capability 8.9, 24 SMs (measured, transfer test done)", options: { bullet: true, breakLine: true } },
    { text: "Single-layer decode benchmarks fit in memory on both; full-model runs are out of scope", options: { bullet: true } },
  ], { x: 0.85, y: 5.15, w: 11.6, h: 1.6, fontSize: 16, paraSpaceAfter: 8 });
}

// =================================================================== 20. risks
{
  const s = slide("Risks: what actually happened", "Plan",
    "Each risk from the proposal and its outcome. H1 held. The toolchain needed the Microsoft C++ build tools, and Windows Smart App Control blocked one large two-architecture executable; a single-architecture build ran, and no security setting was changed. The baseline caveat is the important open item.");
  const r = [
    ["H1 fails: configurations barely differ", "Held: equal-byte fp16 plans differ by 1.8 to 6.4× depending on the shape.", PAL.green],
    ["We are not faster than FlashInfer", "Confirmed and measured: the pick is 1.06× FlashInfer's time on average (0.94× to 1.33×), fp16, same GPU and timer.", PAL.amber],
    ["Blackwell (sm_120) toolchain is new", "Compiles and runs. Needed MSVC build tools; Smart App Control blocked a large fat binary, a smaller build ran.", PAL.indigo],
    ["Laptop GPU noise", "On AC power, GPU idle, L2 flushed every repeat, 20 repeats with median and IQR recorded.", PAL.teal],
    ["Quantization changes the answer", "Gate in place. Measured error: int8 0.8%, int4 11 to 14%.", PAL.green],
    ["Second GPU availability", "Done: the package ran on the friend's RTX 4060 and all 20,928 plans verified.", PAL.green],
  ];
  r.forEach((c, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.6 + col * 6.15, y = 1.45 + row * 1.8;
    rrect(s, x, y, 5.98, 1.65, C.background2);
    badge(s, x + 0.2, y + 0.2, i + 1, c[2]);
    T(s, c[0], { x: x + 0.85, y: y + 0.15, w: 5.0, h: 0.5, fontSize: 15, bold: true, valign: "middle" });
    T(s, c[1], { x: x + 0.85, y: y + 0.75, w: 5.0, h: 0.85, fontSize: 13 });
  });
}

// =================================================================== 21. contributions
{
  const s = slide("What this project contributes", "Plan",
    "Three contributions: a precise problem statement, a mechanism, and an evidence standard. The first two now have measurements behind them. The third is set up but not yet run. We do not claim a faster kernel than hand-tuned libraries.");
  const c = [
    ["1", "The problem statement", "Decode attention has reuse 1, so reuse-based scheduling has nothing to say. Measured: plans that move identical bytes differ by 1.8 to 6.4×."],
    ["2", "The mechanism", "An analytic bandwidth model over representation, placement and partition, in a compiler that emits verified CUDA. Its pick is 1.9× to 3.6× faster than a naive baseline, within about 6 to 11% of the best plan, and within 6% of FlashInfer in fp16."],
    ["3", "The evidence standard", "A model fitted on one GPU that still ranks plans well on another with no refit: rank correlation 0.886 on the RTX 4060 (0.88 held-out on the 5060); regret 6.6% to 16.1%. Reusing a winner tuned on the sibling GPU does better when the shape was already tuned."],
  ];
  c.forEach((x, i) => {
    const y = 1.5 + i * 1.55;
    rrect(s, 0.6, y, 12.13, 1.4, C.background2);
    badge(s, 0.9, y + 0.45, x[0], PAL.teal);
    T(s, x[1], { x: 1.65, y: y + 0.15, w: 3.4, h: 1.1, fontSize: 18, bold: true, valign: "middle" });
    T(s, x[2], { x: 5.1, y: y + 0.1, w: 7.4, h: 1.2, fontSize: 14, valign: "middle" });
  });
  rrect(s, 0.6, 6.15, 12.13, 0.75, THEME.colors.dk1);
  T(s, "Not claimed: a faster kernel than FlashInfer. Measured: 6% slower on average, 33% slower on the group-size-8 shape, 6% faster on one.", { x: 0.9, y: 6.15, w: 11.6, h: 0.75, fontSize: 14, color: C.background1, valign: "middle" });
}

// =================================================================== 22-23. references
function refSlide(title, part, from, to) {
  const s = slide(title, "References", "Every ID was checked against the arXiv API: the title and year match. Links are https://arxiv.org/abs/<ID>.");
  const list = REFS.slice(from, to);
  const runs = [];
  list.forEach((r, i) => {
    const n = from + i + 1;
    runs.push({ text: `[${n}] `, options: { bold: true, color: C.accent1 } });
    runs.push({ text: `${r[1]}  `, options: {} });
    runs.push({ text: `arXiv:${r[2]} (${r[3]})`, options: { color: C.accent6, breakLine: i < list.length - 1 } });
  });
  T(s, runs, { x: 0.6, y: 1.4, w: 12.13, h: 5.0, fontSize: 13, paraSpaceAfter: 7 });
  return s;
}
refSlide("References (1 of 2)", 1, 0, 15);
{
  const s = refSlide("References (2 of 2)", 2, 15, 30);
  s.addText("Also cited, not on arXiv: Williams, Waterman, Patterson. Roofline: an insightful visual performance model. CACM 52(4), 2009.  |  Little. A proof for the queuing formula L = λW. Operations Research 9(3), 1961.  |  NVIDIA CUDA C++ Programming Guide (memory coalescing).  |  Sweep: arXiv API keyword queries through Oct 2026; abstracts read, full texts not.",
    { isTextBox: true, x: 0.6, y: 6.3, w: 12.13, h: 0.7, margin: 0, fontSize: 11, color: C.accent6, valign: "top" });
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
