# The KVForge cost model

One decode step, one layer. Everything is predicted from (a) the shape, (b) the
plan, (c) a machine file measured by `bench/bw_probe`, and (d) a handful of
frozen constants in `model/*.cal`.

```
T = ( T_mem^p + T_cmp^p )^(1/p) * imbalance  +  T_merge  +  T_page  +  T_launch
```

## Terms

| # | Term | Formula | Basis |
| --- | --- | --- | --- |
| 1 | Bytes moved | `B = 2 * rows * (data_row + meta_row) * reread + B_qo` | Counting. With reuse = 1 every cached row is read once per step; `reread = 1` with GQA packing, `1 + (g-1)(1 - hit)` without |
| 2 | Effective element size | `b_eff = (bits + 32/G) / 8` bytes | Group-wise scale and zero point (as in KIVI, KVQuant, QServe) |
| 3 | Intensity | `I = 2g / b_eff` FLOP/byte | Derivation: `4nd` FLOPs per query head over `2*n*d*b_eff` bytes per KV head; `n` and `d` cancel |
| 4 | Bytes in flight | `B_if = blocks_resident * warps * 32 * vec_bytes * 2 * unroll` | Read from the kernel: every lane keeps K and V vector loads for `unroll` tokens outstanding |
| 5 | Per-SM bandwidth | `BW_sm = min( bw_sm , B_if / latency )` | Little's law. `bw_sm` and `latency` are measured |
| 6 | Device bandwidth | `BW_dev = min( bw_peak , active_SMs * BW_sm )` | Measured peak |
| 7 | Layout efficiency | `eta = run / (run + r0)`, normalised | `run` is the contiguous run a block reads before it jumps (a row for token-major, a whole chunk or page for head-major). `r0` is fitted |
| 8 | Memory time | `T_mem = B / (eta * BW_dev)` | |
| 9 | Issue time | `T_cmp = warp_instr / (active_SMs * rate_sm * issue_eff)` | Counted from the kernel source: a per-token part (addressing, loads, unpack) and a per-head part (dot product, lane reduction, softmax, accumulation). `rate_sm` is the measured FP32 rate over 64 FLOPs per warp FMA |
| 10 | Overlap | p-norm of `T_mem` and `T_cmp` | Memory and issue overlap imperfectly: `p = 1` is a sum, `p -> inf` is the max. `p` is fitted |
| 11 | Imbalance | `ceil(blocks / S) * S / blocks` when `blocks > S` | Wave quantisation on `S` SMs |
| 12 | Merge | `T_merge = merge_frac * launch + B_partial / BW_L2` | One more kernel plus the partials read back through L2 |
| 13 | Paging | `T_page = lookups * c_page / parallelism` | One dependent block-table load per page a warp enters |
| 14 | Launch | `T_launch = launch_frac * launch` | Measured empty-kernel time, scaled by a fitted fraction |

## What is measured and what is fitted

Measured on each GPU by `bw_probe` (the **machine file**): `sms`, `bw_peak_gbs`,
`bw_sm_gbs`, `lat_ns`, `bw_l2_gbs`, `f32_gflops`, `launch_us`, `sector_bytes`,
`l2_bytes`, `max_warps_per_sm`, `max_blocks_per_sm`.

Fitted once on one GPU and then frozen (the **calibration file**): `r0_bytes`,
`c_page_ns`, `unpack_l2_hit`, `issue_eff`, `meta_waste`, `overlap_p`,
`launch_frac`, `merge_frac`, and the measured relative error of each lossy
format.

The transfer experiment is exactly the claim that the second list does not
depend on the GPU: constants fitted on one device, combined with a freshly probed
machine file for another, should still rank the plans correctly.

## Accuracy gate

Lossy formats change the numbers. `max_rel_err` in the spec is the budget: a plan
is rejected if its format's calibrated relative L2 error against exact fp32
attention exceeds it. The errors come from the sweep (`err_exact`), measured on
unit-variance random data. Real KV caches have outliers, so the gate is a model
of accuracy, not a guarantee; a deployment should re-measure on its own data.
