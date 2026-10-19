// kvf_driver.cu - runs the kernel the compiler generated for one spec.
//
// Built together with the generated decode_<name>.cu and plan_info.h. It makes
// test data in the chosen format and layout, checks the kernel against a
// double-precision reference, times it, and prints measured against predicted.
#include "plan_info.h"

#include "kvf_host.h"

extern "C" cudaError_t KVF_LAUNCH(const kvf::Args *, cudaStream_t);
extern "C" const char *KVF_PLAN();

int main(int argc, char **argv) {
  int reps = 50;
  for (int i = 1; i + 1 < argc; i += 2)
    if (std::string(argv[i]) == "--reps") reps = std::atoi(argv[i + 1]);

  cudaDeviceProp prop;
  KVF_CUDA_CHECK(cudaGetDeviceProperties(&prop, 0));
  kvf::Shape s;
  s.B = KVF_BATCH; s.H = KVF_H; s.Hkv = KVF_HKV; s.D = KVF_D; s.n = KVF_N;
  kvf::FormatSel f;
  f.fmt = KVF_FMT;
  f.group = KVF_GROUP;
  kvf::LayoutSel l;
  l.order = KVF_ORDER;
  l.paged = KVF_PAGED != 0;
  l.bt = KVF_BLOCK;

  std::printf("device: %s\nplan:   %s\n", prop.name, KVF_PLAN());
  std::vector<float> q, K, V;
  kvf::make_data(s, 1, q, K, V);
  const float scale = 1.0f / std::sqrt((float)s.D);
  const auto exact = kvf::reference_attention(s, q, K, V, scale);
  const kvf::Quantized Kq = kvf::quantize(f, s.D, K, s.rows());
  const kvf::Quantized Vq = kvf::quantize(f, s.D, V, s.rows());
  const auto ref = kvf::reference_attention(s, q, Kq.deq, Vq.deq, scale);
  kvf::Cache cache = kvf::upload_cache(s, f, l, Kq, Vq, 18);
  const size_t flush = std::max<size_t>(96u << 20, (size_t)prop.l2CacheSize * 3);
  kvf::DeviceBuffers d = kvf::alloc_buffers(s, KVF_SPLITS, flush, q);
  const kvf::Args a = kvf::make_args(s, f, l, cache, d, KVF_SPLITS, KVF_WARPS);

  KVF_CUDA_CHECK(KVF_LAUNCH(&a, 0));
  KVF_CUDA_CHECK(cudaDeviceSynchronize());
  std::vector<float> got((size_t)s.B * s.H * s.D);
  KVF_CUDA_CHECK(cudaMemcpy(got.data(), d.out, got.size() * 4, cudaMemcpyDeviceToHost));
  const double err_ref = kvf::rel_l2(got, ref);
  const double err_exact = kvf::rel_l2(got, exact);

  const kvf::TimeStats t = kvf::time_launch([&] { KVF_LAUNCH(&a, 0); }, d, 5, reps);
  const double bytes = 2.0 * s.rows() * (f.rowBytes(s.D) + f.groupsPerRow(s.D) * 4);
  std::printf("check:    relative error vs dequantised reference %.3g (%s)\n", err_ref,
              err_ref < 2e-3 ? "PASS" : "FAIL");
  std::printf("accuracy: relative error vs exact fp32 attention %.3g\n", err_exact);
  std::printf("time:     %.2f us median (IQR %.2f..%.2f, %d reps)\n", t.median, t.p25, t.p75,
              t.reps);
  std::printf("rate:     %.1f GB/s of KV payload\n", bytes / (t.median * 1e3));
  std::printf("predicted %.2f us, measured %.2f us (ratio %.2f)\n", (double)KVF_PRED_US, t.median,
              t.median / (double)KVF_PRED_US);
  cache.release();
  kvf::free_buffers(d);
  return err_ref < 2e-3 ? 0 : 1;
}
