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

