#include "kvf/calib.h"

#include <fstream>
#include <iomanip>
#include <sstream>
#include <stdexcept>

namespace kvf {

Calib Calib::defaults() {
  Calib c;
  // Placeholder accuracy figures until bench/sweep measures them. They are the
  // order of magnitude expected for group-wise asymmetric quantization of
  // unit-variance data, and are overwritten by `kvf calibrate`.
  c.rel_err["int8_64"] = 0.004;
  c.rel_err["int8_128"] = 0.005;
  c.rel_err["int4_32"] = 0.06;
  c.rel_err["int4_64"] = 0.07;
  c.rel_err["int4_128"] = 0.08;
  return c;
}

namespace {
const char *kScalarKeys[] = {"r0_bytes", "c_page_ns", "unpack_l2_hit", "issue_eff",
                             "meta_waste", "overlap_p", "launch_frac", "merge_frac",
                             "lat_scale", "warp_w0", "wave_model"};
}

static double &scalar(Calib &c, const std::string &k) {
  if (k == "r0_bytes") return c.r0_bytes;
  if (k == "c_page_ns") return c.c_page_ns;
  if (k == "unpack_l2_hit") return c.unpack_l2_hit;
  if (k == "issue_eff") return c.issue_eff;
  if (k == "meta_waste") return c.meta_waste;
  if (k == "overlap_p") return c.overlap_p;
  if (k == "launch_frac") return c.launch_frac;
  if (k == "merge_frac") return c.merge_frac;
  if (k == "lat_scale") return c.lat_scale;
  if (k == "warp_w0") return c.warp_w0;
  if (k == "wave_model") return c.wave_model;
  throw std::runtime_error("unknown calibration key '" + k + "'");
}

Calib loadCalib(const std::filesystem::path &p) {
  std::ifstream in(p);
  if (!in)
    throw std::runtime_error("cannot read calibration file " + p.string());
  Calib c = Calib::defaults();
  std::string line;
  int lineno = 0;
  while (std::getline(in, line)) {
    ++lineno;
    const auto hash = line.find('#');
    if (hash != std::string::npos)
      line = line.substr(0, hash);
    const auto eq = line.find('=');
    if (eq == std::string::npos) {
      if (line.find_first_not_of(" \t\r\n") != std::string::npos)
        throw std::runtime_error(p.string() + ":" + std::to_string(lineno) +
                                 ": expected key = value");
      continue;
    }
    auto trim = [](std::string s) {
      const auto a = s.find_first_not_of(" \t\r\n");
      const auto b = s.find_last_not_of(" \t\r\n");
      return a == std::string::npos ? std::string() : s.substr(a, b - a + 1);
    };
    const std::string key = trim(line.substr(0, eq));
    const double v = std::stod(trim(line.substr(eq + 1)));
    if (key.rfind("rel_err.", 0) == 0)
      c.rel_err[key.substr(8)] = v;
    else
      scalar(c, key) = v;
  }
  return c;
}

std::string dumpCalib(const Calib &c) {
  std::ostringstream o;
  o << std::setprecision(8);
  Calib tmp = c;
  for (const char *k : kScalarKeys)
    o << k << " = " << scalar(tmp, k) << "\n";
  for (const auto &kv : c.rel_err)
    o << "rel_err." << kv.first << " = " << kv.second << "\n";
  return o.str();
}

void saveCalib(const Calib &c, const std::filesystem::path &p) {
  std::ofstream o(p);
  if (!o)
    throw std::runtime_error("cannot write " + p.string());
  o << "# KVForge cost-model constants. Fitted once on one GPU, then frozen.\n";
  o << dumpCalib(c);
}

} // namespace kvf
