#pragma once

#include "kvf/format.h"
#include "kvf/layout.h"
#include "kvf/machine.h"
#include "kvf/spec.h"

#include <string>
#include <vector>

namespace kvf {

// How the KV scan is cut into parallel work and scheduled on one SM.
struct Partition {
  int splits = 1;        // chunks of the KV length per head (split-KV)
  bool gqa_pack = false; // one block serves all g query heads of a KV group, so
                         // K/V for that group is loaded once instead of g times
  int warps = 4;         // warps per block
  int unroll = 2;        // tokens a lane group keeps in flight per step
  std::string str() const;
};

// One candidate kernel. K and V share a format and layout in this release.
struct Plan {
  KvFormat fmt;
  KvLayout layout;
  Partition part;
  std::string str() const;
};

// Free dimensions: anything the DSL left as '?' is searched, anything written
// concretely is pinned. Splits and GQA packing are tracked separately, so
// pinning one never silently frees or ignores the other.
struct SearchSpace {
  bool format_free = true;
  bool layout_free = true;
  bool splits_free = true;
  bool pack_free = true;
  bool include_quantized = false;
  int max_splits = 0; // 0 = default cap (64)
  KvFormat pinned_fmt;
  KvLayout pinned_layout;
  int pinned_splits = 1;
  bool pinned_pack = false;

  // Scheduling knobs the compiler always searches.
  std::vector<int> warps_cand{4, 8};
  std::vector<int> unroll_cand{2, 4};

  // Accuracy gate: plans whose measured relative error exceeds this are
  // rejected. 0 means no gate (every format is eligible).
  double max_rel_err = 0.0;
};

std::vector<Plan> enumeratePlans(const DecodeSpec &s, const Machine &m,
                                 const SearchSpace &sp);

} // namespace kvf
