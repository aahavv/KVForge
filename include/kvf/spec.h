#pragma once

#include <string>

namespace kvf {

// Shape of one decode step for one attention layer.
//
// Decode generates one token at a time, so the query is a single vector per
// head. The KV cache holds n past tokens and is re-read in full every step.
struct DecodeSpec {
  std::string name = "decode";
  int H = 32;      // query heads
  int H_kv = 32;   // key/value heads (H_kv == H is MHA, H_kv < H is GQA)
  int d = 128;     // head dimension (64 or 128 are supported by the kernels)
  int n = 4096;    // context length (cached tokens)
  int batch = 1;   // independent sequences decoded together
  float scale = 0; // 0 means 1/sqrt(d)

  // GQA group size: how many query heads share one K/V head.
  int g() const { return H_kv > 0 ? H / H_kv : 1; }
};

} // namespace kvf
