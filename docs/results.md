# Results on the RTX 5060 Laptop

All numbers are from `results/` and regenerate with the commands at the end.
Machine: RTX 5060 Laptop GPU, compute capability 12.0, 26 SMs, 8.5 GB, on AC power.

## Machine, as measured by `bw_probe`

| Parameter | Value |
| --- | --- |
| DRAM read bandwidth, all SMs | 341 GB/s |
| One SM | 79 GB/s |
| DRAM latency, idle | 148 ns |
| L2 bandwidth, size | 1,581 GB/s, 32 MB |
| FP32 throughput | 16.0 TFLOP/s (ridge 47 FLOP/byte) |
| Sector size | 32 B (stride test) |
| Empty-kernel launch | 20.8 us |

## Hypothesis H1: do plans that move the same bytes differ?

Yes. Over the 20,928-plan sweep (10 shapes, none failed verification), the best
and worst fp16 plan differ by **1.8x to 6.4x** depending on the shape. The large
spreads are batch-1 grouped-query shapes, where few independent blocks make the
split count, GQA packing and bytes in flight decide how many SMs stay busy.

## Which axes matter

Best time given one axis value, over best time overall, median over shapes:

| Axis | Wrong value costs |
| --- | --- |
| Splits | up to 58% (splits = 1) |
| GQA packing | 40% (off) |
| Format | fp16 is 1.8x slower than the best lossy format |
| Unroll | 11% |
| Layout | up to 8% |
| Warps | about 0 |

Placement is nearly flat for fp16 on this GPU: a fp16 row is 256 B, a whole
number of memory sectors, so layout changes cost little.

## Model quality (constants fitted on 7 shapes, scored on 3 held out)

| Metric | Fit | Held-out |
| --- | --- | --- |
| MAPE, all formats | 17.4% | 15.2% |
| MAPE, fp16 only | 26.4% | 25.1% |
| Spearman rho, all | 0.88 | 0.88 |
| Kendall tau, all | 0.71 | 0.70 |
| Regret, fp16 only | 8.9% | 15.3% |
| Regret, int8 allowed | 4.0% | 1.9% |
| Regret, all formats | 10.1% | 13.9% |

Regret is how much slower the model's pick is than the best plan in the sweep.

## The compiler's pick against a naive baseline

Baseline: fp16, token-major, contiguous, no splitting, no GQA packing, 4 warps,
unroll 2. This is a naive first kernel in our own family, **not a tuned library**.

| Eligible formats | Geomean speedup | Mean regret (10 shapes) | Best shape |
| --- | --- | --- | --- |
| lossless (fp16) | 1.93x | 11.4% | 3.7x |
| int8 allowed (error <= 0.02) | 3.00x | 5.8% | 6.2x |
| all formats | 3.64x | 11.2% | 7.0x |

Measured accuracy: int8 relative error 0.8%, int4 11 to 14%, fp16 0.03%
(unit-variance random data; real caches have outliers).

## Against FlashInfer and PyTorch SDPA (fp16, same GPU, same timer)

Run in WSL2 (`bench/wsl/compare.py`): every method in one process, on the same K and V,
timed with CUDA events and an L2 flush before every repetition, every output checked
against an fp32 reference. KVForge kernels were compiled on Windows (`build/cubin`) and
launched through the driver API, so they are the kernels the sweep timed. FlashInfer 0.7.1
used its pre-built batch decode kernel (paged cache, page size 16); its single-request
kernel needs a CUDA compiler that WSL does not have. Only fp16 is compared.

| Method, relative to FlashInfer's time | Geomean | Range |
| --- | --- | --- |
| KVForge, the compiler's pick | 1.06x | 0.94x to 1.33x |
| KVForge, best contiguous plan in the sweep | 1.04x | 0.93x to 1.31x |
| PyTorch SDPA, best backend | 1.02x | 0.96x to 1.08x |
| Naive baseline | 2.12x | 1.08x to 3.85x |

* The compiler's pick is **6% slower than FlashInfer on average**, faster on one shape
  (0.94x), and 33% slower on the group-size-8 shape (H64/8, n=8192). The best plan in the
  sweep is also 31% slower there, so the gap is the kernel, not the model's choice.
* Likely cause (not proven): the 8-head-pack kernel needs 201 to 248 registers per thread, so
  only one 8-warp block fits per SM (8 of 48 warp slots).
* At large contexts every method sits at the measured 341 GB/s limit, so the differences
  appear on the smaller shapes.
