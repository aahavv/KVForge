#pragma once

#include "kvf/ir.h"

#include <filesystem>
#include <string>

namespace kvf {

struct Artifacts {
  std::filesystem::path dir;
  std::filesystem::path report;    // human-readable analysis
  std::filesystem::path plans_csv; // every candidate, for plotting
  std::filesystem::path ir_txt;    // IR before and after planning
  std::filesystem::path kernel_cu; // generated CUDA for the chosen plan
};

Artifacts emitAll(const Module &m, const std::filesystem::path &out_dir,
                  const std::string &ir_before, int top_n);

// The roofline table that motivates the whole project: intensity against the
// machine's ridge point for each storage format and GQA group size.
std::string emitRoofline(const Module &m);

// One CSV row per plan, with the same columns the sweep harness writes for
// measured runs, so predicted and measured data line up.
std::string plansCsv(const Module &m);

} // namespace kvf
