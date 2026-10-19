#include "kvf/cost.h"

#include <algorithm>
#include <cmath>
#include <sstream>

namespace kvf {

namespace {

// Bytes a lane loads per token per step. The kernels give every lane eight
// elements of a row, so the vector width follows the storage format.
int laneVectorBytes(const KvFormat &f) { return 8 * f.rawBits() / 8; }

// Warp instructions the inner loop of runtime/kvf_kernels.cuh issues per lane,
// counted from the source. A visit is one block reading one token's K and V rows
// for G query heads at once. Everything that is per token (addressing, two vector
// loads, unpacking K and V) is paid once per visit; everything per head (the dot
// product, the lane reduction, the softmax update, the value accumulation) is
// paid G times.
struct InstrCost {
  double per_token;
  double per_token_head;
};

InstrCost instrCost(const KvFormat &f, int lanes_per_token) {
  InstrCost c;
  const bool q = f.isQuantized();
  const double unpack = f.fmt == Format::F16 ? 8.0 : 32.0; // K and V, 8 elements
  c.per_token = 10.0 + unpack;
  const double reduce = 2.0 * std::log2(static_cast<double>(lanes_per_token));
  c.per_token_head = 8.0                  // dot product, 8 FMAs
                     + (q ? 2.0 : 0.0)    // scale and zero-point correction
                     + reduce             // shuffle + add per reduction step
                     + 12.0               // running max, two exp2, rescale
                     + (q ? 16.0 : 8.0);  // value accumulation
  return c;
}

// Registers per thread of the kernel a plan compiles to, looked up in the table
// the build extracted from the binary; an estimate when the table has no entry.
int kernelRegs(const Machine &m, const DecodeSpec &s, const Plan &p) {
  const int fmt = p.fmt.fmt == Format::F16 ? 0 : p.fmt.fmt == Format::INT8 ? 1 : 2;
  const int g = p.part.gqa_pack ? s.g() : 1;
  const int ord = p.layout.order == Order::HeadMajor ? 0 : 1;
  const int fin = p.part.splits == 1 ? 1 : 0;
  std::ostringstream key;
  key << fmt << '_' << s.d << '_' << g << '_' << p.part.unroll << '_' << ord << '_'
      << (p.layout.paged() ? 1 : 0) << '_' << fin;
  const int r = m.regsFor(key.str());
  return r > 0 ? r : 64 + 22 * g + 8 * p.part.unroll;
}

// Length in bytes of the contiguous run one block reads before it must jump
// elsewhere in memory. A block scans one KV head over its chunk of tokens.
double runBytes(const DecodeSpec &s, const KvFormat &f, const KvLayout &l,
                double chunk_tokens) {
  const double row = f.dataRowBytes(s.d);
  if (l.order == Order::TokenMajor)
    return row; // the next token of the same head is H_kv rows away
  // HeadMajor: consecutive tokens of one head are adjacent, up to the page.
  if (l.paged())
    return std::min<double>(l.block_tokens, chunk_tokens) * row;
  return chunk_tokens * row;
}

// eta_run = run / (run + r0), normalised so an unbounded run scores 1.
double runEfficiency(double run, double r0) {
  const double big = 1 << 22;
  const double ref = big / (big + r0);
  return std::min(1.0, (run / (run + r0)) / ref);
}

} // namespace

double idealIntensity(const DecodeSpec &s, const KvFormat &f) {
  // 4nd FLOPs per query head, 2nd*b bytes per KV head: the n cancels.
  return 2.0 * s.g() / f.effectiveBytes();
}

Cost evaluate(const DecodeSpec &s, const Machine &m, const Calib &c,
              const Plan &p, double max_rel_err) {
  Cost k;
  const int g = s.g();
  const bool pack = p.part.gqa_pack;
  const int loading_heads = pack ? s.H_kv : s.H;
  const double rows = 1.0 * s.n * s.H_kv * s.batch; // rows of K, same for V
  const double data_row = p.fmt.dataRowBytes(s.d);
  const double meta_row = p.fmt.metaRowBytes(s.d);

  // Blocks are launched split-fastest, so the g blocks of a GQA group that share
  // a KV chunk are `splits` blocks apart. They hit each other's lines in L2 only
  // while all of them are resident together.
  // Blocks per SM are limited by block slots, warp slots and registers.
  int resident_cap =
      std::max(1, std::min(m.max_blocks_per_sm, m.max_warps_per_sm / p.part.warps));
  if (m.regs_per_sm > 0) {
    const int regs = (kernelRegs(m, s, p) + 7) / 8 * 8;
    const int warp_regs = (regs * 32 + 255) / 256 * 256; // allocated per warp
    resident_cap = std::max(
        1, std::min(resident_cap, m.regs_per_sm / (warp_regs * p.part.warps)));
  }
  const double resident_total = 1.0 * m.sms * resident_cap;
  const double window =
      std::clamp(resident_total / (1.0 * g * p.part.splits), 0.0, 1.0);

  // Without GQA packing every query head streams its KV head independently, so
  // the same rows are requested g times. L2 serves the repeats only inside the
  // co-residency window.
  const double reread =
      pack ? 1.0 : 1.0 + (g - 1) * (1.0 - c.unpack_l2_hit * window);
  k.kv_bytes = 2.0 * rows * data_row * reread;

  // Token-major metadata is strided: each row's few scale bytes sit in a sector
  // shared with other heads, so most of the fetched sector is wasted.
  double meta_eff = 1.0;
  if (meta_row > 0 && p.layout.order == Order::TokenMajor)
    meta_eff = std::min(1.0, meta_row / m.sector_bytes);
  k.meta_bytes = 2.0 * rows * meta_row * reread / std::pow(meta_eff, c.meta_waste);

  k.qo_bytes = 2.0 * s.H * s.d * 4.0 * s.batch; // read Q, write O, both fp32
  if (p.part.splits > 1)
    k.partial_bytes = 2.0 * s.H * p.part.splits * (s.d + 2) * 4.0 * s.batch;
  const double main_bytes = k.kv_bytes + k.meta_bytes + k.qo_bytes;
  k.total_bytes = main_bytes + k.partial_bytes;

  k.attn_flops = 4.0 * s.n * s.d * s.H * s.batch; // QK^T then PV
  const double elems = 2.0 * s.n * s.d * loading_heads * s.batch; // K and V
  k.dequant_flops = elems * p.fmt.dequantFlopsPerElem();
  k.total_flops = k.attn_flops + k.dequant_flops;
  k.intensity = k.total_bytes > 0 ? k.total_flops / k.total_bytes : 0;

  // Parallel work: one block per (split, loading head, sequence).
  k.blocks = 1LL * p.part.splits * loading_heads * s.batch;
  k.active_sms = static_cast<int>(std::min<long long>(k.blocks, m.sms));
  const long long per_sm = (k.blocks + m.sms - 1) / m.sms;
  k.resident_blocks =
      static_cast<int>(std::clamp<long long>(per_sm, 1, resident_cap));

  // Little's law: bytes in flight per SM over memory latency caps per-SM
  // bandwidth. Every lane keeps `unroll` vector loads in flight.
  const double bif_block =
      1.0 * p.part.warps * 32 * laneVectorBytes(p.fmt) * p.part.unroll * 2.0; // K and V
  k.bif_sm_bytes = k.resident_blocks * bif_block;

  const double chunk = std::ceil(static_cast<double>(s.n) / p.part.splits);
  k.eta = runEfficiency(runBytes(s, p.fmt, p.layout, chunk), c.r0_bytes);

  // Bandwidth the machine delivers while n blocks stream together: each SM holds
  // its share of blocks, so its bytes in flight (and Little's-law rate) follow.
  const long long capacity = static_cast<long long>(resident_total);
  auto aggregate = [&](long long n) {
    const long long act = std::min<long long>(n, m.sms);
    const long long per =
        std::clamp<long long>((n + m.sms - 1) / m.sms, 1, resident_cap);
    return k.eta * m.bwDeviceGbs(static_cast<int>(act), per * bif_block, c.lat_scale);
  };
  k.bw_eff_gbs = aggregate(std::min(k.blocks, capacity));

  // GB/s to bytes/us: 1 GB/s == 1000 bytes/us.
  // Waves. Blocks run `capacity` at a time; the last wave has fewer blocks, so it
  // generates less bandwidth. Time is the sum over waves of bytes / bandwidth.
  {
    const double per_block_bytes = main_bytes / static_cast<double>(k.blocks);
    const long long full = k.blocks / capacity;
    const long long tail = k.blocks - full * capacity;
    double t = 0;
    if (full > 0)
      t += full * (capacity * per_block_bytes) / (aggregate(capacity) * 1000.0);
    if (tail > 0)
      t += (tail * per_block_bytes) / (aggregate(tail) * 1000.0);
    const double ideal = main_bytes / (k.bw_eff_gbs * 1000.0);
    if (c.wave_model < 0.5) {
      // Whole-run scaling by the wave count.
      if (k.blocks > capacity) {
        const long long waves = (k.blocks + capacity - 1) / capacity;
        k.imbalance = static_cast<double>(waves * capacity) / static_cast<double>(k.blocks);
      } else if (k.blocks > m.sms) {
        k.imbalance = static_cast<double>(per_sm * m.sms) / static_cast<double>(k.blocks);
      } else {
        k.imbalance = 1.0;
      }
      k.t_mem_us = ideal * k.imbalance;
    } else {
      k.t_mem_us = t;
      k.imbalance = ideal > 0 ? t / ideal : 1.0;
    }
  }
  // Compute time is issue time: warp instructions over the SMs' issue rate. One
  // warp-wide FMA is 64 FLOPs, so FP32 GFLOP/s over 64 is warp-instructions/ns.
  {
    const int lanes = s.d / 8;
    const double tokens_per_warp_step = 32.0 / lanes;
    const int pack_g = pack ? g : 1;
    const InstrCost ic = instrCost(p.fmt, lanes);
    const double visits = 1.0 * s.batch * loading_heads * s.n;
    const double warp_instr =
        visits * (ic.per_token + pack_g * ic.per_token_head) / tokens_per_warp_step;
    const double rate_per_sm = m.fSmGflops() / 64.0; // warp-instructions per ns
    // Warps resident on a busy SM: too few and the pipeline cannot be kept full.
    const double warps_per_sm = 1.0 * k.resident_blocks * p.part.warps;
    const double occupancy = 1.0 - std::exp(-warps_per_sm / c.warp_w0);
    k.t_cmp_us = warp_instr / (std::max(1, k.active_sms) * rate_per_sm *
                               c.issue_eff * occupancy) / 1000.0;
  }
  k.memory_bound = k.t_mem_us >= k.t_cmp_us;
  // Memory and issue overlap imperfectly: a p-norm between the sum and the max.
  const double t_par =
      std::pow(std::pow(k.t_mem_us, c.overlap_p) + std::pow(k.t_cmp_us, c.overlap_p),
               1.0 / c.overlap_p);

  // Merge kernel: one more launch, plus every partial read back through L2.
  if (p.part.splits > 1)
    k.t_merge_us =
        c.merge_frac * m.launch_us + k.partial_bytes / (m.bw_l2_gbs * 1000.0);

  // Paged indirection: one dependent block-table load per page a warp enters,
  // not hidden by the loads already in flight.
  if (p.layout.paged() && p.layout.block_tokens > 0) {
    const double pages =
        std::ceil(chunk / p.layout.block_tokens) * k.blocks * p.part.warps;
    const double parallel = std::max(1.0, 1.0 * k.active_sms * k.resident_blocks *
                                              p.part.warps);
    k.t_page_us = pages * c.c_page_ns / parallel / 1000.0;
  }

  k.t_launch_us = c.launch_frac * m.launch_us;
  k.t_total_us = t_par + k.t_merge_us + k.t_page_us + k.t_launch_us;
  k.achieved_gbs =
      k.t_total_us > 0 ? (k.kv_bytes + k.meta_bytes) / (k.t_total_us * 1000.0) : 0;
  k.frac_of_peak = m.bw_peak_gbs > 0 ? k.achieved_gbs / m.bw_peak_gbs : 0;

  // Accuracy gate: lossy formats carry a measured relative error.
  if (p.fmt.isQuantized()) {
    const auto it = c.rel_err.find(p.fmt.key());
    k.rel_err = it == c.rel_err.end() ? 1.0 : it->second;
  }
  if (max_rel_err > 0 && k.rel_err > max_rel_err) {
    k.rejected = true;
    k.note = "rejected: error above accuracy limit";
  }
  return k;
}

std::vector<Ranked> rankPlans(const DecodeSpec &s, const Machine &m,
                              const Calib &c, const std::vector<Plan> &plans,
                              double max_rel_err) {
  std::vector<Ranked> out;
  out.reserve(plans.size());
  for (const auto &p : plans)
    out.push_back(Ranked{p, evaluate(s, m, c, p, max_rel_err)});
  std::stable_sort(out.begin(), out.end(), [](const Ranked &a, const Ranked &b) {
    return a.cost.t_total_us < b.cost.t_total_us;
  });
  return out;
}

} // namespace kvf
