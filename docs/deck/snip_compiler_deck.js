// Body of the compiler-focused final deck. make_compiler_deck.py prepends the theme,
// helpers and REFS from build_deck.js (everything above its title slide).

const code = (s, text, x, y, w, h, fs = 13) => {
  rrect(s, x, y, w, h, HEX.ink);
  T(s, text, { x: x + 0.25, y: y + 0.18, w: w - 0.5, h: h - 0.36, fontSize: fs, fontFace: "Consolas", color: "E2E8F0" });
};

// =================================================================== 1. title
{
  pres.addSection({ title: "Opening" }); declared.add("Opening");
  const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Opening" });
  T(s, "COMPILER DESIGN  |  FINAL PRESENTATION", { x: 0.8, y: 0.8, w: 8, h: 0.4, fontSize: 14, bold: true, color: C.accent2, charSpacing: 3 });
  T(s, "KVForge", { x: 0.8, y: 1.5, w: 8, h: 1.1, fontSize: 60, bold: true, color: C.background1, fontFace: "Cambria" });
  T(s, "A compiler for GPU decode attention: the programmer leaves the hard choices as holes, and the compiler fills them", { x: 0.8, y: 2.7, w: 7.6, h: 1.3, fontSize: 22, color: C.background2 });
  T(s, [
    { text: "Aahav Yadav  -  24BKT0138", options: { breakLine: true } },
    { text: "Akshat Kapur  -  24BDS0318", options: { breakLine: true } },
    { text: "Rishab Jajodia  -  24BDS0268" },
  ], { x: 0.8, y: 4.6, w: 7, h: 1.1, fontSize: 18, color: C.background1, paraSpaceAfter: 6 });
  T(s, "Course: Compiler Design  |  VIT Vellore", { x: 0.8, y: 6.3, w: 7, h: 0.4, fontSize: 14, color: C.background2 });
  code(s, "decode layer(...) {\n  K: kvcache<n, d, ?, ?, ?>\n  O = decode_attn(Q, K, V,\n        splits = ?)\n}", 8.9, 1.6, 3.9, 2.0, 14);
  arrowR(s, 10.45, 3.75, 0.8, 0.5, "F59E0B");
  box(s, 8.9, 4.4, 3.9, 0.8, "0F766E", "kvf compiler", { fontSize: 18, bold: true });
  T(s, "holes in, verified GPU code out", { x: 8.9, y: 5.35, w: 3.9, h: 0.3, fontSize: 13, color: C.accent2, align: "center" });
  s.addNotes("One-line pitch: KVForge is a domain-specific compiler. The program describes one attention layer and leaves storage format, memory layout and work division as holes; the compiler fills them using a model of the GPU and emits CUDA.");
}

// =================================================================== 2. problem
{
  const s = slide("The problem", "Problem",
    "When a language model writes a reply, every new word requires reading the whole key-value (KV) cache: the stored keys and values of every earlier token. That read, not arithmetic, sets the speed. There are thousands of ways to perform it, and the best one depends on the model and the GPU. Backup numbers if asked: for Llama-3-8B at 32k tokens the cache is 4 GB per conversation; the GPU does about 4 operations per byte read, far below the ~47 it could sustain, so it waits on memory.");
  const cards = [
    ["1", "Every new word re-reads the whole cache", "The model stores keys and values for every earlier token (the KV cache). Each new word reads all of it once.", PAL.rose],
    ["2", "Thousands of ways to do that read", "How numbers are stored, how memory is arranged, how the work is split across the GPU: each choice changes the speed.", PAL.amber],
    ["3", "The best way is chosen by hand today", "Experts tune per GPU, or tools try hundreds of options on each machine. Change the model or the GPU and the work starts again.", PAL.slate],
  ];
  cards.forEach((c, i) => {
    const x = 0.6 + i * 4.1;
    rrect(s, x, 1.5, 3.93, 3.6, C.background2);
    badge(s, x + 0.3, 1.8, c[0], c[3]);
    T(s, c[1], { x: x + 0.3, y: 2.45, w: 3.4, h: 0.95, fontSize: 19, bold: true });
    T(s, c[2], { x: x + 0.3, y: 3.45, w: 3.4, h: 1.6, fontSize: 15, color: C.accent6 });
  });
  rrect(s, 0.6, 5.45, 12.13, 1.35, THEME.colors.dk1);
  T(s, "Our question", { x: 0.9, y: 5.6, w: 4, h: 0.35, fontSize: 14, bold: true, color: C.accent2 });
  T(s, "Can a compiler make this choice automatically, by predicting from a model of the GPU instead of trying every option?", { x: 0.9, y: 5.95, w: 11.5, h: 0.75, fontSize: 19, color: C.background1 });
}

