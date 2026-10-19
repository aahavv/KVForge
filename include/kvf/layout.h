#pragma once

#include <string>
#include <vector>

namespace kvf {

// How the cached rows are ordered in GPU memory. A "row" is one token's d
// channels for one KV head, so it is always contiguous.
//
// HeadMajor  K[b][h][t][c]: for one KV head, consecutive tokens are adjacent.
//            A block scanning one head streams one long run.
// TokenMajor K[b][t][h][c]: the layout a model naturally produces, appending one
//            token for every head at a time. A block scanning one head sees runs
//            of a single row, then a jump of H_kv rows.
enum class Order { HeadMajor, TokenMajor, Unset };

// Contiguous: one flat region per sequence.
// Paged: fixed-size blocks of `block_tokens` tokens, reached through a block
//        table (one dependent load per block, as in vLLM-style allocators).
enum class Residency { Contiguous, Paged, Unset };

struct KvLayout {
  Order order = Order::HeadMajor;
  Residency residency = Residency::Contiguous;
  int block_tokens = 0; // tokens per page, Paged only

  bool paged() const { return residency == Residency::Paged; }
  std::string str() const;
};

Order parseOrder(const std::string &s);
Residency parseResidency(const std::string &s);
const char *orderName(Order o);
const char *residencyName(Residency r);

std::vector<KvLayout> candidateLayouts();

} // namespace kvf
