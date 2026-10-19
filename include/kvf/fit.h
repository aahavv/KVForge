#pragma once

#include "kvf/calib.h"
#include "kvf/cost.h"
#include "kvf/machine.h"

#include <filesystem>
#include <functional>
#include <string>
#include <vector>

namespace kvf {

// One measured configuration, as written by the sweep harness.
struct SweepRow {
  DecodeSpec spec;
  Plan plan;
  double t_us = 0;       // median measured time
  double t_p25 = 0, t_p75 = 0;
  double err_exact = 0;  // relative L2 error against the exact fp32 attention
  bool verified = true;  // kernel output matched the dequantised reference
};

std::vector<SweepRow> loadSweep(const std::filesystem::path &p);

// Prediction quality over a set of measured rows.
struct Metrics {
  int rows = 0;
  int shapes = 0;
  double mape = 0;            // mean |pred - meas| / meas
  double spearman = 0;        // mean over shapes
  double kendall = 0;         // mean over shapes
  double regret_mean = 0;     // T_meas(chosen) / T_meas(best) - 1, mean over shapes
  double regret_max = 0;
  double top1 = 0;            // fraction of shapes where the best plan was chosen
  std::string per_shape;      // one line per shape
};

// Which rows may be chosen: a format filter and an accuracy limit, so the
// regret is measured against the best plan the user would have accepted.
struct Eligibility {
  double max_rel_err = 0;                 // 0 = every format
  std::vector<std::string> formats;       // empty = every format; else fmt names
};

Metrics evaluateSweep(const std::vector<SweepRow> &rows, const Machine &m,
                      const Calib &c, const Eligibility &elig,
                      const std::function<bool(const std::string &)> &use_shape);

// Stable key of a decode shape within a sweep.
std::string shapeKey(const DecodeSpec &s);

// Fit the shape-of-the-curve constants on the rows selected by use_shape and
// measure the accuracy of each lossy format. The machine description is held
// fixed: only Calib is fitted.
Calib calibrate(const std::vector<SweepRow> &rows, const Machine &m,
                const Calib &start,
                const std::function<bool(const std::string &)> &use_shape);

} // namespace kvf