// =================================================================== 3. idea
{
  const s = slide("The idea: a program with holes", "Idea",
    "Separate what to compute from how to compute it. The programmer writes the what: the attention operation and the shape of the model. Each how decision is written as a question mark. The compiler's job is to fill every question mark. This is the same separation Halide and TVM make for image processing and deep learning.");
  code(s, "target max_rel_err = 0.02     # accuracy budget\n\ndecode llama3(H: 32, H_kv: 8, d: 128,\n              n: 32768, batch: 1) {\n  Q: query<H, d, f32>\n  K: kvcache<n, d, ?, ?, ?>\n  V: kvcache<n, d, ?, ?, ?>\n  O = decode_attn(Q, K, V,\n        splits = ?, gqa_pack = ?)\n}", 0.6, 1.45, 6.2, 4.3, 14);
  T(s, "Each ? is a decision left to the compiler", { x: 7.2, y: 1.45, w: 5.5, h: 0.4, fontSize: 17, bold: true, color: C.accent1 });
  const rows = [
    ["Representation", "How each number is stored: 16-bit, or compressed to 8 or 4 bits", PAL.teal],
    ["Placement", "How the cache is arranged in memory", PAL.indigo],
    ["Partition", "How the work is divided across the GPU's cores", PAL.amber],
    ["Accuracy budget", "A constraint: compressed formats are allowed only if their error fits", PAL.rose],
  ];
  rows.forEach((r, i) => {
    const y = 2.0 + i * 0.95;
    rrect(s, 7.2, y, 5.53, 0.82, C.background2);
    rect(s, 7.2, y, 0.1, 0.82, r[2]);
    T(s, r[0], { x: 7.45, y: y + 0.08, w: 5.1, h: 0.3, fontSize: 15, bold: true });
    T(s, r[1], { x: 7.45, y: y + 0.4, w: 5.2, h: 0.38, fontSize: 12.5, color: C.accent6 });
  });
  rrect(s, 0.6, 6.05, 12.13, 0.8, "FDE68A");
  T(s, "The programmer says WHAT to compute. The compiler decides HOW.", { x: 0.9, y: 6.05, w: 11.6, h: 0.8, fontSize: 20, bold: true, valign: "middle" });
}

// =================================================================== 4. language
{
  const s = slide("The KVForge language", "Compiler",
    "A small domain-specific language with a grammar and type rules (docs/dsl.md in the repository). The point to make: these are typed declarations, and the hole is part of the type. A program with holes is a valid but incomplete program; compilation completes it.");
  const h = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.ink }, fontSize: 14 } });
  const c = (t, o = {}) => ({ text: t, options: Object.assign({ fontSize: 14, valign: "middle" }, o) });
  const m = (t) => c(t, { fontFace: "Consolas", bold: true });
  s.addTable([
    [h("Construct"), h("Meaning"), h("Compiler-course equivalent")],
    [m("decode name(H: 32, ...) { }"), c("One attention layer, with the model's shape as parameters"), c("A function definition")],
    [m("K: kvcache<n, d, f16, ...>"), c("A typed declaration of the cache"), c("A variable with a type")],
    [m("?"), c("A choice left open: a hole in the type or in an argument"), c("An unknown the compiler must infer")],
    [m("O = decode_attn(Q, K, V, ...)"), c("The operation, in single-assignment form"), c("A statement / an IR operation")],
    [m("target max_rel_err = 0.02"), c("A constraint the result must satisfy"), c("A compiler directive")],
  ], { x: 0.6, y: 1.45, w: 12.13, colW: [4.3, 4.6, 3.23], rowH: 0.62, border: { type: "solid", pt: 0.75, color: HEX.grid }, fontFace: "Calibri", color: HEX.ink });
  rrect(s, 0.6, 5.6, 12.13, 1.25, C.background2);
  T(s, "Write a value instead of ? and the choice is fixed: the compiler searches only what is left open. Leave out the budget line and only exact 16-bit storage is allowed.", { x: 0.9, y: 5.7, w: 11.6, h: 1.05, fontSize: 16, valign: "middle" });
}

