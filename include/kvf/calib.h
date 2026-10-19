#pragma once

#include <filesystem>
#include <map>
#include <string>

namespace kvf {

// The constants of the cost model that are NOT properties of one GPU.
//
// Machine holds what bw_probe measures on each device. Calib holds the few
// shape-of-the-curve constants that are fitted once, on one GPU, against the
// sweep data, and then frozen. The transfer experiment asks whether a Calib
// fitted on one GPU, combined with a freshly probed Machine for another GPU,
// still ranks plans correctly. Nothing in Calib may be refitted per device.
struct Calib {
  // Run-length efficiency: eta_run = run / (run + r0_bytes). A run is the
  // contiguous stretch of memory one block reads before jumping elsewhere.
  double r0_bytes = 64.0;
  // Cost of one block-table lookup (a dependent load before the page's data).
  double c_page_ns = 60.0;
  // Fraction of the repeated KV reads of an unpacked GQA group that L2 serves
  // when all the group's blocks are resident together. It shrinks as the group's
  // blocks spread beyond what the GPU can hold at once. With packing this is
  // irrelevant: the KV head is read once.
  double unpack_l2_hit = 0.8;
  // Loaded-to-idle memory latency ratio, for the bytes-in-flight term.
  double lat_scale = 4.0;
  // Fraction of the SM's instruction issue rate the attention inner loop
  // sustains. The loop is counted in warp instructions (runtime/kvf_kernels.cuh),
  // not FLOPs: unpacking, shuffles and softmax cost issue slots, not arithmetic.
  double issue_eff = 0.35;
  // How the last partial wave of blocks is costed: 0 scales the whole memory
  // time by ceil(waves)*capacity/blocks, 1 sums bytes/bandwidth wave by wave so
  // the tail runs at the bandwidth its few blocks can generate. Not fitted: it
  // is a structural choice, made on the fit shapes only.
  double wave_model = 0.0;
  // Issue needs enough resident warps to hide instruction latency: the sustained
  // fraction is issue_eff * (1 - exp(-warps_per_sm / warp_w0)).
  double warp_w0 = 8.0;
  // Imperfect overlap of memory and issue time: t = (t_mem^p + t_cmp^p)^(1/p).
  // p = 1 is no overlap at all, p -> infinity is perfect overlap (the max).
  double overlap_p = 4.0;
  // Share of the measured empty-kernel time charged to the main kernel and to
  // the merge kernel. Back-to-back launches hide part of the second one.
  double launch_frac = 0.5;
  double merge_frac = 0.3;
  // Extra time per element of metadata handling, as a multiple of data bytes
  // wasted on partially used sectors (token-major metadata is strided).
  double meta_waste = 1.0;

  // Measured relative L2 error of each lossy format against an exact fp32
  // reference, keyed by KvFormat::key(). Used by the accuracy gate.
  std::map<std::string, double> rel_err;

  static Calib defaults();
};

Calib loadCalib(const std::filesystem::path &p);
void saveCalib(const Calib &c, const std::filesystem::path &p);
std::string dumpCalib(const Calib &c);

} // namespace kvf
