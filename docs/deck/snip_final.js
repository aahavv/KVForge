// =================================================================== BASE-PAPER SLIDES
// (inserted after the "gap" slide by make_final.py)
{
  const s = slide("Base paper: PersistentKV (arXiv 2606.26666)", "Evidence",
    "Our base paper. Read in full (9 pages). Single author, arXiv preprint June 2026, revised July 2026; no peer-reviewed venue is stated, and the paper itself calls its evidence workshop-level. It is the closest prior work: same operator (GQA decode attention), the same Llama-style shape we use most (32 query heads, 8 KV heads, d 128), a commodity GPU (RTX 3060), and, crucially, a calibrated roofline-style cost model with constants fixed on calibration data and tested on held-out data. That is the methodology we follow, which is why we treat it as the base. The formula on the slide is the paper's equation in section 3.5, with its measured constants.");
  rrect(s, 0.6, 1.4, 5.0, 5.5, C.background2);
  T(s, "The paper", { x: 0.85, y: 1.55, w: 4.5, h: 0.4, fontSize: 18, bold: true, color: C.accent1 });
  T(s, [
    { text: "PersistentKV: Page-Aware Decode Scheduling for Long-Context LLM Serving on Commodity GPUs", options: { bold: true, breakLine: true } },
    { text: "M. Ahmed, arXiv:2606.26666 (Jun 2026, v2 Jul 2026), preprint", options: { color: C.accent6, breakLine: true } },
    { text: " ", options: { breakLine: true } },
    { text: "Setup: RTX 3060, fp16, page size 16, 32 query / 8 KV heads, d 128 (our Llama-3 shape)", options: { breakLine: true } },
    { text: " ", options: { breakLine: true } },
    { text: "Built: a paged decode kernel that splits the sequence and maps one block per KV-head group, plus a policy that chooses between FlashInfer and its own routes with a cost model:", options: { breakLine: true } },
  ], { x: 0.85, y: 2.0, w: 4.55, h: 3.2, fontSize: 13 });
  rrect(s, 0.85, 4.95, 4.5, 1.2, "FFFFFF");
  T(s, "T = KVBytes/β · max(1, C_min/C_r)\n    + L_r·λ + MergeBytes/β", { x: 0.95, y: 5.02, w: 4.3, h: 0.55, fontSize: 11, bold: true, fontFace: "Consolas" });
  T(s, "β 331.2 GB/s, C_min 4 blocks/SM, λ 8.19 µs; fitted on one seed, tested on five", { x: 0.95, y: 5.62, w: 4.3, h: 0.45, fontSize: 10.5, color: C.accent6 });
  T(s, "Section 3.5 of the paper", { x: 0.85, y: 6.3, w: 4.5, h: 0.3, fontSize: 11, color: C.accent6 });
  T(s, "What it found", { x: 5.9, y: 1.4, w: 6.8, h: 0.4, fontSize: 18, bold: true, color: C.accent1 });
  const f = [
    ["FlashInfer is the fastest single kernel", "Its own kernel is 1.044× slower in isolation (Table 1).", PAL.slate],
    ["Work assignment is decisive", "Sequence splitting: 1.40× wall throughput at batch 1, long context; workqueue 1.04–1.08× at batch 8.", PAL.teal],
    ["Split counts are not monotone", "Neighbouring split counts swing results (Table 7); it uses conservative multiples of 4.", PAL.amber],
    ["Group sizes 1 and 8 lose", "Only G = 4 is calibrated; G = 1 and G = 8 are routed to FlashInfer.", PAL.rose],
    ["Constants are per GPU", "\"Not derived hardware invariants; a different GPU should re-fit them.\" Only one GPU tested.", PAL.indigo],
    ["Quantization left open", "fp16 only; \"dequantization-aware paged decode\" listed as future work.", PAL.green],
  ];
  f.forEach((c, i) => {
    const y = 1.9 + i * 0.83;
    rrect(s, 5.9, y, 6.83, 0.74, C.background2);
    rect(s, 5.9, y, 0.1, 0.74, c[2]);
    T(s, c[0], { x: 6.15, y: y + 0.06, w: 6.5, h: 0.3, fontSize: 13.5, bold: true });
    T(s, c[1], { x: 6.15, y: y + 0.36, w: 6.5, h: 0.36, fontSize: 11.5, color: C.accent6 });
  });
}
{
  const s = slide("What the base paper gives us, and what we add", "Evidence",
    "Row by row: a finding of the base paper, what we did with it, and what we measured. Four of its findings we reproduce independently on different GPUs (FlashInfer is hard to beat; partition decides; split counts are not monotone; group size 8 is hard). Three of its open points are our contributions: the format axis with an accuracy gate, a compiler with a language and IR instead of a fixed route policy, and the cross-GPU test it says requires refitting. Our test agrees with it in part: absolute times do need refitting (time error rises from 15 to 23 percent), but the ranking of plans transfers (0.886).");
  const h = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.ink }, fontSize: 12, valign: "middle" } });
  const c = (t, o = {}) => ({ text: t, options: Object.assign({ fontSize: 11.5, valign: "middle" }, o) });
  const tag = (t, col) => ({ text: t, options: { fontSize: 11, bold: true, color: "FFFFFF", fill: { color: col }, align: "center", valign: "middle" } });
  const SAME = "0F766E", NEW = "4F46E5", OPEN = "BE123C";
  s.addTable([
    [h("Base paper finding"), h(""), h("What we did with it"), h("Our measured result")],
    [c("Decode is limited by KV movement, not arithmetic"), tag("same", SAME), c("Cost model built on bytes, bandwidth and latency"), c("4 FLOP/byte vs the GPU's ridge of 47")],
    [c("Work assignment (splits, KV-head groups) is decisive"), tag("same", SAME), c("Splits and GQA packing are compiler holes"), c("Wrong split up to 58% slower; no packing 40%")],
    [c("Small calibrated roofline model, held-out test"), tag("extended", NEW), c("Same method, richer model: Little's law, registers, issue rate, waves; 7 fit / 3 held-out shapes"), c("Rank correlation 0.88 held out")],
    [c("FlashInfer is the best single kernel"), tag("same", SAME), c("Compared on the same GPU and timer"), c("Our pick 1.06× FlashInfer's time")],
    [c("Split counts are not monotone"), tag("same", SAME), c("Seen in our sweep too"), c("Not yet modelled (open)")],
    [c("Group size 8 loses, routed away"), tag("same", SAME), c("Our 8-head pack kernel is register-heavy"), c("33% slower on H64/8; fails one 4060 shape")],
    [c("fp16 only; quantization is future work"), tag("new", NEW), c("int8 / int4 formats behind an accuracy budget in the language"), c("3.0× / 3.6× vs naive; int8 error 0.8%")],
    [c("A fixed policy over three routes"), tag("new", NEW), c("A compiler: .kv language, IR with holes, passes, CUDA codegen"), c("2,688 plans searched, 44,224 runs verified")],
    [c("\"A different GPU should re-fit\"; one GPU only"), tag("tested", OPEN), c("Frozen constants run on a second GPU generation"), c("Ranking transfers (ρ 0.886); times need refit (error 15→23%)")],
  ], { x: 0.6, y: 1.35, w: 12.13, colW: [3.5, 1.0, 4.03, 3.6], rowH: 0.47, border: { type: "solid", pt: 0.75, color: HEX.grid }, fontFace: "Calibri", color: HEX.ink });
  rrect(s, 0.6, 6.25, 12.13, 0.65, THEME.colors.dk1);
  T(s, "Its open problems are our contributions: the format axis, a compiler, and the cross-GPU test. Its caution holds for times, not for rankings.", { x: 0.85, y: 6.25, w: 11.7, h: 0.65, fontSize: 14, bold: true, color: C.background1, valign: "middle" });
}

