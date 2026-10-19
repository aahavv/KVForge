// kvf_kernels.cuh - decode-phase attention kernels, one template instance per
// compile-time choice of a KVForge plan.
//
// One decode step for one layer: a single query vector per head attends to n
// cached tokens. Each cached byte is read once and used once, so the kernels are
// written to move bytes at the rate the memory system allows:
//
//   * every lane loads a 4, 8 or 16 byte vector (eight elements of one row), so
//     a warp's loads form contiguous, sector-aligned runs;
//   * `U` tokens' K and V rows are requested before any is consumed, which keeps
//     2*U vector loads in flight per lane (the bytes-in-flight of Little's law);
//   * softmax is online (running max and sum), so the score vector never leaves
//     registers and split chunks can be merged afterwards;
//   * quantized rows are dequantized in registers: x = raw * scale + zero.
//
// Template parameters (compile time):  FMT, D, G, U, ORD, PAGED, FINAL
// Runtime parameters (Args):           splits, warps, group, block size
#pragma once

#include <cuda_fp16.h>
#include <cuda_runtime.h>
#include <cstdint>

namespace kvf {

enum Fmt { FMT_F16 = 0, FMT_INT8 = 1, FMT_INT4 = 2 };
enum Ord { ORD_HEAD = 0, ORD_TOKEN = 1 };

struct Args {
  const float *q;              // [B][H][D], fp32
  const unsigned char *k;      // K payload
  const unsigned char *v;      // V payload
  const __half2 *k_meta;       // [rows][D/group] (scale, zero), quantized only
  const __half2 *v_meta;
  const int *block_table;      // [B][max_blocks] page ids, paged layouts only
  float *out;                  // [B][H][D], fp32
  float *part_o;               // [B][H][splits][D] unnormalised partial output
  float *part_ml;              // [B][H][splits][2] running max (log2) and sum
  int B, H, Hkv, n;
  int splits;                  // chunks of the KV length per head
  int warps;                   // warps per block (<= 8)
  int group_shift;             // log2(quantization group), quantized only
  int block_shift;             // log2(tokens per page), paged only
  int max_blocks;              // pages per sequence in the block table
  float scale_log2;            // softmax scale * log2(e)
};

// Row of the cache holding (sequence b, KV head h, token t). A row is one
// token's D channels for one head. Contiguous layouts are the paged formula
// with a single page that spans the sequence.
template <int ORD, bool PAGED>
__device__ __forceinline__ long long row_of(const Args &a, int b, int h, int t) {
  if (!PAGED) {
    return ORD == ORD_HEAD ? ((long long)b * a.Hkv + h) * a.n + t
                           : ((long long)b * a.n + t) * a.Hkv + h;
  }
  const int bt = 1 << a.block_shift;
  const int blk = t >> a.block_shift;
  const int tl = t & (bt - 1);
  const long long page = a.block_table[(long long)b * a.max_blocks + blk];
  const long long base = page * a.Hkv * bt;
  return ORD == ORD_HEAD ? base + (long long)h * bt + tl
                         : base + (long long)tl * a.Hkv + h;
}

// Eight consecutive elements of a row, as raw bits.
template <int FMT, int D>
__device__ __forceinline__ uint4 load_slice(const unsigned char *base,
                                            long long row, int li) {
  uint4 u = make_uint4(0, 0, 0, 0);
  if (FMT == FMT_F16) {
    u = __ldcs(reinterpret_cast<const uint4 *>(base + row * (D * 2) + li * 16));
  } else if (FMT == FMT_INT8) {
    const uint2 t =
        __ldcs(reinterpret_cast<const uint2 *>(base + row * D + li * 8));
    u.x = t.x;
    u.y = t.y;
  } else {
    u.x = __ldcs(reinterpret_cast<const unsigned *>(base + row * (D / 2) + li * 4));
  }
  return u;
}

// Raw values of the eight elements: the stored number for fp16, the unsigned
// integer code for int8 / int4. The affine map back to real values is applied
// by the caller, algebraically, so it is not repeated per element.
template <int FMT>
__device__ __forceinline__ void unpack8(const uint4 &u, float (&x)[8]) {
  if (FMT == FMT_F16) {
    const __half2 *h = reinterpret_cast<const __half2 *>(&u);
#pragma unroll
    for (int i = 0; i < 4; ++i) {
      const float2 f = __half22float2(h[i]);
      x[2 * i] = f.x;
      x[2 * i + 1] = f.y;
    }
  } else if (FMT == FMT_INT8) {
#pragma unroll
    for (int i = 0; i < 4; ++i) {
      x[i] = (float)((u.x >> (8 * i)) & 0xFFu);
      x[4 + i] = (float)((u.y >> (8 * i)) & 0xFFu);
    }
  } else {
#pragma unroll
    for (int i = 0; i < 8; ++i)
      x[i] = (float)((u.x >> (4 * i)) & 0xFu);
  }
}

template <int FMT>
__device__ __forceinline__ float2 load_sz(const __half2 *meta, long long row,
                                          int li, int d, int group_shift) {
  if (FMT == FMT_F16)
    return make_float2(1.f, 0.f);
  const long long groups_per_row = d >> group_shift;
  const __half2 sz = __ldg(meta + row * groups_per_row + ((li * 8) >> group_shift));
  return __half22float2(sz);
}

// Partial attention over one chunk of the KV length for one (sequence, KV head
// or query head). G query heads share every K/V row when G > 1 (GQA packing).
// FINAL writes the normalised output directly (splits == 1); otherwise it
// writes an unnormalised partial plus (max, sum) for the merge kernel.
template <int FMT, int D, int G, int U, int ORD, bool PAGED, bool FINAL>
__global__ void __launch_bounds__(256)
decode_partial(const Args a) {
  constexpr int E = 8;                 // elements per lane per row
  constexpr int LPT = D / E;           // lanes per token
  constexpr int TPW = 32 / LPT;        // tokens a warp handles per step
  constexpr int MAXG = 8 * TPW;        // lane groups per block, at most
  static_assert(D == 64 || D == 128, "head dimension");
  static_assert(G == 1 || G == 2 || G == 4 || G == 8, "GQA pack size");

  const int tid = threadIdx.x;
  const int lane = tid & 31;
  const int warp = tid >> 5;
  const int nw = a.warps;
  const int grp = lane / LPT;
  const int li = lane % LPT;

  const int split = blockIdx.x;
  const int hb = blockIdx.y;
  const int b = blockIdx.z;
  const int gq = a.H / a.Hkv;
  const int hkv = G > 1 ? hb : hb / gq;

  // Chunk of tokens this block owns.
  const int chunk = (a.n + a.splits - 1) / a.splits;
  const int t0 = split * chunk;
  const int t1 = min(a.n, t0 + chunk);
  const int step_tokens = nw * TPW;
  const int steps = t1 > t0 ? (t1 - t0 + step_tokens - 1) / step_tokens : 0;
  const int base_t = t0 + warp * TPW + grp;

  // Queries, pre-scaled so scores come out in the log2 domain.
  float q[G][E];
  float qsum[G];
#pragma unroll
  for (int j = 0; j < G; ++j) {
    const int hq = G > 1 ? hkv * G + j : hb;
    const float4 *qp = reinterpret_cast<const float4 *>(
        a.q + ((long long)b * a.H + hq) * D + li * E);
    const float4 q0 = __ldg(qp), q1 = __ldg(qp + 1);
    q[j][0] = q0.x * a.scale_log2; q[j][1] = q0.y * a.scale_log2;
    q[j][2] = q0.z * a.scale_log2; q[j][3] = q0.w * a.scale_log2;
    q[j][4] = q1.x * a.scale_log2; q[j][5] = q1.y * a.scale_log2;
    q[j][6] = q1.z * a.scale_log2; q[j][7] = q1.w * a.scale_log2;
    float s = 0.f;
#pragma unroll
    for (int i = 0; i < E; ++i) s += q[j][i];
    qsum[j] = s;
  }

  float m[G], l[G], acc[G][E];
#pragma unroll
  for (int j = 0; j < G; ++j) {
    m[j] = -INFINITY;
    l[j] = 0.f;
#pragma unroll
    for (int i = 0; i < E; ++i) acc[j][i] = 0.f;
  }

  for (int s0 = 0; s0 < steps; s0 += U) {
    // Issue every load for U tokens before any is consumed.
    uint4 ku[U], vu[U];
    float2 ksz[U], vsz[U];
    bool valid[U];
#pragma unroll
    for (int u = 0; u < U; ++u) {
      const int t = base_t + (s0 + u) * step_tokens;
      valid[u] = (s0 + u < steps) && (t < t1);
      const long long row = valid[u] ? row_of<ORD, PAGED>(a, b, hkv, t) : 0;
      ku[u] = valid[u] ? load_slice<FMT, D>(a.k, row, li) : make_uint4(0, 0, 0, 0);
      vu[u] = valid[u] ? load_slice<FMT, D>(a.v, row, li) : make_uint4(0, 0, 0, 0);
      ksz[u] = load_sz<FMT>(a.k_meta, row, li, D, a.group_shift);
      vsz[u] = load_sz<FMT>(a.v_meta, row, li, D, a.group_shift);
    }

    // Scores: per-lane partial dot, affine correction, reduce over the lanes of
    // one token.
    float sc[U][G];
#pragma unroll
    for (int u = 0; u < U; ++u) {
      float kx[E];
      unpack8<FMT>(ku[u], kx);
#pragma unroll
      for (int j = 0; j < G; ++j) {
        float dot = 0.f;
#pragma unroll
        for (int i = 0; i < E; ++i) dot = fmaf(q[j][i], kx[i], dot);
        float s = FMT == FMT_F16 ? dot : fmaf(ksz[u].x, dot, ksz[u].y * qsum[j]);
#pragma unroll
        for (int off = LPT / 2; off > 0; off >>= 1)
          s += __shfl_xor_sync(0xffffffffu, s, off);
        sc[u][j] = s;
      }
    }

    // Online softmax update and value accumulation.
#pragma unroll
    for (int u = 0; u < U; ++u) {
      if (!valid[u]) continue;
      float vx[E];
      unpack8<FMT>(vu[u], vx);
#pragma unroll
      for (int j = 0; j < G; ++j) {
        const float s = sc[u][j];
        const float m_new = fmaxf(m[j], s);
        const float alpha = exp2f(m[j] - m_new);
        const float p = exp2f(s - m_new);
        l[j] = fmaf(l[j], alpha, p);
        m[j] = m_new;
        if (FMT == FMT_F16) {
#pragma unroll
          for (int i = 0; i < E; ++i) acc[j][i] = fmaf(vx[i], p, acc[j][i] * alpha);
        } else {
          const float ps = p * vsz[u].x, pz = p * vsz[u].y;
#pragma unroll
          for (int i = 0; i < E; ++i)
            acc[j][i] = fmaf(vx[i], ps, fmaf(acc[j][i], alpha, pz));
        }
      }
    }
  }

  // Merge the lane groups of the block, one head at a time.
  __shared__ float s_acc[MAXG][D];
  __shared__ float s_m[MAXG], s_l[MAXG];
  const int gid = warp * TPW + grp;
  const int ngroups = nw * TPW;
#pragma unroll
  for (int j = 0; j < G; ++j) {
    __syncthreads();
    if (li == 0) {
      s_m[gid] = m[j];
      s_l[gid] = l[j];
    }
#pragma unroll
    for (int i = 0; i < E; ++i) s_acc[gid][li * E + i] = acc[j][i];
    __syncthreads();
    if (tid < D) {
      float M = -INFINITY;
      for (int g2 = 0; g2 < ngroups; ++g2) M = fmaxf(M, s_m[g2]);
      float L = 0.f, O = 0.f;
      if (M != -INFINITY) {
        for (int g2 = 0; g2 < ngroups; ++g2) {
          const float w = exp2f(s_m[g2] - M);
          L = fmaf(s_l[g2], w, L);
          O = fmaf(s_acc[g2][tid], w, O);
        }
      }
      const int hq = G > 1 ? hkv * G + j : hb;
      const long long head = (long long)b * a.H + hq;
      if (FINAL) {
        a.out[head * D + tid] = L > 0.f ? O / L : 0.f;
      } else {
        a.part_o[(head * a.splits + split) * D + tid] = O;
        if (tid == 0) {
          a.part_ml[(head * a.splits + split) * 2] = M;
          a.part_ml[(head * a.splits + split) * 2 + 1] = L;
        }
      }
    }
  }
}

// Log-sum-exp recombination of the split-KV partials.
template <int D>
__global__ void decode_merge(const Args a) {
  const int hq = blockIdx.x;
  const int b = blockIdx.y;
  const int t = threadIdx.x;
  const long long head = (long long)b * a.H + hq;
  float M = -INFINITY;
  for (int s = 0; s < a.splits; ++s)
    M = fmaxf(M, a.part_ml[(head * a.splits + s) * 2]);
  float L = 0.f, O = 0.f;
  for (int s = 0; s < a.splits; ++s) {
    const float ms = a.part_ml[(head * a.splits + s) * 2];
    if (ms == -INFINITY) continue;
    const float w = exp2f(ms - M);
    L = fmaf(a.part_ml[(head * a.splits + s) * 2 + 1], w, L);
    O = fmaf(a.part_o[(head * a.splits + s) * D + t], w, O);
  }
  a.out[head * D + t] = L > 0.f ? O / L : 0.f;
}

// Launch one decode step: the partial kernel, then the merge when split.
template <int FMT, int D, int G, int U, int ORD, bool PAGED>
cudaError_t launch(const Args &a, cudaStream_t st) {
  const dim3 grid(a.splits, G > 1 ? a.Hkv : a.H, a.B);
  const dim3 block(a.warps * 32);
  if (a.splits == 1) {
    decode_partial<FMT, D, G, U, ORD, PAGED, true><<<grid, block, 0, st>>>(a);
  } else {
    decode_partial<FMT, D, G, U, ORD, PAGED, false><<<grid, block, 0, st>>>(a);
    decode_merge<D><<<dim3(a.H, a.B), D, 0, st>>>(a);
  }
  return cudaGetLastError();
}

} // namespace kvf