// =================================================================== 5. architecture
{
  const s = slide("Compiler architecture", "Compiler",
    "Three parts, as in any compiler. Front end: textbook. Middle end: our contribution; the passes that decide how to run the operation. Back end: deliberately thin; it configures a kernel template and hands it to NVIDIA's nvcc, which does instruction selection and register allocation, the way many language front ends hand code to LLVM.");
  const groups = [
    ["FRONT END", "classic", ["Lexer", "Parser", "Semantic checks", "IR with holes"], PAL.slate, 0.6],
    ["MIDDLE END", "our contribution", ["Enumerate plans", "Cost model", "Accuracy gate", "IR rewrite"], PAL.teal, 4.75],
    ["BACK END", "thin, reuses nvcc", ["CUDA generation", "nvcc", "Check and time"], PAL.indigo, 8.9],
  ];
  groups.forEach((g) => {
    const x = g[4];
    rrect(s, x, 1.45, 3.83, 4.4, C.background2);
    T(s, g[0], { x: x + 0.25, y: 1.6, w: 3.4, h: 0.4, fontSize: 18, bold: true, color: g[3] });
    T(s, g[1], { x: x + 0.25, y: 2.0, w: 3.4, h: 0.3, fontSize: 13, color: C.accent6 });
    g[2].forEach((st, i) => box(s, x + 0.3, 2.5 + i * 0.8, 3.23, 0.62, g[3], st, { fontSize: 15, bold: true }));
  });
  arrowR(s, 4.47, 3.45, 0.25, 0.4, "94A3B8");
  arrowR(s, 8.62, 3.45, 0.25, 0.4, "94A3B8");
  T(s, ".kv program", { x: 0.6, y: 6.0, w: 3.8, h: 0.35, fontSize: 14, bold: true, align: "center" });
  T(s, "complete plan in the IR", { x: 4.75, y: 6.0, w: 3.83, h: 0.35, fontSize: 14, bold: true, align: "center" });
  T(s, "verified GPU kernel", { x: 8.9, y: 6.0, w: 3.83, h: 0.35, fontSize: 14, bold: true, align: "center" });
  T(s, "Each part maps to a course topic: lexical and syntax analysis, semantic analysis, intermediate code, optimisation, code generation.", { x: 0.6, y: 6.45, w: 12.13, h: 0.4, fontSize: 13, color: C.accent6, align: "center" });
}

// =================================================================== 6. front end
{
  const s = slide("Front end: from text to an IR with holes", "Compiler",
    "Lexer cuts the text into tokens, including the hole token. Parser builds the syntax tree. Semantic analysis rejects programs that are grammatical but meaningless; these rejections are covered by the automatic tests (19 tests, all passing). The IR is in single-assignment style and its types can contain holes.");
  const steps = [["Lexer", "characters to tokens: kvcache, <, n, ?, ..."], ["Parser", "tokens to a syntax tree; grammar errors with line numbers"], ["Semantic checks", "is the program meaningful? (examples on the right)"], ["IR", "one internal form; the holes are part of the types"]];
  steps.forEach((st, i) => {
    const y = 1.45 + i * 0.85;
    badge(s, 0.6, y + 0.1, i + 1, PAL.slate);
    T(s, st[0], { x: 1.2, y, w: 5.2, h: 0.35, fontSize: 16, bold: true });
    T(s, st[1], { x: 1.2, y: y + 0.36, w: 5.4, h: 0.4, fontSize: 13, color: C.accent6 });
  });
  code(s, "%K = kvf.kvcache : kvcache<32768x128x?, ?/?>\n%O = kvf.decode_attn %Q, %K, %V", 0.6, 5.0, 6.2, 1.0, 12.5);
  T(s, "The IR after the front end: the cache's type still has holes", { x: 0.6, y: 6.1, w: 6.2, h: 0.35, fontSize: 12, color: C.accent6 });
  rrect(s, 7.1, 1.45, 5.63, 5.0, C.background2);
  T(s, "Programs the compiler rejects", { x: 7.35, y: 1.6, w: 5.2, h: 0.4, fontSize: 17, bold: true, color: C.accent4 });
  const rej = ["Query heads that do not divide evenly over KV heads", "A head size the kernels do not support", "A compression group that does not divide the head size", "K and V leaving different things open", "A misspelt setting (bw_peek_gbs): an error, not silently ignored", "Using a cache that was never declared"];
  rej.forEach((r, i) => {
    T(s, "✕", { x: 7.35, y: 2.15 + i * 0.68, w: 0.35, h: 0.35, fontSize: 16, bold: true, color: C.accent4 });
    T(s, r, { x: 7.75, y: 2.15 + i * 0.68, w: 4.8, h: 0.6, fontSize: 13.5 });
  });
}

