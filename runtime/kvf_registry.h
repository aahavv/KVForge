// kvf_registry.h - maps a variant id to the launcher of that instantiation.
//
// The compiler emits dispatch sources whose registration functions fill this
// table, so the sweep harness times kernels that code generation produced,
// not hand-written copies.
#pragma once

#include "kvf_kernels.cuh"

#include <string>
#include <unordered_map>

namespace kvf {

using LaunchFn = cudaError_t (*)(const Args &, cudaStream_t);

struct Registry {
  std::unordered_map<std::string, LaunchFn> fn;
  void add(const char *id, LaunchFn f) { fn[id] = f; }
  LaunchFn find(const std::string &id) const {
    const auto it = fn.find(id);
    return it == fn.end() ? nullptr : it->second;
  }
};

} // namespace kvf

// Defined in the generated kvf_dispatch.cu.
void kvf_register_all(kvf::Registry &r);
