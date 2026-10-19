// kvf_host.h - host-side support shared by the sweep harness and the generated
// benchmark driver: test data, quantization, layout placement, the fp32
// reference attention, and timing.
#pragma once

#include "kvf_kernels.cuh"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <numeric>
#include <random>
#include <string>
#include <vector>

#define KVF_CUDA_CHECK(call)                                                   \
  do {                                                                         \
    cudaError_t e__ = (call);                                                  \
    if (e__ != cudaSuccess) {                                                  \
      std::fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(e__), \
                   __FILE__, __LINE__);                                        \
      std::exit(1);                                                            \
    }                                                                          \
  } while (0)

namespace kvf {

struct Shape {
  int B = 1, H = 32, Hkv = 8, D = 128, n = 4096;
  int g() const { return H / Hkv; }
  long long rows() const { return 1LL * B * Hkv * n; }
};

struct LayoutSel {
  int order = ORD_HEAD; // ORD_HEAD or ORD_TOKEN
  bool paged = false;
  int bt = 0; // tokens per page when paged
};

struct FormatSel {
  int fmt = FMT_F16;
  int group = 0;
  int bits() const { return fmt == FMT_F16 ? 16 : fmt == FMT_INT8 ? 8 : 4; }
  int rowBytes(int D) const { return D * bits() / 8; }
  int groupsPerRow(int D) const { return fmt == FMT_F16 ? 0 : D / group; }
};

// ---------------------------------------------------------------- test data
inline void make_data(const Shape &s, uint64_t seed, std::vector<float> &q,
                      std::vector<float> &K, std::vector<float> &V) {
  std::mt19937_64 rng(seed);
  std::normal_distribution<float> nd(0.f, 1.f);
  q.resize((size_t)s.B * s.H * s.D);
  K.resize((size_t)s.rows() * s.D);
  V.resize((size_t)s.rows() * s.D);
  for (auto &x : q) x = nd(rng);
  for (auto &x : K) x = nd(rng);
  for (auto &x : V) x = nd(rng);
}

// ---------------------------------------------------------------- quantize
// Rows are in logical order ((b*Hkv + h)*n + t). Quantization groups run along
// the head dimension inside one row.
struct Quantized {
  std::vector<unsigned char> data; // rows * rowBytes
  std::vector<__half2> meta;       // rows * groupsPerRow (scale, zero)
  std::vector<float> deq;          // dequantised values, logical order
};

inline Quantized quantize(const FormatSel &f, int D, const std::vector<float> &X,
                          long long rows) {
  Quantized out;
  const int rb = f.rowBytes(D);
  out.data.assign((size_t)rows * rb, 0);
  out.deq.resize(X.size());
  if (f.fmt == FMT_F16) {
    for (size_t i = 0; i < X.size(); ++i) {
      const __half h = __float2half(X[i]);
      std::memcpy(out.data.data() + i * 2, &h, 2);
      out.deq[i] = __half2float(h);
    }
    return out;
  }
  const int gpr = f.groupsPerRow(D);
  const int levels = f.fmt == FMT_INT8 ? 255 : 15;
  out.meta.resize((size_t)rows * gpr);
  for (long long r = 0; r < rows; ++r) {
    for (int gi = 0; gi < gpr; ++gi) {
      const float *x = &X[(size_t)r * D + (size_t)gi * f.group];
      float lo = x[0], hi = x[0];
      for (int i = 1; i < f.group; ++i) {
        lo = std::min(lo, x[i]);
        hi = std::max(hi, x[i]);
      }
      // Use the fp16-rounded scale and zero, exactly as the kernel will.
      const __half zero_h = __float2half(lo);
      float scale = (hi - lo) / levels;
      if (scale <= 0.f) scale = 1.f;
      const __half scale_h = __float2half(scale);
      const float zero = __half2float(zero_h);
      const float sc = __half2float(scale_h);
      out.meta[(size_t)r * gpr + gi] = __halves2half2(scale_h, zero_h);
      for (int i = 0; i < f.group; ++i) {
        const int col = gi * f.group + i;
        int qv = (int)std::lround((x[i] - zero) / sc);
        qv = std::min(std::max(qv, 0), levels);
        out.deq[(size_t)r * D + col] = qv * sc + zero;
        if (f.fmt == FMT_INT8) {
          out.data[(size_t)r * rb + col] = (unsigned char)qv;
        } else {
          unsigned char &byte = out.data[(size_t)r * rb + col / 2];
          byte = (col & 1) ? (unsigned char)((byte & 0x0F) | (qv << 4))
                           : (unsigned char)((byte & 0xF0) | qv);
        }
      }
    }
  }
  return out;
}

// ---------------------------------------------------------------- placement
inline long long host_row_of(const Shape &s, const LayoutSel &l, const int *table,
                             int max_blocks, int b, int h, int t) {
  if (!l.paged) {
    return l.order == ORD_HEAD ? ((long long)b * s.Hkv + h) * s.n + t
                               : ((long long)b * s.n + t) * s.Hkv + h;
  }
  const int blk = t / l.bt, tl = t % l.bt;
  const long long page = table[(long long)b * max_blocks + blk];
  const long long base = page * s.Hkv * l.bt;
  return l.order == ORD_HEAD ? base + (long long)h * l.bt + tl
                             : base + (long long)tl * s.Hkv + h;
}

struct Cache {
  unsigned char *k = nullptr, *v = nullptr;
  __half2 *km = nullptr, *vm = nullptr;
  int *table = nullptr;
  int max_blocks = 0;
  size_t bytes = 0;
  void release() {
    cudaFree(k); cudaFree(v); cudaFree(km); cudaFree(vm); cudaFree(table);
    k = v = nullptr; km = vm = nullptr; table = nullptr;
  }
};

inline Cache upload_cache(const Shape &s, const FormatSel &f, const LayoutSel &l,
                          const Quantized &Kq, const Quantized &Vq, uint64_t seed) {
  Cache c;
  const int rb = f.rowBytes(s.D);
  const int gpr = f.groupsPerRow(s.D);
  std::vector<int> table;
  long long rows_alloc = s.rows();
  if (l.paged) {
    c.max_blocks = (s.n + l.bt - 1) / l.bt;
    const long long pages = 1LL * s.B * c.max_blocks;
    std::vector<int> perm(pages);
    std::iota(perm.begin(), perm.end(), 0);
    std::mt19937_64 rng(seed);
    std::shuffle(perm.begin(), perm.end(), rng); // pages are not in order
    table = perm;
    rows_alloc = pages * s.Hkv * l.bt;
  }
  std::vector<unsigned char> kd((size_t)rows_alloc * rb), vd((size_t)rows_alloc * rb);
  std::vector<__half2> km, vm;
  if (gpr) {
    km.resize((size_t)rows_alloc * gpr);
    vm.resize((size_t)rows_alloc * gpr);
  }
  for (int b = 0; b < s.B; ++b)
    for (int h = 0; h < s.Hkv; ++h)
      for (int t = 0; t < s.n; ++t) {
        const long long lr = ((long long)b * s.Hkv + h) * s.n + t;
        const long long pr =
            host_row_of(s, l, table.data(), c.max_blocks, b, h, t);
        std::memcpy(&kd[(size_t)pr * rb], &Kq.data[(size_t)lr * rb], rb);
        std::memcpy(&vd[(size_t)pr * rb], &Vq.data[(size_t)lr * rb], rb);
        if (gpr) {
          std::memcpy(&km[(size_t)pr * gpr], &Kq.meta[(size_t)lr * gpr], gpr * 4);
          std::memcpy(&vm[(size_t)pr * gpr], &Vq.meta[(size_t)lr * gpr], gpr * 4);
        }
      }
  auto up = [&](void **dst, const void *src, size_t n) {
    if (!n) { *dst = nullptr; return; }
    KVF_CUDA_CHECK(cudaMalloc(dst, n));
    KVF_CUDA_CHECK(cudaMemcpy(*dst, src, n, cudaMemcpyHostToDevice));
    c.bytes += n;
  };
  up((void **)&c.k, kd.data(), kd.size());
  up((void **)&c.v, vd.data(), vd.size());
  up((void **)&c.km, km.data(), km.size() * 4);
  up((void **)&c.vm, vm.data(), vm.size() * 4);
  up((void **)&c.table, table.data(), table.size() * 4);
  return c;
}

// ---------------------------------------------------------------- reference
// Exact attention in double precision over the given (already dequantised)
// logical K and V.
inline std::vector<float> reference_attention(const Shape &s,
                                              const std::vector<float> &q,
                                              const std::vector<float> &K,
                                              const std::vector<float> &V,
                                              float scale) {
  std::vector<float> out((size_t)s.B * s.H * s.D);
  const int gq = s.H / s.Hkv;
  std::vector<double> sc(s.n), acc(s.D);
  for (int b = 0; b < s.B; ++b)
    for (int h = 0; h < s.H; ++h) {
      const int hk = h / gq;
      const float *qh = &q[((size_t)b * s.H + h) * s.D];
      double mx = -1e300;
      for (int t = 0; t < s.n; ++t) {
        const float *k = &K[(((size_t)b * s.Hkv + hk) * s.n + t) * s.D];
        double d = 0;
        for (int c = 0; c < s.D; ++c) d += (double)qh[c] * k[c];
        sc[t] = d * scale;
        mx = std::max(mx, sc[t]);
      }
      double sum = 0;
      std::fill(acc.begin(), acc.end(), 0.0);
      for (int t = 0; t < s.n; ++t) {
        const double p = std::exp(sc[t] - mx);
        sum += p;
        const float *v = &V[(((size_t)b * s.Hkv + hk) * s.n + t) * s.D];
        for (int c = 0; c < s.D; ++c) acc[c] += p * v[c];
      }
      for (int c = 0; c < s.D; ++c)
        out[((size_t)b * s.H + h) * s.D + c] = (float)(acc[c] / sum);
    }
  return out;
}

inline double rel_l2(const std::vector<float> &a, const std::vector<float> &ref) {
  double num = 0, den = 0;
  for (size_t i = 0; i < a.size(); ++i) {
    const double d = (double)a[i] - ref[i];
    num += d * d;
    den += (double)ref[i] * ref[i];
  }
  return den > 0 ? std::sqrt(num / den) : 0;
}

// ---------------------------------------------------------------- run setup
struct DeviceBuffers {
  float *q = nullptr, *out = nullptr, *part_o = nullptr, *part_ml = nullptr;
  void *flush = nullptr;
  size_t flush_bytes = 0;
};

inline DeviceBuffers alloc_buffers(const Shape &s, int max_splits,
                                   size_t flush_bytes,
                                   const std::vector<float> &q) {
  DeviceBuffers d;
  KVF_CUDA_CHECK(cudaMalloc(&d.q, q.size() * 4));
  KVF_CUDA_CHECK(cudaMemcpy(d.q, q.data(), q.size() * 4, cudaMemcpyHostToDevice));
  KVF_CUDA_CHECK(cudaMalloc(&d.out, (size_t)s.B * s.H * s.D * 4));
  KVF_CUDA_CHECK(
      cudaMalloc(&d.part_o, (size_t)s.B * s.H * max_splits * s.D * 4));
  KVF_CUDA_CHECK(cudaMalloc(&d.part_ml, (size_t)s.B * s.H * max_splits * 2 * 4));
  d.flush_bytes = flush_bytes;
  KVF_CUDA_CHECK(cudaMalloc(&d.flush, flush_bytes));
  return d;
}

inline void free_buffers(DeviceBuffers &d) {
  cudaFree(d.q); cudaFree(d.out); cudaFree(d.part_o); cudaFree(d.part_ml);
  cudaFree(d.flush);
}

inline Args make_args(const Shape &s, const FormatSel &f, const LayoutSel &l,
                      const Cache &c, const DeviceBuffers &d, int splits,
                      int warps) {
  Args a{};
  a.q = d.q;
  a.k = c.k;
  a.v = c.v;
  a.k_meta = c.km;
  a.v_meta = c.vm;
  a.block_table = c.table;
  a.out = d.out;
  a.part_o = d.part_o;
  a.part_ml = d.part_ml;
  a.B = s.B; a.H = s.H; a.Hkv = s.Hkv; a.n = s.n;
  a.splits = splits;
  a.warps = warps;
  a.group_shift = f.fmt == FMT_F16 ? 0 : (int)std::lround(std::log2((double)f.group));
  a.block_shift = l.paged ? (int)std::lround(std::log2((double)l.bt)) : 0;
  a.max_blocks = c.max_blocks;
  a.scale_log2 = (1.0f / std::sqrt((float)s.D)) * 1.4426950408889634f;
  return a;
}

// ---------------------------------------------------------------- timing
struct TimeStats {
  double median = 0, p25 = 0, p75 = 0, min = 0;
  int reps = 0;
};

template <class Launch>
TimeStats time_launch(Launch &&launch, const DeviceBuffers &d, int warmup,
                      int reps) {
  cudaEvent_t e0, e1;
  KVF_CUDA_CHECK(cudaEventCreate(&e0));
  KVF_CUDA_CHECK(cudaEventCreate(&e1));
  std::vector<double> t;
  for (int i = 0; i < warmup + reps; ++i) {
    // Evict the cache so every repetition reads from DRAM, as a real decode
    // step does after the rest of the layer has run.
    KVF_CUDA_CHECK(cudaMemsetAsync(d.flush, i & 0xFF, d.flush_bytes, 0));
    KVF_CUDA_CHECK(cudaEventRecord(e0, 0));
    launch();
    KVF_CUDA_CHECK(cudaEventRecord(e1, 0));
    KVF_CUDA_CHECK(cudaEventSynchronize(e1));
    float ms = 0;
    KVF_CUDA_CHECK(cudaEventElapsedTime(&ms, e0, e1));
    if (i >= warmup) t.push_back(ms * 1000.0);
  }
  cudaEventDestroy(e0);
  cudaEventDestroy(e1);
  std::sort(t.begin(), t.end());
  TimeStats s;
  s.reps = (int)t.size();
  s.min = t.front();
  s.median = t[t.size() / 2];
  s.p25 = t[t.size() / 4];
  s.p75 = t[(3 * t.size()) / 4];
  return s;
}

} // namespace kvf
