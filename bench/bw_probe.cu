// bw_probe - measure the machine parameters the KVForge cost model depends on.
//
// The cost model is written in terms of quantities a GPU can be asked for
// directly, so none of them is taken from a datasheet:
//
//   bw_peak_gbs   sustained DRAM read bandwidth, every SM
//   bw_sm_gbs     sustained read bandwidth of ONE SM with ample warps in flight
//   lat_ns        DRAM load-to-use latency (dependent pointer chase)
//   bw_l2_gbs     read bandwidth of a working set that fits in L2
//   f32_gflops    sustained FP32 FMA throughput
//   launch_us     event-measured duration of an empty kernel
//   sector_bytes  memory transaction granularity, from a strided-read test
//
// The kernels are pure streaming reads, because that is what decode attention
// does to the KV cache: touch every byte once, in order, never come back.
//
//   bw_probe [--name NAME] [--out machines/this.gpu] [--device N]
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <numeric>
#include <random>
#include <string>
#include <vector>

#include <cuda_runtime.h>

#define CK(call)                                                               \
  do {                                                                         \
    cudaError_t e__ = (call);                                                  \
    if (e__ != cudaSuccess) {                                                  \
      std::fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(e__), \
                   __FILE__, __LINE__);                                        \
      std::exit(1);                                                            \
    }                                                                          \
  } while (0)

// ------------------------------------------------------------------ kernels
// Grid-stride sum of 16-byte loads; the xor is a sink so the loads are kept.
// Each thread keeps UNROLL independent loads in flight.
template <int UNROLL>
__global__ void stream_read(const uint4 *__restrict__ p, size_t n_vec, unsigned *sink) {
  unsigned acc = 0;
  const size_t stride = (size_t)gridDim.x * blockDim.x;
  size_t i = (size_t)blockIdx.x * blockDim.x + threadIdx.x;
  for (; i + (UNROLL - 1) * stride < n_vec; i += UNROLL * stride) {
    uint4 v[UNROLL];
#pragma unroll
    for (int u = 0; u < UNROLL; ++u) v[u] = __ldcs(p + i + (size_t)u * stride);
#pragma unroll
    for (int u = 0; u < UNROLL; ++u) acc ^= v[u].x ^ v[u].y ^ v[u].z ^ v[u].w;
  }
  if (acc == 0x9e3779b9u) *sink = acc; // practically never true
}

// One thread chases a random cycle of cache-line-sized slots.
__global__ void chase(const unsigned *next, unsigned start, int steps, unsigned *out) {
  unsigned i = start;
  for (int s = 0; s < steps; ++s) i = next[(size_t)i * 32]; // 32 x 4 B = one 128 B line
  *out = i;
}

// Repeated reads of a small region, to measure L2 rather than DRAM.
__global__ void l2_read(const uint4 *__restrict__ p, size_t n_vec, int passes, unsigned *sink) {
  unsigned acc = 0;
  const size_t stride = (size_t)gridDim.x * blockDim.x;
  for (int r = 0; r < passes; ++r)
    for (size_t i = (size_t)blockIdx.x * blockDim.x + threadIdx.x; i < n_vec; i += stride) {
      const uint4 v = __ldcg(p + i); // cache at L2, skip L1
      acc ^= v.x ^ v.y ^ v.z ^ v.w;
    }
  if (acc == 0x9e3779b9u) *sink = acc;
}

// Eight independent FMA chains per thread.
__global__ void fma_chain(float *out, int iters) {
  float a0 = threadIdx.x, a1 = a0 + 1, a2 = a0 + 2, a3 = a0 + 3;
  float a4 = a0 + 4, a5 = a0 + 5, a6 = a0 + 6, a7 = a0 + 7;
  const float m = 1.0000001f, c = 1e-7f;
  for (int i = 0; i < iters; ++i) {
    a0 = fmaf(a0, m, c); a1 = fmaf(a1, m, c); a2 = fmaf(a2, m, c); a3 = fmaf(a3, m, c);
    a4 = fmaf(a4, m, c); a5 = fmaf(a5, m, c); a6 = fmaf(a6, m, c); a7 = fmaf(a7, m, c);
  }
  out[blockIdx.x * blockDim.x + threadIdx.x] = a0 + a1 + a2 + a3 + a4 + a5 + a6 + a7;
}

__global__ void empty_kernel() {}

// 4-byte reads at a byte stride: the time per access grows with the number of
// distinct memory sectors touched, and stops growing once each access owns one.
__global__ void stride_read(const char *p, size_t n_access, int stride, unsigned *sink) {
  unsigned acc = 0;
  const size_t step = (size_t)gridDim.x * blockDim.x;
  for (size_t i = (size_t)blockIdx.x * blockDim.x + threadIdx.x; i < n_access; i += step)
    acc ^= __ldcs(reinterpret_cast<const unsigned *>(p + i * (size_t)stride));
  if (acc == 0x9e3779b9u) *sink = acc;
}