* Reproduce: `compare_plans.py`, build the cubins, then `bench/wsl/compare.py` in WSL, then
  `tools/compare_summary.py`. WSL setup: `bench/wsl/setup_env.sh`, `install_flashinfer.sh`,
  `install_jit_cache.sh`.

## Tuning effort: how much measuring does the model save?

Brute force times every plan to find the best one. The middle path is to time only the
model's top-k plans and keep the fastest measured one. The control is k plans picked at
random (exact expectation, no sampling). Regret is as above; k = 1 is the compiler's pick.
Script: `tools/tuning_effort.py`, output in `results/tuning_effort_rtx5060.txt` and
`results/tuning_effort_rtx4060.txt`.

Mean regret on the 3 held-out shapes of the RTX 5060 (192 to 2,304 plans per shape):

| Plans timed | fp16 only: model / random | int8 allowed: model / random | All formats: model / random |
| --- | --- | --- | --- |
| 1 (compiler's pick) | 15.3% / 34.2% | 1.9% / 74.8% | 13.9% / 107% |
| 3 | 5.1% / 11.7% | 0.5% / 31.0% | 8.3% / 49.6% |
| 5 | 2.6% / 7.8% | 0.5% / 21.0% | 5.2% / 36.5% |
| 10 | 2.6% / 4.9% | 0.5% / 12.6% | 0.4% / 25.2% |

* Timing the model's top 5 (0.3% to 1.7% of the plans) gets within 0.5% to 5.2% of the best
  plan on average; 5 random plans are 7.8% to 36.5% off. The model's advantage over random
  is largest when lossy formats are in the search, because most of those plans are slow.
* On the RTX 4060 (frozen constants, every shape unseen), top 1 beats random 1 in every
  class (6.6% against 24.2%; 11.8% against 68.6%; 16.1% against 109%), and with all formats
  the model stays ahead at every k up to 20. **Negative result:** for fp16 on the 4060 a
  random 3 to 20 plans does as well as or better than the model's top 3 to 20 (for example
  3.3% against 2.4% at k = 5), because many fp16 plans are near the best and the model's errors on
  one or two shapes are systematic, so a longer shortlist does not fix them.
* Cost of brute force on this setup: the full 20,928-plan sweep took 8 min 29 s on the
  RTX 5060 (about 24 ms per plan, about 51 s per shape, kernels precompiled into one
  sweep binary). `kvf plan` scores all 2,688 plans of the Llama-3 shape in about 0.1 s.
  Brute force is affordable for one shape; the model's value is that it answers instantly
  for any shape (n and batch change at every decode step in serving) and on another GPU
  without re-measuring.

## Known limits

* Some split counts (16 and 32 on the 32k shape) run slower than both smaller and
  larger ones. The model does not capture this; memory-channel conflicts are the
  suspect, and are not modelled.
* The baseline above is naive; the comparison with FlashInfer and PyTorch is the section before this one.
* Sections above are the RTX 5060 Laptop; the transfer section is the RTX 4060 Laptop. Both are consumer GPUs with the same 32 B sectors and 64K registers per SM; the transfer is untested on a GPU that differs more (for example a datacenter part with HBM).

## Reproduce

```powershell
powershell -File tools\build_cuda.ps1 -Targets probe,sweep -Dims "128,64" -Groups "1,4,8" -Arch 120
build\cuda\bw_probe.exe --name rtx5060-laptop --out machines\rtx5060-laptop.gpu
python tools\dump_resources.py build\cuda\sweep.exe machines\resources_sm120.csv
build\kvf plan shapes\<shape>.kv --out results\plans\<shape> --top 1      # per shape
build\cuda\sweep.exe --plans <plans.csv,...> --out results\sweep_rtx5060-laptop.csv
build\kvf calibrate --sweep results\sweep_rtx5060-laptop.csv --machine machines\rtx5060-laptop.gpu --out model\constants_rtx5060.cal
build\kvf predict --sweep results\sweep_rtx5060-laptop.csv --machine machines\rtx5060-laptop.gpu --calib model\constants_rtx5060.cal --out results\predicted_full_rtx5060-laptop.csv
python tools\tuning_effort.py results\predicted_full_rtx5060-laptop.csv
build\kvf predict --sweep results\sweep_rtx5060-laptop.csv --machine machines\rtx5060-laptop.gpu --calib model\constants_rtx5060.cal --out results\predicted_rtx5060-laptop.csv
python tools\analyze.py --sweep results\sweep_rtx5060-laptop.csv --predicted results\predicted_rtx5060-laptop.csv
python tools\speedup.py results\predicted_rtx5060-laptop.csv
```

