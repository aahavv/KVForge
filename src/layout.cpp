#include "kvf/layout.h"

#include <sstream>
#include <stdexcept>

namespace kvf {

const char *orderName(Order o) {
  switch (o) {
  case Order::HeadMajor:
    return "head_major";
  case Order::TokenMajor:
    return "token_major";
  case Order::Unset:
    return "?";
  }
  return "?";
}

const char *residencyName(Residency r) {
  switch (r) {
  case Residency::Contiguous:
    return "contiguous";
  case Residency::Paged:
    return "paged";
  case Residency::Unset:
    return "?";
  }
  return "?";
}

Order parseOrder(const std::string &s) {
  if (s == "head_major")
    return Order::HeadMajor;
  if (s == "token_major")
    return Order::TokenMajor;
  if (s == "?")
    return Order::Unset;
  throw std::runtime_error("unknown KV order '" + s +
                           "' (head_major, token_major, ?)");
}

Residency parseResidency(const std::string &s) {
  if (s == "contiguous")
    return Residency::Contiguous;
  if (s == "paged")
    return Residency::Paged;
  if (s == "?")
    return Residency::Unset;
  throw std::runtime_error("unknown KV residency '" + s +
                           "' (contiguous, paged, ?)");
}

std::string KvLayout::str() const {
  std::ostringstream o;
  o << orderName(order) << "/" << residencyName(residency);
  if (residency == Residency::Paged && block_tokens > 0)
    o << ":" << block_tokens;
  return o.str();
}

std::vector<KvLayout> candidateLayouts() {
  std::vector<KvLayout> out;
  auto add = [&](Order o, Residency r, int block) {
    KvLayout l;
    l.order = o;
    l.residency = r;
    l.block_tokens = block;
    out.push_back(l);
  };
  add(Order::HeadMajor, Residency::Contiguous, 0);
  add(Order::TokenMajor, Residency::Contiguous, 0);
  for (int b : {16, 32, 64, 128})
    add(Order::HeadMajor, Residency::Paged, b);
  for (int b : {16, 64})
    add(Order::TokenMajor, Residency::Paged, b);
  return out;
}

} // namespace kvf