// =================================================================== DEMO SLIDE
// (inserted before the plan slide by make_final.py)
{
  const s = slide("Live demo: one Llama-3-8B layer, three programs", "Results",
    "Run live with: powershell -ExecutionPolicy Bypass -File demo\\run_demo.ps1 -Pause. Each program is compiled by kvf.exe with the measured machine file and frozen constants, the generated CUDA is built by nvcc, checked against a double-precision reference and timed (50 runs, L2 flushed before each). The numbers on the slide are a recorded run (demo/demo_output_recorded.txt). For any other model: demo\\try_model.ps1 asks for the model, context length, batch and budget. Example: Qwen2.5-7B, 4,096 tokens, 64 users, budget 0.2 gave 1.71x over naive with int4, but the predicted times were 2.5 to 3.1x too low, because that shape (batch 64, 7 query heads per KV head, no packing possible) is far outside the fitted range; the ranking was still right.");
  const progs = [
    ["1_baseline.kv", "everything pinned", "K: kvcache<n, d, f16, token_major, contiguous>\nsplits = 1, gqa_pack = false", PAL.slate],
    ["2_lossless.kv", "compiler chooses, fp16 only", "K: kvcache<n, d, ?, ?, ?>\nsplits = ?, gqa_pack = ?", PAL.teal],
    ["3_budget.kv", "+ accuracy budget", "target max_rel_err = 0.02\nK: kvcache<n, d, ?, ?, ?> ...", PAL.indigo],
  ];
  progs.forEach((p, i) => {
    const x = 0.6 + i * 4.1;
    rrect(s, x, 1.4, 3.93, 1.75, C.background2);
    rect(s, x, 1.4, 3.93, 0.1, p[3]);
    T(s, p[0], { x: x + 0.2, y: 1.6, w: 3.5, h: 0.35, fontSize: 15, bold: true, fontFace: "Consolas" });
    T(s, p[1], { x: x + 0.2, y: 1.95, w: 3.5, h: 0.3, fontSize: 12, color: C.accent6 });
    T(s, p[2], { x: x + 0.2, y: 2.35, w: 3.6, h: 0.75, fontSize: 10.5, fontFace: "Consolas" });
  });
  const h = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.ink }, fontSize: 12, align: "center" } });
  const c = (t, o = {}) => ({ text: t, options: Object.assign({ fontSize: 12, align: "center", valign: "middle" }, o) });
  s.addTable([
    [h("Program"), h("Plan the compiler chose"), h("Check"), h("Error vs exact"), h("Predicted"), h("Measured"), h("Speedup")],
    [c("1_baseline", { bold: true }), c("f16, token-major, no split"), c("PASS"), c("0.03%"), c("1168 µs"), c("845 µs"), c("1.00×")],
    [c("2_lossless", { bold: true }), c("f16, head-major, split 32, packed"), c("PASS"), c("0.03%"), c("425 µs"), c("430 µs"), c("1.96×", { bold: true, color: "0F766E" })],
    [c("3_budget", { bold: true }), c("int8:128, head-major, split 32, packed"), c("PASS"), c("0.84%"), c("313 µs"), c("273 µs"), c("3.09×", { bold: true, color: "0F766E" })],
  ], { x: 0.6, y: 3.4, w: 12.13, colW: [1.7, 3.83, 1.1, 1.5, 1.3, 1.3, 1.4], rowH: 0.45, border: { type: "solid", pt: 0.75, color: HEX.grid }, fontFace: "Calibri", color: HEX.ink });
  rrect(s, 0.6, 5.45, 5.95, 1.45, C.background2);
  T(s, "Run it", { x: 0.8, y: 5.55, w: 5.5, h: 0.3, fontSize: 13, bold: true, color: C.accent1 });
  T(s, "demo\\run_demo.ps1 -Pause\ndemo\\try_model.ps1   (any model: asks H, H_kv, d, n, batch, budget)", { x: 0.8, y: 5.9, w: 5.6, h: 0.9, fontSize: 11, fontFace: "Consolas" });
  rrect(s, 6.78, 5.45, 5.95, 1.45, "FDE68A");
  T(s, "Off the fitted range", { x: 6.98, y: 5.55, w: 5.5, h: 0.3, fontSize: 13, bold: true });
  T(s, "Qwen2.5-7B, 4k tokens, 64 users: int4 pick 1.71× faster than naive, ranking right, but times predicted 2.5–3.1× too low (no packing possible at 7 heads per KV head).", { x: 6.98, y: 5.88, w: 5.6, h: 0.95, fontSize: 11.5 });
}