## Transfer test: the frozen model on a second GPU (RTX 4060 Laptop)

Setup: constants fitted once on the RTX 5060 Laptop (`model/constants_rtx5060.cal`, SHA-256
`01E6FEA6175B8E8093AF6DF8D43237C2DBBF1DB879D0DB1528E128E4F21BF882`, unchanged by this test),
the 4060's own machine file from `bw_probe` plus its Ada register table, **no refit**. The 4060
sweep has the same 20,928 plans over the same 10 shapes, all verified (`results/sweep_rtx4060.csv`).
Machine: Ada, compute capability 8.9, 24 SMs, 250 GB/s peak, 128 ns idle latency, 32 B sector.

| Metric (all formats unless noted) | 5060, held-out shapes | 4060, transfer |
| --- | --- | --- |
| Spearman rho | 0.88 | **0.886** |
| Kendall tau | 0.70 | 0.714 |
| MAPE, all formats / fp16 only | 15.2% / 25.1% | 22.6% / 35.2% |
| Regret, fp16 only | 15.3% | 6.6% (worst shape 17%) |
| Regret, int8 allowed | 1.9% | 11.8% (worst shape 42%) |
| Regret, all formats | 13.9% | 16.1% (worst shape 55%) |
| Speedup over naive baseline (fp16 / int8 / all) | 1.93x / 3.00x / 3.64x | 1.46x / 2.34x / 3.20x |

Success criteria written before the run: rank correlation near 0.88 (**met**: 0.886); pick within
10 to 15% of the best plan (**met** for fp16 6.6% and int8 11.8%, **narrowly missed** for all
formats 16.1%). H1 also holds on the 4060: equal-byte fp16 plans differ by 1.1x to 4.6x.

### Controls (`tools/transfer_report.py`)

Mean regret on the 4060, worst shape in brackets:

| Method | fp16 only | int8 allowed | all formats |
| --- | --- | --- | --- |
| KVForge model, frozen 5060 constants | 6.6% (17%) | 11.8% (42%) | 16.1% (55%) |
| Reuse the plan measured fastest on the 5060 (same shape) | 2.3% (8%) | 7.1% (22%) | 6.8% (18%) |
| Reuse the nearest other shape's 5060 winner (new-shape test) | 8.1% (46%) | 12.5% (61%) | 16.2% (64%) |

* The two GPUs rank plans very similarly (measured plan-by-plan rank correlation 0.85), so for
  two sibling consumer GPUs and a shape that was already tuned, **copying the winner beats the
  model**. We report that.
* On a shape nobody tuned, the model matches the nearest-shape heuristic on average and has a far
  better worst case (17/42/55% against 46/61/64%). The donor rule is our own simple heuristic.
* Refit control (not the transfer result): refitting on 4060 data cuts MAPE (32% to 16% for fp16
  on the 3 held-out shapes) but not regret (3.9% against 3.7%; 12.0% against 12.0%; 19.5% against
  12.5%). The frozen constants mis-predict absolute time more than they mis-rank plans.
  The refit moved `launch_frac`, `merge_frac` and `unpack_l2_hit` most (`results/CONTROL_refit_on_rtx4060.cal`).

### The one bad shape (H64/8, n = 8192)

The model predicts fp16 at 157 us and int8 at 161 us, a near tie. Measured: fp16 200 us, int8 152 us,
so it picks fp16 and loses 42% (int8 allowed) to 55% (all formats). The fp16 8-head-pack kernel uses
216 to 250 registers per thread on Ada and runs slower than the model expects. It is the same kernel
that trails FlashInfer on the 5060. We did not tune anything to hide this.

### Reproduce

```powershell
build\kvf evaluate --sweep results\sweep_rtx4060.csv --machine machines\rtx4060-laptop.gpu --calib model\constants_rtx5060.cal --which all
build\kvf predict  --sweep results\sweep_rtx4060.csv --machine machines\rtx4060-laptop.gpu --calib model\constants_rtx5060.cal --out results\predicted_rtx4060.csv
python tools\transfer_report.py results\sweep_rtx5060-laptop.csv results\sweep_rtx4060.csv results\predicted_rtx4060.csv
```

`machines\rtx4060-laptop.gpu` is the probe's output plus one line, `resources = resources_sm89.csv`.
