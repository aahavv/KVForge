#include "kvf/ir.h"

#include <cmath>
#include <filesystem>
#include <sstream>
#include <stdexcept>
#include <unordered_map>

namespace kvf {

int Module::addValue(std::string name, ValueType ty) {
  Value v;
  v.id = static_cast<int>(values.size());
  v.name = std::move(name);
  v.type = std::move(ty);
  values.push_back(std::move(v));
  return values.back().id;
}

std::string ValueType::str() const {
  std::ostringstream o;
  if (kind == ValueKind::Dense) {
    o << "tensor<" << rows << "x" << cols << "xf32>";
    return o.str();
  }
  o << "kvcache<" << rows << "x" << cols << "x" << fmt.str() << ", "
    << layout.str() << ">";
  return o.str();
}

namespace {

// Formats and layouts are resolved here, not in the parser: a '?' is a
// statement about the search space, which is semantic information.
KvFormat resolveFormat(const KvDecl &d, int head_dim, bool &free_out) {
  KvFormat f;
  const Format parsed = parseFormat(d.fmt);
  free_out = parsed == Format::Unset;
  if (free_out)
    return f; // value unused while free
  f.fmt = parsed;
  if (f.isQuantized()) {
    f.group = d.fmt_group > 0 ? d.fmt_group : 128;
    f.metadata_bits = 32; // fp16 scale + fp16 zero point
    if (f.group != 32 && f.group != 64 && f.group != 128)
      throw std::runtime_error("quantization group must be 32, 64 or 128");
    if (f.group > head_dim || head_dim % f.group != 0)
      throw std::runtime_error("quantization group must divide d");
  } else {
    f.group = 0;
    f.metadata_bits = 0;
  }
  return f;
}

KvLayout resolveLayout(const KvDecl &d, bool &free_out) {
  KvLayout l;
  const Order o = parseOrder(d.order);
  const Residency r = parseResidency(d.residency);
  free_out = o == Order::Unset || r == Residency::Unset;
  if (free_out)
    return l;
  l.order = o;
  l.residency = r;
  l.block_tokens =
      r == Residency::Paged ? (d.block_tokens > 0 ? d.block_tokens : 64) : 0;
  if (r == Residency::Paged && l.block_tokens != 16 && l.block_tokens != 32 &&
      l.block_tokens != 64 && l.block_tokens != 128)
    throw std::runtime_error("paged block size must be 16, 32, 64 or 128");
  return l;
}

const KvDecl *findCache(const DecodeFn &fn, const std::string &name) {
  for (const auto &c : fn.caches)
    if (c.name == name)
      return &c;
  return nullptr;
}

} // namespace

Module importAst(const Program &p) {
  Module m;
  const DecodeFn &fn = p.fn;

  m.spec.name = fn.name;
  m.spec.H = fn.H;
  m.spec.H_kv = fn.H_kv;
  m.spec.d = fn.d;
  m.spec.n = fn.n;
  m.spec.batch = fn.batch;
  m.machine = Machine::defaults();
  m.calib = Calib::defaults();

  // Target keys name a machine or calibration file, set a search option, or
  // override one machine key.
  for (const auto &t : p.targets) {
    if (t.key == "machine") {
      if (!t.is_text)
        throw std::runtime_error("target machine must be a quoted path");
      m.machine_file = t.text;
      m.machine = loadMachine(std::filesystem::path(t.text));
    } else if (t.key == "calib") {
      if (!t.is_text)
        throw std::runtime_error("target calib must be a quoted path");
      m.calib_file = t.text;
      m.calib = loadCalib(std::filesystem::path(t.text));
    } else if (t.key == "include_quantized") {
      m.space.include_quantized = t.value != 0;
    } else if (t.key == "max_splits") {
      m.space.max_splits = static_cast<int>(t.value);
    } else if (t.key == "max_rel_err") {
      m.space.max_rel_err = t.value;
    } else {
      applyMachineKey(m.machine, t.key, t.value, t.text);
    }
  }
  // A stated accuracy budget is what permits lossy formats.
  if (m.space.max_rel_err > 0)
    m.space.include_quantized = true;

  if (m.spec.H <= 0 || m.spec.H_kv <= 0 || m.spec.d <= 0 || m.spec.n <= 0)
    throw std::runtime_error("H, H_kv, d and n must be positive");
  if (m.spec.H % m.spec.H_kv != 0)
    throw std::runtime_error("H must be a multiple of H_kv (GQA group size)");
  if (m.spec.d != 64 && m.spec.d != 128)
    throw std::runtime_error("the kernels support d = 64 or d = 128");
  if (m.spec.batch < 1)
    throw std::runtime_error("batch must be >= 1");
  if (m.machine.sms < 1)
    throw std::runtime_error("sms must be >= 1");
  if (m.machine.bw_peak_gbs <= 0 || m.machine.bw_sm_gbs <= 0)
    throw std::runtime_error("bandwidth parameters must be positive");

  const KvDecl *kd = findCache(fn, fn.attn.k);
  const KvDecl *vd = findCache(fn, fn.attn.v);
  if (!kd || !vd)
    throw std::runtime_error("decode_attn names a cache that was not declared");
  if (fn.attn.q != fn.query.name)
    throw std::runtime_error("decode_attn names an undeclared query '" +
                             fn.attn.q + "'");
  if (fn.query.rows != "H" || fn.query.cols != "d")
    throw std::runtime_error("query must be declared as query<H, d, f32>");
  if (fn.query.dtype != "f32")
    throw std::runtime_error("only f32 queries are supported");

  bool kf_free = false, vf_free = false, kl_free = false, vl_free = false;
  const KvFormat kf = resolveFormat(*kd, m.spec.d, kf_free);
  const KvFormat vf = resolveFormat(*vd, m.spec.d, vf_free);
  const KvLayout kl = resolveLayout(*kd, kl_free);
  const KvLayout vl = resolveLayout(*vd, vl_free);

  // This release keeps K and V on the same format and layout, so a program is
  // rejected rather than silently half-honoured.
  if (kf_free != vf_free)
    throw std::runtime_error(
        "K and V must both pin a format or both leave it '?'");
  if (kl_free != vl_free)
    throw std::runtime_error(
        "K and V must both pin a layout or both leave it '?'");
  if (!kf_free && kf.str() != vf.str())
    throw std::runtime_error("K and V formats must match in this release");
  if (!kl_free && kl.str() != vl.str())
    throw std::runtime_error("K and V layouts must match in this release");

  m.space.format_free = kf_free;
  m.space.layout_free = kl_free;
  m.space.pinned_fmt = kf;
  m.space.pinned_layout = kl;

  // Splits and GQA packing are independent: pinning one never frees or ignores
  // the other.
  m.space.splits_free = fn.attn.splits == 0;
  m.space.pack_free = !fn.attn.gqa_pack_set;
  m.space.pinned_splits = fn.attn.splits > 0 ? fn.attn.splits : 1;
  m.space.pinned_pack = fn.attn.gqa_pack;
  const int g = m.spec.g();
  if (!m.space.pack_free && m.space.pinned_pack && g != 2 && g != 4 && g != 8)
    throw std::runtime_error(
        "gqa_pack = true needs a group size of 2, 4 or 8 query heads per KV head");

  ValueType qt;
  qt.kind = ValueKind::Dense;
  qt.rows = m.spec.H;
  qt.cols = m.spec.d;
  const int qid = m.addValue(fn.query.name, qt);
  Operation qop;
  qop.kind = OpKind::Query;
  qop.result = qid;
  m.ops.push_back(qop);

  std::unordered_map<std::string, int> ids;
  for (const auto &c : fn.caches) {
    ValueType ct;
    ct.kind = ValueKind::KvCache;
    ct.rows = m.spec.n;
    ct.cols = m.spec.d;
    bool unused = false;
    ct.fmt = resolveFormat(c, m.spec.d, unused);
    if (unused)
      ct.fmt.fmt = Format::Unset;
    ct.layout = resolveLayout(c, unused);
    if (unused) {
      ct.layout.order = Order::Unset;
      ct.layout.residency = Residency::Unset;
    }
    const int id = m.addValue(c.name, ct);
    ids[c.name] = id;
    Operation op;
    op.kind = OpKind::KvCache;
    op.result = id;
    m.ops.push_back(op);
  }

  ValueType ot;
  ot.kind = ValueKind::Dense;
  ot.rows = m.spec.H;
  ot.cols = m.spec.d;
  const int oid = m.addValue(fn.attn.out, ot);

  Operation attn;
  attn.kind = OpKind::DecodeAttn;
  attn.operands = {qid, ids[fn.attn.k], ids[fn.attn.v]};
  attn.result = oid;
  attn.scale = fn.attn.scale_auto
                   ? 1.0f / std::sqrt(static_cast<float>(m.spec.d))
                   : static_cast<float>(fn.attn.scale);
  m.ops.push_back(attn);
  m.spec.scale = attn.scale;

  Operation out;
  out.kind = OpKind::Output;
  out.operands = {oid};
  m.ops.push_back(out);
  return m;
}

namespace {

const char *opName(OpKind k) {
  switch (k) {
  case OpKind::Query:
    return "kvf.query";
  case OpKind::KvCache:
    return "kvf.kvcache";
  case OpKind::DecodeAttn:
    return "kvf.decode_attn";
  case OpKind::PlannedAttn:
    return "kvf.decode_attn_split";
  case OpKind::Output:
    return "kvf.output";
  }
  return "kvf.unknown";
}

} // namespace

std::string dumpModule(const Module &m) {
  std::ostringstream o;
  o << "module {\n";
  o << "  func @" << m.spec.name << "()  // H=" << m.spec.H
    << " H_kv=" << m.spec.H_kv << " g=" << m.spec.g() << " d=" << m.spec.d
    << " n=" << m.spec.n << " batch=" << m.spec.batch << "\n";
  o << "  {\n";
  for (const auto &op : m.ops) {
    o << "    ";
    if (op.result >= 0)
      o << '%' << m.v(op.result).name << " = ";
    o << opName(op.kind);
    for (std::size_t i = 0; i < op.operands.size(); ++i)
      o << (i ? ", " : " ") << '%' << m.v(op.operands[i]).name;
    if (op.result >= 0)
      o << " : " << m.v(op.result).type.str();
    else if (!op.operands.empty())
      o << " : " << m.v(op.operands[0]).type.str();
    if (op.kind == OpKind::DecodeAttn || op.kind == OpKind::PlannedAttn) {
      o << " {scale = " << op.scale;
      if (op.planned) {
        o << ", format = " << op.plan.fmt.str()
          << ", layout = " << op.plan.layout.str()
          << ", splits = " << op.plan.part.splits
          << ", gqa_pack = " << (op.plan.part.gqa_pack ? "true" : "false")
          << ", warps = " << op.plan.part.warps
          << ", unroll = " << op.plan.part.unroll
          << ", blocks = " << op.cost.blocks
          << ", pred_us = " << op.cost.t_total_us
          << ", pred_gbs = " << op.cost.achieved_gbs;
      }
      o << '}';
    }
    o << '\n';
  }
  o << "  }\n}\n";
  return o.str();
}

} // namespace kvf
