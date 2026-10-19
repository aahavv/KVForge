#pragma once

#include "kvf/calib.h"
#include "kvf/plan.h"

#include <string>
#include <vector>

namespace kvf {

// Predicted cost of one decode step for one layer, under one plan.
//
//   T = max( Bytes / BW_eff , FLOPs / F_eff ) * imbalance
//       + T_merge + T_page + T_launch
//
// Decode attention sits far below the roofline ridge point, so the first term
// almost always wins; the model still evaluates both so that GQA packing and
// low-bit formats, which push intensity up toward the ridge, are not credited
// with speedups the machine cannot deliver.
struct Cost {
  double kv_bytes = 0;       // K and V payload fetched from DRAM
  double meta_bytes = 0;     // quantization scales and zero points
  double qo_bytes = 0;       // query read and output write
  double partial_bytes = 0;  // split-KV partial results, written then merged
  double total_bytes = 0;

  double attn_flops = 0;     // QK^T and PV
  double dequant_flops = 0;  // unpack and rescale
  double total_flops = 0;

  double intensity = 0;      // total_flops / total_bytes
  double eta = 1.0;          // layout bandwidth efficiency in (0, 1]
  long long blocks = 0;      // thread blocks launched
  int active_sms = 0;
  int resident_blocks = 0;   // blocks resident per SM
  double bif_sm_bytes = 0;   // bytes in flight per SM
  double imbalance = 1.0;    // ceil(blocks/sms) * sms / blocks
  double bw_eff_gbs = 0;     // after eta

  double t_mem_us = 0;
  double t_cmp_us = 0;
  double t_merge_us = 0;
  double t_page_us = 0;
  double t_launch_us = 0;
  double t_total_us = 0;

  double achieved_gbs = 0;   // kv_bytes / t_total
  double frac_of_peak = 0;   // achieved / bw_peak
  bool memory_bound = true;
  double rel_err = 0;        // calibrated relative error of this format
  bool rejected = false;     // failed the accuracy gate
  std::string note;
};

Cost evaluate(const DecodeSpec &s, const Machine &m, const Calib &c,
              const Plan &p, double max_rel_err = 0.0);

struct Ranked {
  Plan plan;
  Cost cost;
};

// Evaluate every candidate and sort by predicted time, cheapest first.
std::vector<Ranked> rankPlans(const DecodeSpec &s, const Machine &m,
                              const Calib &c, const std::vector<Plan> &plans,
                              double max_rel_err = 0.0);

// Arithmetic intensity of the idealized decode step, 2g/b FLOP/byte: the
// context length cancels, which is why tile size cannot fix this operator.
double idealIntensity(const DecodeSpec &s, const KvFormat &f);

} // namespace kvf
