#include "kvf/plan.h"

#include <algorithm>
#include <sstream>

namespace kvf {

std::string Partition::str() const {
  std::ostringstream o;
  o << "splits=" << splits << (gqa_pack ? " pack" : "") << " w" << warps << " u"
    << unroll;
  return o.str();
}

std::string Plan::str() const {
  std::ostringstream o;
  o << fmt.str() << " | " << layout.str() << " | " << part.str();
  return o.str();
}

namespace {

// Split counts worth trying: powers of two up to a cap. A chunk shorter than
// min_chunk_tokens is dominated by its own merge overhead, so those are dropped.
std::vector<int> candidateSplits(const DecodeSpec &s, int max_splits) {
  const int cap = max_splits > 0 ? max_splits : 64;
  const int min_chunk_tokens = 128;
  std::vector<int> out;
  for (int v = 1; v <= cap; v *= 2)
    if (v == 1 || s.n / v >= min_chunk_tokens)
      out.push_back(v);
  return out;
}

} // namespace

std::vector<Plan> enumeratePlans(const DecodeSpec &s, const Machine &,
                                 const SearchSpace &sp) {
  std::vector<KvFormat> formats;
  if (sp.format_free)
    formats = candidateFormats(s.d, sp.include_quantized);
  else
    formats.push_back(sp.pinned_fmt);

  std::vector<KvLayout> layouts;
  if (sp.layout_free)
    layouts = candidateLayouts();
  else
    layouts.push_back(sp.pinned_layout);

  // The kernels pack groups of 2, 4 or 8 query heads per KV head.
  const int g = s.g();
  const bool can_pack = g == 2 || g == 4 || g == 8;
  std::vector<bool> packing;
  if (sp.pack_free) {
    packing.push_back(false);
    if (can_pack)
      packing.push_back(true);
  } else {
    packing.push_back(sp.pinned_pack);
  }

  std::vector<int> splits;
  if (sp.splits_free)
    splits = candidateSplits(s, sp.max_splits);
  else
    splits.push_back(sp.pinned_splits);

  std::vector<Plan> out;
  for (const auto &f : formats)
    for (const auto &l : layouts)
      for (bool pack : packing)
        for (int sv : splits)
          for (int w : sp.warps_cand)
            for (int u : sp.unroll_cand) {
              Plan p;
              p.fmt = f;
              p.layout = l;
              p.part.splits = sv;
              p.part.gqa_pack = pack;
              p.part.warps = w;
              p.part.unroll = u;
              out.push_back(p);
            }
  return out;
}

} // namespace kvf
