#pragma once

#include <string>
#include <vector>

namespace kvf {

// Parse tree for the .kv specification language. Format, layout and
// partitioning fields are kept as written, including the literal "?" that marks
// a dimension the compiler is free to choose; resolving them is a semantic
// step, not a parsing one.

struct TargetDecl {
  std::string key;
  double value = 0;
  std::string text; // quoted value, for `target machine = "..."`
  bool is_text = false;
  int line = 1;
};

struct KvDecl {
  std::string name;      // K or V
  std::string rows;      // "n" or a literal
  std::string cols;      // "d" or a literal
  std::string fmt = "?";
  int fmt_group = 0;     // int4:128 -> 128
  std::string order = "?";
  int channel_block = 0; // channel_major:32 -> 32
  std::string residency = "?";
  int block_tokens = 0;  // paged:64 -> 64
  int line = 1;
};

struct QueryDecl {
  std::string name;
  std::string rows = "H";
  std::string cols = "d";
  std::string dtype = "f32";
  int line = 1;
};

struct AttnStmt {
  std::string out, q, k, v;
  bool scale_auto = true;
  double scale = 0;
  int splits = 0;        // 0 means not written: free
  bool gqa_pack = false;
  bool gqa_pack_set = false;
  int line = 1;
};

struct DecodeFn {
  std::string name;
  int H = 0, H_kv = 0, d = 0, n = 0, batch = 1;
  std::vector<KvDecl> caches;
  QueryDecl query;
  AttnStmt attn;
  int line = 1;
};

struct Program {
  std::vector<TargetDecl> targets;
  DecodeFn fn;
};

} // namespace kvf
