#include "kvf/emit.h"

#include "kvf/codegen.h"

#include <algorithm>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <stdexcept>

namespace kvf {

namespace {

void writeFile(const std::filesystem::path &p, const std::string &s) {
  std::ofstream o(p, std::ios::binary);
  if (!o)
    throw std::runtime_error("cannot write " + p.string());
  o << s;
}

const Operation &plannedOp(const Module &m) {
  for (const auto &op : m.ops)
    if (op.kind == OpKind::PlannedAttn)
      return op;
  throw std::runtime_error("emit: module was not planned");
}

std::string mib(double bytes) {
  std::ostringstream o;
  o << std::fixed << std::setprecision(2) << bytes / (1024.0 * 1024.0) << " MiB";
  return o.str();
}

std::string fixed(double v, int prec) {
  std::ostringstream o;
  o << std::fixed << std::setprecision(prec) << v;
  return o.str();
}

std::string pad(const std::string &s, std::size_t w) {
  return s.size() >= w ? s : s + std::string(w - s.size(), ' ');
}

std::string lpad(const std::string &s, std::size_t w) {
  return s.size() >= w ? s : std::string(w - s.size(), ' ') + s;
}

std::string planTable(const Module &m, int top_n) {
  std::ostringstream o;
  o << pad("#", 4) << pad("plan", 58) << lpad("us", 10) << lpad("GB/s", 9)
    << lpad("%peak", 8) << lpad("I", 8) << lpad("blocks", 8) << lpad("eta", 7)
    << "  bound  status\n";
  o << std::string(118, '-') << "\n";
  const int limit =
      top_n > 0 ? std::min<int>(top_n, static_cast<int>(m.ranked.size()))
                : static_cast<int>(m.ranked.size());
  for (int i = 0; i < limit; ++i) {
    const Ranked &r = m.ranked[static_cast<std::size_t>(i)];
    o << pad(std::to_string(i + 1), 4) << pad(r.plan.str(), 58)
      << lpad(fixed(r.cost.t_total_us, 2), 10)
      << lpad(fixed(r.cost.achieved_gbs, 1), 9)
      << lpad(fixed(100.0 * r.cost.frac_of_peak, 1), 8)
      << lpad(fixed(r.cost.intensity, 2), 8) << lpad(std::to_string(r.cost.blocks), 8)
      << lpad(fixed(r.cost.eta, 2), 7) << "  "
      << pad(r.cost.memory_bound ? "mem" : "cmp", 7)
      << (r.cost.rejected ? r.cost.note : "ok") << "\n";
  }
  if (limit < static_cast<int>(m.ranked.size()))
    o << "... " << (m.ranked.size() - static_cast<std::size_t>(limit))
      << " more candidates in plans.csv\n";
  return o.str();
}

} // namespace

std::string plansCsv(const Module &m) {
  const DecodeSpec &s = m.spec;
  std::ostringstream o;
  o << "name,H,H_kv,d,n,batch,fmt,group,order,residency,block_tokens,splits,"
       "gqa_pack,warps,unroll,pred_us,pred_gbs,pred_eta,pred_mem_us,pred_cmp_us,"
       "pred_merge_us,pred_page_us,blocks,active_sms,rel_err,rejected\n";
  for (const auto &r : m.ranked) {
    const Plan &p = r.plan;
    const Cost &c = r.cost;
    o << s.name << ',' << s.H << ',' << s.H_kv << ',' << s.d << ',' << s.n << ','
      << s.batch << ',' << formatName(p.fmt.fmt) << ',' << p.fmt.group << ','
      << orderName(p.layout.order) << ',' << residencyName(p.layout.residency)
      << ',' << p.layout.block_tokens << ',' << p.part.splits << ','
      << (p.part.gqa_pack ? 1 : 0) << ',' << p.part.warps << ',' << p.part.unroll
      << ',' << c.t_total_us << ',' << c.achieved_gbs << ',' << c.eta << ','
      << c.t_mem_us << ',' << c.t_cmp_us << ',' << c.t_merge_us << ','
      << c.t_page_us << ',' << c.blocks << ',' << c.active_sms << ',' << c.rel_err
      << ',' << (c.rejected ? 1 : 0) << "\n";
  }
  return o.str();
}

std::string emitRoofline(const Module &m) {
  const DecodeSpec &s = m.spec;
  const Machine &mc = m.machine;
  std::ostringstream o;
  o << "Roofline position of this operator\n";
  o << "---------------------------------\n";
  o << "Ridge point of " << mc.name << ": " << fixed(mc.ridgeFlopPerByte(), 2)
    << " FLOP/byte  (" << fixed(mc.f32_gflops / 1000.0, 2) << " TFLOP/s over "
    << fixed(mc.bw_peak_gbs, 1) << " GB/s)\n";
  o << "Decode intensity is 2g/b_eff FLOP/byte and does not depend on n:\n";
  o << "  4*n*d FLOPs per query head over 2*n*d*b_eff bytes per KV head.\n\n";
  o << pad("format", 12) << lpad("bits/elem", 11) << lpad("g=1", 10)
    << lpad("g=4", 10) << lpad("g=8", 10) << "   verdict at this spec (g=" << s.g()
    << ")\n";
  o << std::string(72, '-') << "\n";
  for (const auto &f : candidateFormats(s.d, true)) {
    DecodeSpec t = s;
    o << pad(f.str(), 12) << lpad(fixed(f.effectiveBits(), 2), 11);
    for (int g : {1, 4, 8}) {
      t.H_kv = t.H / g > 0 ? t.H / g : 1;
      o << lpad(fixed(idealIntensity(t, f), 2), 10);
    }
    const double here = idealIntensity(s, f);
    o << "   " << (here < mc.ridgeFlopPerByte() ? "memory bound" : "compute bound")
      << "\n";
  }
  o << "\nb_eff for a quantized format is bits + metadata_bits/group, so\n";
  o << "int4:128 with an fp16 scale and zero point costs 4 + 32/128 = 4.25\n";
  o << "bits per element, not 4.\n";
  return o.str();
}

Artifacts emitAll(const Module &m, const std::filesystem::path &out_dir,
                  const std::string &ir_before, int top_n) {
  std::filesystem::create_directories(out_dir);
  const Operation &op = plannedOp(m);
  const Cost &c = op.cost;
  const DecodeSpec &s = m.spec;

  std::ostringstream o;
  o << "kvf plan report\n";
  o << "===============\n\n";
  o << "Operator: decode-phase attention, one layer, one decode step.\n";
  o << "The KV cache is read once per step and each byte is used once, so the\n";
  o << "compiler's lever is bytes moved and the order they are moved in, not\n";
  o << "tile size.\n\n";

  o << "Spec: " << s.name << "\n";
  o << "  H = " << s.H << "   H_kv = " << s.H_kv << "   g = " << s.g()
    << "   d = " << s.d << "   n = " << s.n << "   batch = " << s.batch << "\n";
  o << "  scale = " << op.scale << "\n\n";

  o << "Machine: " << m.machine.name;
  if (!m.machine_file.empty())
    o << "  (" << m.machine_file << ")";
  o << "\n";
  o << "  SMs = " << m.machine.sms << "   bw_sm = " << fixed(m.machine.bw_sm_gbs, 1)
    << " GB/s   bw_peak = " << fixed(m.machine.bw_peak_gbs, 1)
    << " GB/s   latency = " << fixed(m.machine.lat_ns, 0) << " ns\n";
  o << "  ridge = " << fixed(m.machine.ridgeFlopPerByte(), 2) << " FLOP/byte\n";
  o << "  calibration: " << (m.calib_file.empty() ? "defaults" : m.calib_file)
    << "\n\n";

  o << "Search space: format " << (m.space.format_free ? "free" : "pinned")
    << ", layout " << (m.space.layout_free ? "free" : "pinned") << ", splits "
    << (m.space.splits_free ? "free" : "pinned") << ", gqa_pack "
    << (m.space.pack_free ? "free" : "pinned") << ", lossy formats "
    << (m.space.include_quantized ? "included" : "excluded");
  if (m.space.max_rel_err > 0)
    o << " (accuracy limit " << m.space.max_rel_err << ")";
  o << "\n";
  o << "Candidates evaluated: " << m.ranked.size() << "\n\n";

  o << "Chosen plan\n-----------\n";
  o << "  format:    " << op.plan.fmt.str() << "  (" << fixed(op.plan.fmt.effectiveBits(), 2)
    << " bits/element)\n";
  o << "  layout:    " << op.plan.layout.str() << "\n";
  o << "  partition: " << op.plan.part.str() << "   blocks = " << c.blocks
    << "   active SMs = " << c.active_sms << "\n";
  if (op.plan.fmt.isQuantized())
    o << "  accuracy:  calibrated relative error " << c.rel_err << "\n";
  o << "\n";

  o << "Predicted cost\n--------------\n";
  o << "  KV payload       " << lpad(mib(c.kv_bytes), 12) << "\n";
  o << "  metadata         " << lpad(mib(c.meta_bytes), 12) << "\n";
  o << "  Q read + O write " << lpad(mib(c.qo_bytes), 12) << "\n";
  o << "  split partials   " << lpad(mib(c.partial_bytes), 12) << "\n";
  o << "  total traffic    " << lpad(mib(c.total_bytes), 12) << "\n";
  o << "  attention FLOPs  " << lpad(fixed(c.attn_flops / 1e6, 2), 12) << " M\n";
  o << "  dequant FLOPs    " << lpad(fixed(c.dequant_flops / 1e6, 2), 12) << " M\n";
  o << "  intensity        " << lpad(fixed(c.intensity, 3), 12) << " FLOP/byte\n";
  o << "  layout eta       " << lpad(fixed(c.eta, 3), 12) << "\n";
  o << "  bytes in flight  " << lpad(fixed(c.bif_sm_bytes / 1024.0, 1), 12)
    << " KiB per SM\n";
  o << "  BW_eff           " << lpad(fixed(c.bw_eff_gbs, 1), 12) << " GB/s\n";
  o << "  T_mem            " << lpad(fixed(c.t_mem_us, 2), 12) << " us\n";
  o << "  T_cmp            " << lpad(fixed(c.t_cmp_us, 2), 12) << " us\n";
  o << "  T_merge          " << lpad(fixed(c.t_merge_us, 2), 12) << " us\n";
  o << "  T_page           " << lpad(fixed(c.t_page_us, 2), 12) << " us\n";
  o << "  T_launch         " << lpad(fixed(c.t_launch_us, 2), 12) << " us\n";
  o << "  T_total          " << lpad(fixed(c.t_total_us, 2), 12) << " us   ("
    << (c.memory_bound ? "memory bound" : "compute bound") << ")\n";
  o << "  achieved         " << lpad(fixed(c.achieved_gbs, 1), 12) << " GB/s = "
    << fixed(100.0 * c.frac_of_peak, 1) << "% of peak\n\n";

  o << "Candidate ranking\n-----------------\n";
  o << planTable(m, top_n) << "\n";
  o << emitRoofline(m) << "\n";
  o << "--- IR before planning ---\n" << ir_before << "\n";
  o << "--- IR after planning ---\n" << dumpModule(m) << "\n";

  Artifacts a;
  a.dir = out_dir;
  a.report = out_dir / "report.txt";
  a.plans_csv = out_dir / "plans.csv";
  a.ir_txt = out_dir / "ir.txt";
  a.kernel_cu = out_dir / ("decode_" + s.name + ".cu");
  writeFile(a.report, o.str());
  writeFile(a.plans_csv, plansCsv(m));
  writeFile(a.ir_txt, "--- before planning ---\n" + ir_before +
                          "\n--- after planning ---\n" + dumpModule(m));
  writeFile(a.kernel_cu, emitKernelSource(m));
  writeFile(out_dir / "plan_info.h", emitPlanHeader(m));
  return a;
}

} // namespace kvf