// ------------------------------------------------------------------ helpers
struct Timer {
  cudaEvent_t a, b;
  Timer() { CK(cudaEventCreate(&a)); CK(cudaEventCreate(&b)); }
  ~Timer() { cudaEventDestroy(a); cudaEventDestroy(b); }
  void start() { CK(cudaEventRecord(a, 0)); }
  double stop_us() {
    CK(cudaEventRecord(b, 0));
    CK(cudaEventSynchronize(b));
    float ms = 0;
    CK(cudaEventElapsedTime(&ms, a, b));
    return ms * 1000.0;
  }
};

template <class F> double best_us(F &&f, int warm, int reps) {
  Timer t;
  double best = 1e30;
  for (int i = 0; i < warm + reps; ++i) {
    t.start();
    f();
    const double us = t.stop_us();
    if (i >= warm) best = std::min(best, us);
  }
  return best;
}

template <class F> double median_us(F &&f, int warm, int reps) {
  Timer t;
  std::vector<double> v;
  for (int i = 0; i < warm + reps; ++i) {
    t.start();
    f();
    const double us = t.stop_us();
    if (i >= warm) v.push_back(us);
  }
  std::sort(v.begin(), v.end());
  return v[v.size() / 2];
}

int main(int argc, char **argv) {
  std::string name, out_path;
  int dev = 0;
  for (int i = 1; i < argc; ++i) {
    const std::string a = argv[i];
    if (a == "--name" && i + 1 < argc) name = argv[++i];
    else if (a == "--out" && i + 1 < argc) out_path = argv[++i];
    else if (a == "--device" && i + 1 < argc) dev = std::atoi(argv[++i]);
    else { std::fprintf(stderr, "usage: bw_probe [--name N] [--out FILE] [--device N]\n"); return 2; }
  }
  CK(cudaSetDevice(dev));
  cudaDeviceProp prop;
  CK(cudaGetDeviceProperties(&prop, dev));
  int max_blocks_per_sm = 16;
  cudaDeviceGetAttribute(&max_blocks_per_sm, cudaDevAttrMaxBlocksPerMultiprocessor, dev);
  const int sms = prop.multiProcessorCount;
  const int max_warps = prop.maxThreadsPerMultiProcessor / 32;
  if (name.empty()) {
    name = prop.name;
    for (auto &c : name) if (c == ' ') c = '-';
  }
  std::printf("probing %s: cc %d.%d, %d SMs, %.1f GB, L2 %d KB\n", prop.name, prop.major,
              prop.minor, sms, prop.totalGlobalMem / 1e9, prop.l2CacheSize / 1024);

  unsigned *sink;
  CK(cudaMalloc(&sink, 4));

  // ---- peak DRAM bandwidth: a region far larger than L2, several grid shapes.
  const size_t big_bytes = std::min<size_t>(1ull << 30, prop.totalGlobalMem / 4);
  const size_t big_vec = big_bytes / 16;
  uint4 *big;
  CK(cudaMalloc(&big, big_bytes));
  CK(cudaMemset(big, 1, big_bytes));
  double bw_peak = 0;
  for (int bps : {2, 4, 8, 16})
    for (int threads : {256, 512, 1024}) {
      const int blocks = sms * bps;
      if (bps * threads > prop.maxThreadsPerMultiProcessor) continue;
      const double us = best_us([&] { stream_read<8><<<blocks, threads>>>(big, big_vec, sink); }, 2, 8);
      bw_peak = std::max(bw_peak, big_bytes / (us * 1e3));
    }
  std::printf("  bw_peak  = %.1f GB/s\n", bw_peak);

  // ---- one SM: a single block, so exactly one SM is active.
  double bw_sm = 0;
  for (int threads : {512, 1024}) {
    const size_t region_vec = (256u << 20) / 16;
    const double us = best_us([&] { stream_read<8><<<1, threads>>>(big, region_vec, sink); }, 1, 4);
    bw_sm = std::max(bw_sm, region_vec * 16.0 / (us * 1e3));
  }
  std::printf("  bw_sm    = %.2f GB/s (one SM)\n", bw_sm);

  // ---- DRAM latency: one thread chasing a random cycle over 256 MB.
  const size_t lines = (256u << 20) / 128;
  std::vector<unsigned> perm(lines), nxt(lines * 32, 0);
  std::iota(perm.begin(), perm.end(), 0u);
  std::mt19937 rng(7);
  std::shuffle(perm.begin(), perm.end(), rng);
  for (size_t i = 0; i < lines; ++i) nxt[(size_t)perm[i] * 32] = perm[(i + 1) % lines];
  unsigned *dnext, *dout;
  CK(cudaMalloc(&dnext, nxt.size() * 4));
  CK(cudaMalloc(&dout, 4));
  CK(cudaMemcpy(dnext, nxt.data(), nxt.size() * 4, cudaMemcpyHostToDevice));
  const int steps = 200000;
  const double chase_us = best_us([&] { chase<<<1, 1>>>(dnext, perm[0], steps, dout); }, 1, 4);
  const double lat_ns = chase_us * 1e3 / steps;
  std::printf("  lat      = %.0f ns\n", lat_ns);

  // ---- L2 bandwidth: a working set of a quarter of L2, read repeatedly.
  const size_t l2_ws = std::max<size_t>(1u << 20, prop.l2CacheSize / 4);
  const double l2_us = best_us([&] { l2_read<<<sms * 4, 256>>>(big, l2_ws / 16, 200, sink); }, 1, 5);
  const double bw_l2 = l2_ws * 200.0 / (l2_us * 1e3);
  std::printf("  bw_l2    = %.0f GB/s\n", bw_l2);

  // ---- FP32 throughput.
  float *fout;
  CK(cudaMalloc(&fout, (size_t)sms * 8 * 256 * 4));
  const int fiters = 20000;
  const double f_us = best_us([&] { fma_chain<<<sms * 8, 256>>>(fout, fiters); }, 1, 5);
  const double gflops = 2.0 * 8 * fiters * (double)sms * 8 * 256 / (f_us * 1e3);
  std::printf("  f32      = %.0f GFLOP/s\n", gflops);

  // ---- launch overhead: an empty kernel timed with events, as the harness does.
  const double launch_us = median_us([&] { empty_kernel<<<1, 32>>>(); }, 20, 200);
  std::printf("  launch   = %.2f us\n", launch_us);

  // ---- sector size: time per 4-byte access against byte stride.
  const size_t n_acc = 8u << 20;
  std::vector<std::pair<int, double>> st;
  for (int s : {4, 8, 16, 32, 64, 128}) {
    const double us = best_us([&] { stride_read<<<sms * 8, 256>>>((const char *)big, n_acc, s, sink); }, 1, 6);
    st.push_back({s, us * 1e3 / n_acc}); // ns per access
  }
  const double ref = st.back().second;
  int sector = 128;
  for (auto &p : st)
    if (p.second >= 0.9 * ref) { sector = p.first; break; }
  std::printf("  stride test (ns per 4 B access):");
  for (auto &p : st) std::printf("  %dB:%.3f", p.first, p.second);
  std::printf("\n  sector   = %d B (first stride within 10%% of the 128 B time)\n", sector);

  const char *path = out_path.empty() ? nullptr : out_path.c_str();
  FILE *f = path ? std::fopen(path, "w") : stdout;
  if (!f) { std::fprintf(stderr, "cannot write %s\n", path); return 1; }
  std::fprintf(f, "# Measured by bench/bw_probe on %s\n", prop.name);
  std::fprintf(f, "# stride test, ns per 4-byte access:");
  for (auto &p : st) std::fprintf(f, "  %dB=%.3f", p.first, p.second);
  std::fprintf(f, "\nname = %s\n", name.c_str());
  std::fprintf(f, "compute_capability = %d.%d\n", prop.major, prop.minor);
  std::fprintf(f, "dram_gb = %.1f\n", prop.totalGlobalMem / 1e9);
  std::fprintf(f, "sms = %d\n", sms);
  std::fprintf(f, "bw_peak_gbs = %.1f\n", bw_peak);
  std::fprintf(f, "bw_sm_gbs = %.2f\n", bw_sm);
  std::fprintf(f, "lat_ns = %.0f\n", lat_ns);
  std::fprintf(f, "bw_l2_gbs = %.0f\n", bw_l2);
  std::fprintf(f, "l2_bytes = %d\n", prop.l2CacheSize);
  std::fprintf(f, "sector_bytes = %d\n", sector);
  std::fprintf(f, "line_bytes = 128\n");
  std::fprintf(f, "f32_gflops = %.0f\n", gflops);
  std::fprintf(f, "launch_us = %.2f\n", launch_us);
  std::fprintf(f, "max_warps_per_sm = %d\n", max_warps);
  std::fprintf(f, "max_blocks_per_sm = %d\n", max_blocks_per_sm);
  std::fprintf(f, "regs_per_sm = %d\n", prop.regsPerMultiprocessor);
  if (path) { std::fclose(f); std::printf("wrote %s\n", path); }
  return 0;
}
