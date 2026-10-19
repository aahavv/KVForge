#pragma once

#include <filesystem>
#include <map>
#include <string>

namespace kvf {

// Measured and derived parameters of the target GPU.
//
// Every number here is something bench/bw_probe can measure directly, so none
// of them has to be taken from a datasheet. Datasheet bandwidth is a peak that
// no kernel reaches; the model needs the sustained figure.
//
// Bandwidth is split into a per-SM figure and a device figure because one SM
// cannot saturate DRAM: with a bounded number of bytes in flight, per-SM
// bandwidth is latency limited (Little's law: bytes in flight / latency).
struct Machine {
  std::string name = "generic-gpu";
  double compute_capability = 0; // informational
  double dram_gb = 0;            // informational

  int sms = 24;
  double bw_peak_gbs = 250.0; // sustained DRAM read bandwidth, all SMs
  double bw_sm_gbs = 15.0;    // sustained read bandwidth of one SM, ample warps
  double lat_ns = 600.0;      // DRAM load-to-use latency
  double bw_l2_gbs = 1000.0;  // L2 read bandwidth
  long long l2_bytes = 32LL * 1024 * 1024;
  int sector_bytes = 32; // DRAM/L2 transaction granularity
  int line_bytes = 128;

  double f32_gflops = 10000.0; // sustained FP32 FMA throughput, all SMs
  double launch_us = 3.0;      // per-kernel launch and completion overhead
  int max_warps_per_sm = 48;
  int max_blocks_per_sm = 24;
  int regs_per_sm = 0; // 32-bit registers per SM; 0 disables the register limit

  // Registers per thread of each generated kernel, read back from the compiled
  // binary by tools/dump_resources.py. Keyed by `kernelKey`. Empty means the
  // model falls back to an estimate.
  std::string resources_file;
  std::map<std::string, int> kernel_regs;

  // Sustained FP32 FLOP/s of one SM.
  double fSmGflops() const { return sms > 0 ? f32_gflops / sms : 0; }
  // Device FLOP/s over DRAM bandwidth: the roofline ridge point.
  double ridgeFlopPerByte() const;
  // Little's law: one SM with `bif_sm` bytes in flight sustains
  // min(bw_sm, bif_sm / latency). Bytes per ns is GB/s.
  // `lat_scale` is the loaded-to-idle latency ratio (a fitted constant): under
  // load, queueing in the memory system makes a request take several times the
  // idle latency bw_probe measures.
  double bwSmGbs(double bif_sm_bytes, double lat_scale = 1.0) const;
  // Device bandwidth with `active_sms` SMs each holding `bif_sm` bytes in
  // flight, capped by the device peak.
  double bwDeviceGbs(int active_sms, double bif_sm_bytes, double lat_scale = 1.0) const;

  // Registers per thread for a kernel variant, or 0 if the table has none.
  int regsFor(const std::string &key) const {
    const auto it = kernel_regs.find(key);
    return it == kernel_regs.end() ? 0 : it->second;
  }

  static Machine defaults();
};

// Machines are stored as `key = value` lines (see machines/*.gpu). Unknown keys
// are an error, so a typo in a target file cannot silently change a prediction.
Machine loadMachine(const std::filesystem::path &p);
void applyMachineKey(Machine &m, const std::string &key, double value,
                     const std::string &raw);
std::string dumpMachine(const Machine &m);

} // namespace kvf