// =================================================================== REFERENCES (3 slides, linked, base paper highlighted)
function refSlideLinked(title, from, to) {
  const s = slide(title, "References", "Every arXiv ID was checked against the arXiv API: title and year match. Each line is a clickable link to https://arxiv.org/abs/<ID>. The base paper, PersistentKV, was read in full; the others from abstracts.");
  const rowH = 0.5;
  REFS.slice(from, to).forEach((r, i) => {
    const n = from + i + 1;
    const y = 1.35 + i * rowH;
    const base = r[0] === "pkv";
    if (base) rrect(s, 0.5, y - 0.04, 12.33, rowH - 0.02, "FDE68A");
    const url = "https://arxiv.org/abs/" + r[2];
    T(s, [
      { text: `[${n}]  `, options: { bold: true, color: base ? "B45309" : C.accent1 } },
      { text: (base ? "★ BASE PAPER  " : ""), options: { bold: true, color: "B45309" } },
      { text: `${r[1]} (${r[3]})`, options: { bold: base } },
    ], { x: 0.6, y, w: 7.9, h: rowH - 0.06, fontSize: base ? 10.5 : 12, valign: "middle" });
    T(s, [{ text: url, options: { hyperlink: { url, tooltip: r[1] }, color: base ? "B45309" : "0F766E", bold: base } }],
      { x: 8.55, y, w: 4.2, h: rowH - 0.06, fontSize: 12, valign: "middle", fontFace: "Consolas" });
  });
  return s;
}
refSlideLinked("References with links (1 of 3)", 0, 10);
refSlideLinked("References with links (2 of 3): highlighted = base paper", 10, 20);
{
  const s = refSlideLinked("References with links (3 of 3)", 20, 30);
  s.addText("Also cited, not on arXiv: Williams, Waterman, Patterson, Roofline, CACM 52(4), 2009  |  Little, L = λW, Operations Research 9(3), 1961  |  NVIDIA CUDA C++ Programming Guide.  Base paper PDF: Downloads\\Base_Paper_PersistentKV_arXiv_2606.26666.pdf",
    { isTextBox: true, x: 0.6, y: 6.45, w: 12.13, h: 0.55, margin: 0, fontSize: 11, color: C.accent6, valign: "top" });
}