// =================================================================== 7. middle end
{
  const s = slide("Middle end: optimisation passes on the IR", "Compiler",
    "Four passes. Enumerate lists every way to fill the holes (for the Llama-3 example, 2,688 complete plans). The cost model predicts each plan's run time without running it. The accuracy gate removes plans whose storage format is too inaccurate for the budget. The rewrite pass replaces the generic operation with a planned one and fills in the types.");
  const p = [["Enumerate", "every way to fill the holes", PAL.indigo], ["Cost model", "predict each plan's time, without running it", PAL.teal], ["Accuracy gate", "drop formats whose error exceeds the budget", PAL.rose], ["Rewrite", "fill the holes in the IR with the winner", PAL.green]];
  p.forEach((x, i) => {
    const X = 0.6 + i * 3.1;
    box(s, X, 1.45, 2.85, 0.75, x[2], x[0], { fontSize: 18, bold: true });
    T(s, x[1], { x: X, y: 2.3, w: 2.85, h: 0.65, fontSize: 13.5, align: "center", color: C.accent6 });
    if (i < 3) arrowR(s, X + 2.88, 1.62, 0.2, 0.4, "94A3B8");
  });
  T(s, "Before the passes", { x: 0.6, y: 3.2, w: 6, h: 0.35, fontSize: 15, bold: true });
  code(s, "%K = kvf.kvcache : kvcache<32768x128x?, ?/?>\n%O = kvf.decode_attn %Q, %K, %V", 0.6, 3.6, 12.13, 0.95, 13);
  T(s, "After the passes", { x: 0.6, y: 4.75, w: 6, h: 0.35, fontSize: 15, bold: true });
  code(s, "%K = kvf.kvcache : kvcache<32768x128xint8:128, head_major/contiguous>\n%O = kvf.decode_attn_split %Q, %K, %V {format = int8:128, splits = 32, gqa_pack = true, warps = 8}", 0.6, 5.15, 12.13, 1.0, 13);
  T(s, "Like a C compiler lowering a generic operation to a specific one once the types are known.", { x: 0.6, y: 6.3, w: 12.13, h: 0.4, fontSize: 13, color: C.accent6 });
}

// =================================================================== 8. cost model
{
  const s = slide("The cost model is the optimiser's guide", "Compiler",
    "Every optimising compiler needs a way to judge which version is better. GCC and Clang mostly use rules of thumb. KVForge uses a model of the machine instead: it estimates bytes moved, how fast they can arrive given the GPU's measured bandwidth and latency and how many blocks fit (from the kernels' register use), the arithmetic, and fixed overheads such as kernel launch. A few constants (ten) were fitted once from measurements on one GPU and then frozen. If asked for detail: Little's law, bytes in flight divided by loaded latency, gives the bandwidth reached.");
  rrect(s, 0.6, 1.45, 5.9, 2.0, C.background2);
  T(s, "A C compiler asks", { x: 0.85, y: 1.6, w: 5.4, h: 0.35, fontSize: 15, bold: true, color: C.accent6 });
  T(s, "\"Should I unroll this loop? Inline this call?\"\nand answers with rules of thumb.", { x: 0.85, y: 2.0, w: 5.4, h: 1.3, fontSize: 16 });
  rrect(s, 6.83, 1.45, 5.9, 2.0, C.background2);
  T(s, "KVForge asks", { x: 7.08, y: 1.6, w: 5.4, h: 0.35, fontSize: 15, bold: true, color: C.accent1 });
  T(s, "\"Which of these plans runs fastest on this GPU?\"\nand answers with a model of the machine.", { x: 7.08, y: 2.0, w: 5.4, h: 1.3, fontSize: 16 });
  T(s, "What the model uses", { x: 0.6, y: 3.7, w: 6, h: 0.35, fontSize: 15, bold: true });
  const ins = [["Measured machine description", "a probe measures the GPU once: bandwidth, latency, core count", PAL.indigo], ["Kernel resource table", "registers each kernel uses, read from the compiled code", PAL.indigo], ["A few fitted constants", "fitted once on one GPU, then frozen", PAL.amber]];
  ins.forEach((x, i) => {
    const y = 4.1 + i * 0.9;
    rrect(s, 0.6, y, 5.9, 0.78, C.background2);
    rect(s, 0.6, y, 0.1, 0.78, x[2]);
    T(s, x[0], { x: 0.85, y: y + 0.06, w: 5.5, h: 0.32, fontSize: 14, bold: true });
    T(s, x[1], { x: 0.85, y: y + 0.39, w: 5.5, h: 0.35, fontSize: 12, color: C.accent6 });
  });
  T(s, "What it estimates for each plan", { x: 6.83, y: 3.7, w: 6, h: 0.35, fontSize: 15, bold: true });
  ["Bytes to move", "How fast they can arrive", "Arithmetic to do", "Fixed overheads"].forEach((t, i) => {
    box(s, 6.83, 4.1 + i * 0.66, 4.2, 0.55, PAL.teal, t, { fontSize: 14, bold: true, align: "left" });
  });
  arrowR(s, 11.13, 4.95, 0.35, 0.45, "94A3B8");
  box(s, 11.55, 4.45, 1.18, 1.45, PAL.amber, "predicted time", { fontSize: 13, bold: true, color: HEX.ink });
}

