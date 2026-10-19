# KVForge

A bandwidth-model-driven compiler for **GPU decode-phase attention**.

Decode generates one token at a time. Every step sends one query vector per head
through the whole KV cache; each cached byte is read once and used once, so the
operator's *reuse factor is 1*. A scheduler that ranks schedules by how much data
they reuse sees every schedule as equal. What still differs is

| Axis | Choice | What it changes |
| --- | --- | --- |
| Representation | `f16`, `int8:G`, `int4:G` | bytes per cached element |
| Placement | `head_major` / `token_major`, `contiguous` / `paged:B` | how many fetched bytes are useful |
| Partition | split-KV count, GQA packing, warps, unroll | how many SMs stay busy, and bytes in flight |

KVForge enumerates format x layout x partition, scores every candidate with an
**analytic bandwidth model** built from measured machine parameters, picks the
cheapest plan that passes an accuracy budget, and emits a specialised CUDA kernel.

## Pipeline

```
.kv spec -> lexer -> parser -> AST -> semantic analysis
         -> SSA module: kvf.decode_attn over a typed kvcache
         -> plan enumeration (format x layout x partition)
         -> cost model, ranked; accuracy gate
         -> rewrite to kvf.decode_attn_split with the chosen plan
         -> CUDA source generation (template instantiation)  -> nvcc
         -> report.txt, plans.csv, ir.txt, decode_<name>.cu, plan_info.h
```

| Stage | Where |
| --- | --- |
| Lexer, parser | `src/lexer.cpp`, `src/parser.cpp` |
| Semantic analysis, IR | `include/kvf/ir.h`, `src/ir.cpp` |
| GPU machine model | `include/kvf/machine.h`, `src/machine.cpp` |
| Formats, layouts | `src/format.cpp`, `src/layout.cpp` |
| Plan enumeration | `src/plan.cpp` |
| **Cost model** | `src/cost.cpp` |
| Accuracy gate, plan selection | `src/passes.cpp` |
| CUDA code generation | `src/codegen.cpp` |
| Model fit and evaluation | `src/fit.cpp` |
| Kernel templates | `runtime/kvf_kernels.cuh` |
| Machine probe | `bench/bw_probe.cu` |
| Sweep harness (ground truth) | `bench/sweep.cu` |

## Build

The compiler is plain C++20. The CUDA side needs the CUDA Toolkit and, on
Windows, the MSVC C++ build tools (`nvcc` uses `cl.exe` as its host compiler).

```powershell
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build
powershell -File tests\smoke.ps1                 # compiler tests, no GPU needed

powershell -File tools\build_cuda.ps1 -Targets probe
build\cuda\bw_probe.exe --name my-gpu --out machines\my-gpu.gpu
```

`tools\build_cuda.ps1` builds one fat binary for `sm_89` (Ada) and `sm_120`
(Blackwell), so the same `.exe` runs on a machine with no CUDA toolkit.

## Use

```powershell
# measure this GPU, then plan against it
build\kvf machine machines\my-gpu.gpu
build\kvf plan examples\llama3_8b_gqa_32k.kv --machine machines\my-gpu.gpu --out out\llama3

# build and run the kernel the compiler generated, checked against a reference
powershell -File tools\build_plan.ps1 -Dir out\llama3
```

## The cost model

```
T = max( Bytes / BW_eff , FLOPs / F_eff ) * imbalance + T_merge + T_page + T_launch
BW_eff = eta(layout) * min( BW_peak , active_SMs * min( BW_sm , bytes_in_flight / latency ) )
```

* `Bytes` counts the KV payload at the *effective* element size
  (`bits + 32/G` for a lossy format) plus metadata, query/output and partials.
* `bytes_in_flight / latency` is Little's law: one SM cannot saturate DRAM.
* `eta` is the run-length efficiency of the layout: a block that reads long
  contiguous runs scores 1, one that jumps every row scores less.
* `T_merge` is the split-KV log-sum-exp recombination; it is the only term that
  grows with the split count, which is what creates an optimum.

Machine parameters are measured by `bw_probe` on each GPU. The few remaining
shape-of-the-curve constants live in `model/*.cal`, are fitted once on one GPU
with `kvf calibrate`, and are then frozen: `kvf evaluate` checks them against a
second GPU's measurements with no refit.

See [docs/dsl.md](docs/dsl.md) for the specification language.
