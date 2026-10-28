// kvf_lowrank.cuh - decode attention over a cache whose keys are stored low-rank.
//
// Keys are stored as R coefficients per row, c = A^T k (A is D x R, fitted
// offline), values as D channels. A score needs only the projected query:
//
//   q . k  ~=  q . (B c)  =  (B^T q) . c
//
// so one tiny kernel projects each query head to R numbers, and the decode
// kernel reads R key elements per token instead of D. Nothing is reconstructed.
// Values are unchanged, so the output needs no up-projection.
//
// Same lane mapping as decode_partial in kvf_kernels.cuh: D/8 lanes per token,
// eight value elements per lane. Only the first R/8 of those lanes load key
// elements; the rest contribute zero to the score reduction. Each lane that
// loads still issues one 8, 16 byte vector, so key rows stay sector-aligned.
#pragma once

#include "kvf_kernels.cuh"

namespace kvf {

// unpack8 with the integer codes turned into floats without I2F, which issues
// at a quarter of the FMA rate: byte_perm places the code in the low mantissa
// bits of 2^23, and one subtraction removes the 2^23. Exact for codes < 2^23.
template <int FMT>
__device__ __forceinline__ void unpack8_fast(const uint4 &u, float (&x)[8]) {
  if (FMT == FMT_INT8) {
#pragma unroll
    for (int i = 0; i < 4; ++i) {
      x[i] = __uint_as_float(__byte_perm(u.x, 0x4B000000u, 0x7540 + i)) - 8388608.f;
      x[4 + i] = __uint_as_float(__byte_perm(u.y, 0x4B000000u, 0x7540 + i)) - 8388608.f;
    }
  } else if (FMT == FMT_INT4) {
#pragma unroll
    for (int i = 0; i < 8; ++i)
      x[i] = __uint_as_float(0x4B000000u | ((u.x >> (4 * i)) & 0xFu)) - 8388608.f;
  } else {
    unpack8<FMT>(u, x);
  }
}

// q_lr[b][h][r] = sum_d q[b][h][d] * Bp[hkv][d][r]; one block per (head, batch).
template <int D, int R>
__device__ __forceinline__ void project_q_body(const float *q, const float *Bp,
                                               float *q_lr, int H, int Hkv) {
  const int h = blockIdx.x, b = blockIdx.y, r = threadIdx.x;
  const int hkv = h / (H / Hkv);
  __shared__ float s_q[D];
  for (int i = r; i < D; i += R) s_q[i] = q[((long long)b * H + h) * D + i];
  __syncthreads();
  const float *col = Bp + (long long)hkv * D * R + r;
  float s = 0.f;
#pragma unroll 8
  for (int i = 0; i < D; ++i) s = fmaf(s_q[i], __ldg(col + i * R), s);
  q_lr[((long long)b * H + h) * R + r] = s;
}

// a.q points at the projected queries [B][H][R] (the raw queries when R == D
// and no rotation); a.k holds R-element rows. Keys and values may use different
// formats (KF, VF): values tolerate int4 where keys need int8.
// a.group_shift is the value group, kgs the key group.
template <int KF, int VF, int D, int R, int G, int U, int ORD, bool FINAL>
__device__ __forceinline__ void decode_partial_lr_body(const Args &a, int kgs) {
  constexpr int E = 8;
  constexpr int LPT = D / E;           // lanes per token (value side)
  constexpr int LPK = R / E;           // lanes that load key coefficients
  constexpr int TPW = 32 / LPT;
  constexpr int MAXG = 8 * TPW;
  static_assert(D == 64 || D == 128, "head dimension");
  static_assert(R % E == 0 && R <= D, "rank");
  static_assert(G == 1 || G == 2 || G == 4 || G == 8, "GQA pack size");

  const int tid = threadIdx.x;
  const int lane = tid & 31;
  const int warp = tid >> 5;
  const int nw = a.warps;
  const int grp = lane / LPT;
  const int li = lane % LPT;
  const bool kl = li < LPK;            // this lane loads key coefficients

  const int split = blockIdx.x;
  const int hb = blockIdx.y;
  const int b = blockIdx.z;
  const int gq = a.H / a.Hkv;
  const int hkv = G > 1 ? hb : hb / gq;

  const int chunk = (a.n + a.splits - 1) / a.splits;
  const int t0 = split * chunk;
  const int t1 = min(a.n, t0 + chunk);
  const int step_tokens = nw * TPW;
  const int steps = t1 > t0 ? (t1 - t0 + step_tokens - 1) / step_tokens : 0;
  const int base_t = t0 + warp * TPW + grp;

  float q[G][E];
  float qsum[G];
#pragma unroll
  for (int j = 0; j < G; ++j) {
    const int hq = G > 1 ? hkv * G + j : hb;
    float s = 0.f;
#pragma unroll
    for (int i = 0; i < E; ++i) q[j][i] = 0.f;
    if (kl) {
      const float4 *qp = reinterpret_cast<const float4 *>(
          a.q + ((long long)b * a.H + hq) * R + li * E);
      const float4 q0 = __ldg(qp), q1 = __ldg(qp + 1);
      q[j][0] = q0.x * a.scale_log2; q[j][1] = q0.y * a.scale_log2;
      q[j][2] = q0.z * a.scale_log2; q[j][3] = q0.w * a.scale_log2;
      q[j][4] = q1.x * a.scale_log2; q[j][5] = q1.y * a.scale_log2;
      q[j][6] = q1.z * a.scale_log2; q[j][7] = q1.w * a.scale_log2;
#pragma unroll
      for (int i = 0; i < E; ++i) s += q[j][i];
    }
    qsum[j] = s;
  }

  float m[G], l[G], zacc[G], acc[G][E];
#pragma unroll
  for (int j = 0; j < G; ++j) {
    m[j] = -INFINITY;
    l[j] = 0.f;
    zacc[j] = 0.f;
#pragma unroll
    for (int i = 0; i < E; ++i) acc[j][i] = 0.f;
  }

  for (int s0 = 0; s0 < steps; s0 += U) {
    uint4 ku[U], vu[U];
    float2 ksz[U], vsz[U];
    bool valid[U];
#pragma unroll
    for (int u = 0; u < U; ++u) {
      const int t = base_t + (s0 + u) * step_tokens;
      valid[u] = (s0 + u < steps) && (t < t1);
      const long long row = valid[u] ? row_of<ORD, false>(a, b, hkv, t) : 0;
      ku[u] = valid[u] && kl ? load_slice<KF, R>(a.k, row, li) : make_uint4(0, 0, 0, 0);
      vu[u] = valid[u] ? load_slice<VF, D>(a.v, row, li) : make_uint4(0, 0, 0, 0);
      ksz[u] = kl ? load_sz<KF>(a.k_meta, row, li, R, kgs) : make_float2(0.f, 0.f);
      vsz[u] = load_sz<VF>(a.v_meta, row, li, D, a.group_shift);
    }

    float sc[U][G];
#pragma unroll
    for (int u = 0; u < U; ++u) {
      float kx[E];
      unpack8_fast<KF>(ku[u], kx);
#pragma unroll
      for (int j = 0; j < G; ++j) {
        float dot = 0.f;
#pragma unroll
        for (int i = 0; i < E; ++i) dot = fmaf(q[j][i], kx[i], dot);
        float s = KF == FMT_F16 ? dot : fmaf(ksz[u].x, dot, ksz[u].y * qsum[j]);
#pragma unroll
        for (int off = LPT / 2; off > 0; off >>= 1)
          s += __shfl_xor_sync(0xffffffffu, s, off);
        sc[u][j] = s;
      }
    }

    // Online softmax, rescaled once per U tokens: the running max moves to the
    // max over all U scores first, so acc is scaled once instead of U times.
#pragma unroll
    for (int j = 0; j < G; ++j) {
      float mx = m[j];
#pragma unroll
      for (int u = 0; u < U; ++u)
        if (valid[u]) mx = fmaxf(mx, sc[u][j]);
      if (mx == -INFINITY) continue;
      const float alpha = exp2f(m[j] - mx);
      m[j] = mx;
      l[j] *= alpha;
      zacc[j] *= alpha;
#pragma unroll
      for (int i = 0; i < E; ++i) acc[j][i] *= alpha;
#pragma unroll
      for (int u = 0; u < U; ++u) sc[u][j] = valid[u] ? exp2f(sc[u][j] - mx) : 0.f;
    }

    // Values. A lane's eight elements lie in one quantization group, so the
    // zero point adds the same p * zero to all eight: kept as one scalar.
#pragma unroll
    for (int u = 0; u < U; ++u) {
      float vx[E];
      unpack8_fast<VF>(vu[u], vx);
#pragma unroll
      for (int j = 0; j < G; ++j) {
        const float p = sc[u][j];
        l[j] += p;
        const float ps = VF == FMT_F16 ? p : p * vsz[u].x;
        if (VF != FMT_F16) zacc[j] = fmaf(p, vsz[u].y, zacc[j]);
#pragma unroll
        for (int i = 0; i < E; ++i) acc[j][i] = fmaf(vx[i], ps, acc[j][i]);
      }
    }
  }

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
    for (int i = 0; i < E; ++i) s_acc[gid][li * E + i] = acc[j][i] + zacc[j];
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

// decode_merge from kvf_kernels.cuh as a device body, for an extern "C" entry.
template <int D>
__device__ __forceinline__ void decode_merge_body(const Args &a) {
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

} // namespace kvf