// =================================================================== 9. back end
{
  const s = slide("Back end: code generation and verification", "Compiler",
    "KVForge does not emit GPU instructions itself. One CUDA kernel template has compile-time switches for format, layout, packing and unrolling; code generation emits a short file that sets them. nvcc then specialises the template (removing unused code, folding constants) and does instruction selection and register allocation. Every generated kernel is run on random data and compared with a high-precision reference; in all our runs none failed.");
  T(s, "Generated code for the chosen plan", { x: 0.6, y: 1.45, w: 7, h: 0.35, fontSize: 15, bold: true });
  code(s, "a.splits = 32;  a.warps = 8;\nreturn kvf::launch<FMT_INT8, 128, 4, 4, ORD_HEAD, false>(a, st);", 0.6, 1.85, 12.13, 1.05, 14);
  const st = [["Configure", "Code generation sets the switches of one kernel template from the IR", PAL.teal], ["Specialise", "nvcc compiles it: unused code removed, constants folded, registers allocated", PAL.indigo], ["Verify", "the kernel runs on test data and is compared with a reference answer", PAL.green]];
  st.forEach((x, i) => {
    const X = 0.6 + i * 4.1;
    rrect(s, X, 3.2, 3.93, 2.2, C.background2);
    badge(s, X + 0.3, 3.45, i + 1, x[2]);
    T(s, x[0], { x: X + 0.9, y: 3.45, w: 2.8, h: 0.44, fontSize: 19, bold: true, valign: "middle" });
    T(s, x[1], { x: X + 0.3, y: 4.1, w: 3.4, h: 1.2, fontSize: 14.5 });
  });
  rrect(s, 0.6, 5.7, 12.13, 1.15, "FDE68A");
  T(s, "nvcc is our back end, the way LLVM is the back end of many language front ends. Our part is deciding what to generate.", { x: 0.9, y: 5.7, w: 11.6, h: 1.15, fontSize: 17, bold: true, valign: "middle" });
}

// =================================================================== 10. why a compiler
{
  const s = slide("Why this is a compiler", "Compiler",
    "The direct answer to 'is this really a compiler?': yes, a domain-specific one. It has a source language with grammar and types, a front end, an IR transformed by passes, an optimisation pass guided by a cost model, and code generation. It compiles one kind of operation, not general programs, and it relies on nvcc for machine code. Halide (image processing) and TVM (deep learning) are well-known compilers built the same way.");
  const h = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.ink }, fontSize: 15 } });
  const c = (t, o = {}) => ({ text: t, options: Object.assign({ fontSize: 14.5, valign: "middle" }, o) });
  s.addTable([
    [h("A C compiler (GCC, Clang)"), h("KVForge")],
    [c("Source language with grammar and types", { bold: true }), c(".kv language: typed declarations, holes, constraints")],
    [c("Lexer, parser, semantic analysis", { bold: true }), c("The same three stages, with tests for rejected programs")],
    [c("Intermediate representation", { bold: true }), c("Single-assignment IR whose types can contain holes")],
    [c("Optimisation passes with heuristics", { bold: true }), c("Search, cost-model, accuracy-gate and rewrite passes")],
    [c("Code generation", { bold: true }), c("CUDA generation; nvcc produces machine code")],
    [c("Output: an executable", { bold: true }), c("Output: a GPU kernel, checked against a reference")],
  ], { x: 0.6, y: 1.45, w: 12.13, colW: [5.0, 7.13], rowH: 0.58, border: { type: "solid", pt: 0.75, color: HEX.grid }, fontFace: "Calibri", color: HEX.ink });
  rrect(s, 0.6, 5.75, 12.13, 1.1, THEME.colors.dk1);
  T(s, "Same family as Halide and TVM: separate what to compute from how to run it, and let the compiler choose the how.", { x: 0.9, y: 5.75, w: 11.6, h: 1.1, fontSize: 18, bold: true, color: C.background1, valign: "middle" });
}

