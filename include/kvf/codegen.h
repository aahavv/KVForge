#pragma once

#include "kvf/ir.h"

#include <string>
#include <utility>
#include <vector>

namespace kvf {

// Source-to-source CUDA code generation.
//
// The kernel library (runtime/kvf_kernels.cuh) is a set of templates whose
// parameters are the plan's compile-time choices: storage format, layout,
// GQA packing, head dimension and unroll. Code generation turns a planned
// kvf.decode_attn_split into translation units that instantiate exactly the
// variant the plan names and expose it through a plain C launcher.

// Stable identifier of the compile-time part of a plan, e.g.
// "int8_hm_c_g4_u2_d128". Two plans with the same id share one instantiation.
std::string variantId(const Plan &p, int g, int d);

// The .cu for the chosen plan: one instantiation plus `kvf_launch_<name>`.
std::string emitKernelSource(const Module &m);

// plan_info.h: the shape and plan as constants for the generated driver.
std::string emitPlanHeader(const Module &m);

// A dispatch table covering every variant the enumerator can produce for the
// given head dimensions and GQA group sizes: explicit instantiations plus a
// registration function per bucket and a kvf_register_all. Returned as
// (file name, contents), one bucket per format x order x residency so nvcc can
// build them in parallel.
std::vector<std::pair<std::string, std::string>>
emitDispatchSources(const std::vector<int> &dims, const std::vector<int> &groups,
                    bool include_quantized);

} // namespace kvf
