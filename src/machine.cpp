#include "kvf/machine.h"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <vector>

namespace kvf {

double Machine::ridgeFlopPerByte() const {
  return bw_peak_gbs > 0 ? f32_gflops / bw_peak_gbs : 0;
}

double Machine::bwSmGbs(double bif_sm_bytes, double lat_scale) const {
  if (lat_ns <= 0)
    return bw_sm_gbs;
  return std::min(bw_sm_gbs, bif_sm_bytes / (lat_ns * std::max(1.0, lat_scale)));
}

double Machine::bwDeviceGbs(int active_sms, double bif_sm_bytes, double lat_scale) const {
  active_sms = std::clamp(active_sms, 1, std::max(1, sms));
  return std::min(bw_peak_gbs, active_sms * bwSmGbs(bif_sm_bytes, lat_scale));
}

Machine Machine::defaults() { return Machine{}; }

void applyMachineKey(Machine &m, const std::string &key, double value,
                     const std::string &raw) {
  if (key == "name") {
    m.name = raw;
  } else if (key == "compute_capability") {
    m.compute_capability = value;
  } else if (key == "dram_gb") {
    m.dram_gb = value;
  } else if (key == "sms") {
    m.sms = static_cast<int>(value);
  } else if (key == "bw_peak_gbs") {
    m.bw_peak_gbs = value;
  } else if (key == "bw_sm_gbs") {
    m.bw_sm_gbs = value;
  } else if (key == "lat_ns") {
    m.lat_ns = value;
  } else if (key == "bw_l2_gbs") {
    m.bw_l2_gbs = value;
  } else if (key == "l2_bytes") {
    m.l2_bytes = static_cast<long long>(value);
  } else if (key == "sector_bytes") {
    m.sector_bytes = static_cast<int>(value);
  } else if (key == "line_bytes") {
    m.line_bytes = static_cast<int>(value);
  } else if (key == "f32_gflops") {
    m.f32_gflops = value;
  } else if (key == "launch_us") {
    m.launch_us = value;
  } else if (key == "max_warps_per_sm") {
    m.max_warps_per_sm = static_cast<int>(value);
  } else if (key == "max_blocks_per_sm") {
    m.max_blocks_per_sm = static_cast<int>(value);
  } else if (key == "regs_per_sm") {
    m.regs_per_sm = static_cast<int>(value);
  } else if (key == "resources") {
    m.resources_file = raw;
  } else {
    throw std::runtime_error("unknown machine key '" + key + "'");
  }
}

Machine loadMachine(const std::filesystem::path &p) {
  std::ifstream in(p);
  if (!in)
    throw std::runtime_error("cannot read machine file " + p.string());
  Machine m = Machine::defaults();
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
      const auto a = s.find_first_not_of(" \t\r\n\"");
      const auto b = s.find_last_not_of(" \t\r\n\"");
      return a == std::string::npos ? std::string() : s.substr(a, b - a + 1);
    };
    const std::string key = trim(line.substr(0, eq));
    const std::string raw = trim(line.substr(eq + 1));
    double value = 0;
    try {
      value = std::stod(raw);
    } catch (const std::exception &) {
      value = 0; // string-valued keys (name)
    }
    applyMachineKey(m, key, value, raw);
  }

  // The resource table is named relative to the machine file.
  if (!m.resources_file.empty()) {
    std::filesystem::path rp(m.resources_file);
    if (!std::filesystem::exists(rp) && rp.is_relative())
      rp = p.parent_path() / rp;
    std::ifstream rin(rp);
    if (!rin)
      throw std::runtime_error("cannot read resource table " + rp.string());
    std::string rl;
    std::getline(rin, rl); // header: fmt,d,g,u,ord,paged,final,regs,smem
    while (std::getline(rin, rl)) {
      std::stringstream ss(rl);
      std::string tok;
      std::vector<int> f;
      while (std::getline(ss, tok, ','))
        f.push_back(std::stoi(tok));
      if (f.size() < 8)
        continue;
      std::ostringstream key;
      key << f[0] << '_' << f[1] << '_' << f[2] << '_' << f[3] << '_' << f[4] << '_'
          << f[5] << '_' << f[6];
      m.kernel_regs[key.str()] = f[7];
    }
  }
  return m;
}

std::string dumpMachine(const Machine &m) {
  std::ostringstream o;
  o << "name = " << m.name << "\n";
  o << "compute_capability = " << m.compute_capability << "\n";
  o << "dram_gb = " << m.dram_gb << "\n";
  o << "sms = " << m.sms << "\n";
  o << "bw_peak_gbs = " << m.bw_peak_gbs << "\n";
  o << "bw_sm_gbs = " << m.bw_sm_gbs << "\n";
  o << "lat_ns = " << m.lat_ns << "\n";
  o << "bw_l2_gbs = " << m.bw_l2_gbs << "\n";
  o << "l2_bytes = " << m.l2_bytes << "\n";
  o << "sector_bytes = " << m.sector_bytes << "\n";
  o << "line_bytes = " << m.line_bytes << "\n";
  o << "f32_gflops = " << m.f32_gflops << "\n";
  o << "launch_us = " << m.launch_us << "\n";
  o << "max_warps_per_sm = " << m.max_warps_per_sm << "\n";
  o << "max_blocks_per_sm = " << m.max_blocks_per_sm << "\n";
  o << "regs_per_sm = " << m.regs_per_sm << "\n";
  if (!m.resources_file.empty())
    o << "resources = " << m.resources_file << "\n";
  return o.str();
}

} // namespace kvf