// =================================================================== 11. inputs and outputs
{
  const s = slide("What goes in, what comes out", "Compiler",
    "Three input sources. The program changes per model: its five shape numbers come from the model's published configuration. The machine description and register table change per GPU and are collected by tools. The constants were fitted once and never changed. The compiler itself needs no GPU; only building and running the generated kernel does.");
  const ins = [["The program", "written per model: the model's shape, holes, an accuracy budget", PAL.teal], ["Machine description", "measured once per GPU by a probe tool", PAL.indigo], ["Fitted constants", "fitted once, then frozen", PAL.amber]];
  ins.forEach((x, i) => {
    const y = 1.5 + i * 1.5;
    box(s, 0.6, y, 3.6, 1.25, x[2], x[0], { fontSize: 17, bold: true, color: x[2] === PAL.amber ? HEX.ink : C.background1 });
    T(s, x[1], { x: 0.6, y: y + 1.27, w: 3.6, h: 0.25, fontSize: 11, color: C.accent6, align: "center" });
  });
  arrowR(s, 4.4, 3.4, 0.6, 0.6, "94A3B8");
  box(s, 5.2, 2.3, 2.9, 2.8, HEX.ink, "kvf\ncompiler\n\n(no GPU needed)", { fontSize: 20, bold: true });
  arrowR(s, 8.3, 3.4, 0.6, 0.6, "94A3B8");
  const outs = ["The reasoning: why this plan, what was rejected", "The IR before and after planning", "Generated CUDA code", "A kernel that is built, checked and timed"];
  outs.forEach((t, i) => box(s, 9.1, 1.5 + i * 1.1, 3.63, 0.9, PAL.green, t, { fontSize: 14 }));
}

// =================================================================== 12. demo
{
  const s = slide("Live demo: one layer of Llama-3-8B, three programs", "Demo",
    "Run: powershell -ExecutionPolicy Bypass -File demo\\run_demo.ps1 -Pause. Any other model: demo\\try_model.ps1 asks for it. Backup detail: measured 845, 430 and 273 microseconds; error versus exact attention 0.03% for 16-bit and 0.84% for the 8-bit format. If the laptop fails, demo\\demo_output_recorded.txt has a recorded run.");
  const progs = [
    ["1_baseline.kv", "everything fixed by hand", "K: kvcache<n, d, f16,\n   token_major, contiguous>\nsplits = 1", PAL.slate, "1×", "the starting point"],
    ["2_lossless.kv", "compiler chooses, exact storage only", "K: kvcache<n, d, ?, ?, ?>\nsplits = ?", PAL.teal, "about 2×", "same accuracy"],
    ["3_budget.kv", "compiler chooses, within an accuracy budget", "target max_rel_err = 0.02\nK: kvcache<n, d, ?, ?, ?>", PAL.indigo, "about 3×", "under 1% error"],
  ];
  progs.forEach((p, i) => {
    const x = 0.6 + i * 4.1;
    rrect(s, x, 1.45, 3.93, 4.25, C.background2);
    rect(s, x, 1.45, 3.93, 0.1, p[3]);
    T(s, p[0], { x: x + 0.25, y: 1.7, w: 3.5, h: 0.4, fontSize: 17, bold: true, fontFace: "Consolas" });
    T(s, p[1], { x: x + 0.25, y: 2.1, w: 3.5, h: 0.6, fontSize: 13, color: C.accent6 });
    code(s, p[2], x + 0.25, 2.75, 3.43, 1.15, 11);
    T(s, p[4], { x: x + 0.25, y: 4.1, w: 3.43, h: 0.75, fontSize: 36, bold: true, color: p[3], align: "center", fontFace: "Cambria" });
    T(s, "faster, " + p[5] + "  ·  check PASS", { x: x + 0.25, y: 4.9, w: 3.43, h: 0.4, fontSize: 13, align: "center" });
  });
  rrect(s, 0.6, 5.95, 12.13, 0.9, "FDE68A");
  T(s, "Only question marks and one budget line differ. Every generated kernel is compiled, run on the GPU and checked against a reference.", { x: 0.9, y: 5.95, w: 11.6, h: 0.9, fontSize: 16, bold: true, valign: "middle" });
}

// =================================================================== 13. base paper
{
  const s = slide("Base paper: FlashInfer (MLSys 2025)", "Context",
    "Our base paper: FlashInfer, Ye et al., Proceedings of the 8th MLSys Conference, 2025 (arXiv 2501.01005; University of Washington, NVIDIA, CMU and others). Peer reviewed, read in full. It is the attention engine inside vLLM, SGLang and MLC-Engine. It is itself code-generation based: attention variants and KV-cache layouts are specified and compiled just in time from templates. For decode it uses split-K work splitting and head-group fusion for GQA, the same two levers that matter most in our measurements. It picks tile sizes with heuristics based on hardware resources and workload, and notes that the best tile size differs by GPU architecture. Backup numbers: evaluated on A100 and H100 in fp16; 29 to 69 percent lower inter-token latency than a Triton backend in SGLang; it also supports an fp8 KV cache. On our GPU our compiler's pick takes 1.06 times FlashInfer's time on average: close, not faster. Closest related work: PersistentKV (arXiv 2606.26666, 2026 preprint, not peer reviewed) uses a small calibrated cost model on one GPU, fp16 only.");
  const cols = [
    ["What it is", ["The attention engine used inside vLLM, SGLang and MLC", "Peer reviewed: MLSys 2025 (UW, NVIDIA, CMU)", "Builds kernels from templates by just-in-time compilation"], PAL.slate],
    ["What it shows us", ["Decode needs work splitting and grouping of query heads: both are holes in our language", "The best settings differ by GPU and workload", "It chooses them with hand-written rules"], PAL.teal],
    ["What we add", ["A cost model chooses, instead of hand-written rules", "Storage format chosen too, under an accuracy budget", "A language with holes, an IR and passes", "Tested on a second GPU without re-tuning"], PAL.indigo],
  ];
  cols.forEach((c, i) => {
    const x = 0.6 + i * 4.1;
    rrect(s, x, 1.45, 3.93, 4.45, C.background2);
    box(s, x + 0.25, 1.65, 3.43, 0.6, c[2], c[0], { fontSize: 17, bold: true });
    c[1].forEach((t, j) => T(s, "•  " + t, { x: x + 0.3, y: 2.45 + j * 0.86, w: 3.4, h: 0.84, fontSize: 14 }));
  });
  rrect(s, 0.6, 6.05, 12.13, 0.85, THEME.colors.dk1);
  T(s, [
    { text: "We are close to FlashInfer in speed, not ahead; our contribution is choosing automatically.", options: { bold: true, breakLine: true } },
    { text: "Closest related work: PersistentKV (arXiv preprint 2026), a small calibrated cost model on one GPU.", options: { color: "CBD5E1" } },
  ], { x: 0.9, y: 6.08, w: 11.6, h: 0.8, fontSize: 14, color: C.background1, valign: "middle" });
}

// =================================================================== 14. findings
{
  const s = slide("What we found", "Results",
    "Stated qualitatively on purpose. Backup numbers if asked: 2 to 3 times over a straightforward kernel (1.9x exact, 3.0x with 8-bit, averaged over 10 shapes; demo 1.96x and 3.09x); our pick takes 1.06 times FlashInfer's time on average (6% slower); on the second GPU (RTX 4060) with constants frozen, rank correlation 0.886; 44,224 generated-kernel runs checked against a reference, none failed; plans reading identical bytes differed by up to 6.4 times.");
  const f = [
    ["The choice matters", "Plans that move exactly the same data can differ several times in speed, so the choice is worth a compiler.", PAL.amber],
    ["The compiler chooses well", "Its choice is about two to three times faster than a straightforward kernel.", PAL.teal],
    ["Close to expert code, not ahead of it", "It comes close to FlashInfer, the leading hand-tuned library, but does not beat it.", PAL.slate],
    ["It carries over to another GPU", "Fitted on one GPU, it still ranks choices well on a GPU of a different generation, with nothing re-tuned.", PAL.indigo],
    ["The code is correct", "Every kernel it generated was checked against a reference answer; none failed.", PAL.green],
  ];
  f.forEach((x, i) => {
    const y = 1.45 + i * 1.07;
    rrect(s, 0.6, y, 12.13, 0.92, C.background2);
    rect(s, 0.6, y, 0.12, 0.92, x[2]);
    T(s, x[0], { x: 0.95, y: y + 0.1, w: 4.1, h: 0.72, fontSize: 18, bold: true, valign: "middle" });
    T(s, x[1], { x: 5.1, y: y + 0.1, w: 7.4, h: 0.72, fontSize: 15, valign: "middle" });
  });
}

// =================================================================== 15. limits
{
  const s = slide("Limits, stated plainly", "Results",
    "Say these before anyone asks. Backup: the weak kernel is the one that serves 8 query heads per KV head; it needs too many registers. The Qwen2.5-7B run at 64 users had the ranking right but times predicted 2.5 to 3 times too low.");
  const l = [
    ["Not faster than the best library", "The claim is choosing well without per-GPU tuning, not a faster kernel."],
    ["Two laptop GPUs only", "Two generations tested; server GPUs not yet."],
    ["Accuracy measured on test data", "The error of compressed formats was measured on random data, not on a real model's text."],
    ["One weak kernel", "One kernel variant is slow and causes our one clear mis-prediction."],
    ["Far from tested shapes, times are rougher", "The ranking held in our tests, but predicted times can be well off."],
  ];
  l.forEach((x, i) => {
    const y = 1.45 + i * 1.07;
    rrect(s, 0.6, y, 12.13, 0.92, C.background2);
    s.addText("!", { shape: pres.ShapeType.ellipse, x: 0.85, y: y + 0.24, w: 0.44, h: 0.44, fill: { color: "BE123C" }, line: { type: "none" }, align: "center", valign: "middle", fontSize: 16, bold: true, color: "FFFFFF" });
    T(s, x[0], { x: 1.5, y: y + 0.1, w: 4.4, h: 0.72, fontSize: 17, bold: true, valign: "middle" });
    T(s, x[1], { x: 6.0, y: y + 0.1, w: 6.5, h: 0.72, fontSize: 15, valign: "middle" });
  });
}

// =================================================================== 16. summary
{
  const s = slide("Summary", "Results",
    "Three contributions, all compiler-shaped. Close by offering the live demo or a model of the examiner's choice with try_model.ps1.");
  const c = [
    ["1", "A language with holes", "The programmer describes one attention layer and leaves storage, layout and work division to the compiler, with an accuracy budget as a constraint."],
    ["2", "A cost-model-driven optimiser", "Passes on the IR enumerate, predict, filter and rewrite, guided by a model of the measured machine instead of trial runs."],
    ["3", "Verified code generation", "The chosen plan becomes CUDA, compiled by nvcc and checked against a reference; tested on two GPU generations."],
  ];
  c.forEach((x, i) => {
    const y = 1.5 + i * 1.55;
    rrect(s, 0.6, y, 12.13, 1.4, C.background2);
    badge(s, 0.9, y + 0.48, x[0], PAL.teal);
    T(s, x[1], { x: 1.65, y: y + 0.15, w: 3.6, h: 1.1, fontSize: 19, bold: true, valign: "middle" });
    T(s, x[2], { x: 5.3, y: y + 0.1, w: 7.2, h: 1.2, fontSize: 15, valign: "middle" });
  });
  rrect(s, 0.6, 6.2, 12.13, 0.7, THEME.colors.dk1);
  T(s, "Want to try a model? demo\\try_model.ps1 compiles, runs and checks it live.", { x: 0.9, y: 6.2, w: 11.6, h: 0.7, fontSize: 16, bold: true, color: C.background1, valign: "middle" });
}

// =================================================================== references, linked, base paper highlighted
function refSlideLinked(title, from, to) {
  const s = slide(title, "References", "Every arXiv ID was checked against the arXiv API. Each line is a clickable link. The base paper, FlashInfer (MLSys 2025), and the closest related work, PersistentKV (arXiv preprint), were read in full; the others from abstracts.");
  const rowH = 0.5;
  REFS.slice(from, to).forEach((r, i) => {
    const n = from + i + 1;
    const y = 1.35 + i * rowH;
    const base = r[0] === "flashinfer";
    const related = r[0] === "pkv";
    if (base) rrect(s, 0.5, y - 0.04, 12.33, rowH - 0.02, "FDE68A");
    if (related) rrect(s, 0.5, y - 0.04, 12.33, rowH - 0.02, "E2E8F0");
    const url = "https://arxiv.org/abs/" + r[2];
    T(s, [
      { text: `[${n}]  `, options: { bold: true, color: base ? "B45309" : C.accent1 } },
      { text: (base ? "★ BASE PAPER (MLSys 2025)  " : related ? "CLOSEST RELATED  " : ""), options: { bold: true, color: base ? "B45309" : "475569" } },
      { text: `${r[1]} (${r[3]})`, options: { bold: base } },
    ], { x: 0.6, y, w: 7.9, h: rowH - 0.06, fontSize: base || related ? 10.5 : 12, valign: "middle" });
    T(s, [{ text: url, options: { hyperlink: { url, tooltip: r[1] }, color: base ? "B45309" : "0F766E", bold: base } }],
      { x: 8.55, y, w: 4.2, h: rowH - 0.06, fontSize: 12, valign: "middle", fontFace: "Consolas" });
  });
  return s;
}
refSlideLinked("References (1 of 3)", 0, 10);
refSlideLinked("References (2 of 3): highlighted = base paper", 10, 20);
{
  const s = refSlideLinked("References (3 of 3)", 20, 30);
  s.addText("Also cited: Williams, Waterman, Patterson, Roofline, CACM 2009  |  Little, L = λW, Operations Research 1961  |  NVIDIA CUDA C++ Programming Guide.  Base paper PDF: Downloads\\Base_Paper_FlashInfer_arXiv_2501.01005.pdf",
    { isTextBox: true, x: 0.6, y: 6.45, w: 12.13, h: 0.55, margin: 0, fontSize: 11, color: C.accent6, valign: "top" });
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
