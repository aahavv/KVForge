// kvf_tc.cuh - grouped-query decode attention on tensor cores, int8 keys and
// int8 or int4 values (per-group scale and zero, as in kvf_kernels.cuh).
//
// The CUDA-core kernels spend about 100 warp instructions per token on a packed
// group of 4 query heads: every lane redoes the softmax and the head loop for
// its slice. With compressed caches that, not DRAM, sets the time. Here one warp
// handles 16 tokens per step with mma.m16n8k16 (fp16 in, fp32 accumulate):
//
//   scores  S  [heads x 8 tokens]  = Q [heads x 16 dims] . K^T [16 dims x 8 tokens]
//   output  O^T[16 dims x heads ]  = V^T [16 dims x 16 tokens] . P^T [16 tokens x heads]
//
// The score accumulator holds, per lane, head g = lane/4 at tokens 2t, 2t+1
// (t = lane%4): exactly the P^T fragment the second product takes, so P never
// leaves registers. Query heads fill rows 0..G-1 of the 16-row score tile (G <= 8)
// and columns 0..G-1 of the output tile.
//
// Dimension order inside a product is free (a dot product does not care), so
// the head dimension is permuted to make every lane's loads contiguous:
//   keys:   lane t of a token loads bytes [16t, 16t+16) of each 64-dim chunk;
//           k-step s uses dims 64(s/4) + 16t + 4(s%4) + {0..3}.
//   values: lane g loads dims [VPT g, VPT g + VPT) (VPT = D/8) of four tokens;
//           output row r of m-tile i is dim VPT g + i (r = g) or VPT g + VPT/2 + i
//           (r = g + 8), and is written back to its real position at the end.
// Quantized elements become fp16 with byte_perm into the mantissa of 1024,
// one subtraction, and one fused scale-and-zero, two elements per instruction.
#pragma once

#include "kvf_lowrank.cuh"

namespace kvf {

__device__ __forceinline__ void mma16816(float (&c)[4], unsigned a0, unsigned a1,
                                         unsigned a2, unsigned a3, unsigned b0,
                                         unsigned b1) {
  asm volatile(
      "mma.sync.aligned.m16n8k16.row.col.f32.f16.f16.f32 "
      "{%0,%1,%2,%3}, {%4,%5,%6,%7}, {%8,%9}, {%0,%1,%2,%3};\n"
      : "+f"(c[0]), "+f"(c[1]), "+f"(c[2]), "+f"(c[3])
      : "r"(a0), "r"(a1), "r"(a2), "r"(a3), "r"(b0), "r"(b1));
}

__device__ __forceinline__ unsigned h2u(__half2 h) {
  return *reinterpret_cast<unsigned *>(&h);
}
__device__ __forceinline__ __half2 u2h(unsigned u) {
  return *reinterpret_cast<__half2 *>(&u);
}

// Bytes x0 (low) and x1 of x, already isolated in bytes 0 and 2 of w,
// to the half2 (x0, x1) as integers.
__device__ __forceinline__ __half2 bytes02_to_h2(unsigned w) {
  const unsigned m = (w & 0x00FF00FFu) | 0x64006400u;
  return __hsub2(u2h(m), u2h(0x64006400u));
}

// In-place fast Walsh-Hadamard transform of n = 2^k rows of length D in shared
// memory (Sylvester order), by the whole block.
template <int D>
__device__ __forceinline__ void fwht_smem(float *x, int rows) {
  for (int h = 1; h < D; h <<= 1) {
    __syncthreads();
    for (int i = threadIdx.x; i < rows * D / 2; i += blockDim.x) {
      const int r = i / (D / 2), k = i % (D / 2);
      const int j = (k / h) * 2 * h + (k % h);
      float *row = x + r * D;
      const float u = row[j], v = row[j + h];
      row[j] = u + v;
      row[j + h] = u - v;
    }
  }
  __syncthreads();
}

// ROT: keys and values were stored rotated by H = diag(signs) Had / sqrt(D);
// the query is rotated here (q H = FWHT(q * signs) / sqrt(D)) and the output is
// rotated back by the merge (decode_merge_rot_body). The rotation spreads outlier
// channels, which lets int8 keys and int4 values use 128-wide groups.
// PF: software-pipelined loop (U must be 1).
template <int KF, int VF, int D, int U, bool FINAL, bool ROT = false, bool PF = false>
__device__ __forceinline__ void decode_tc_body(const Args &a, int kgs,
                                               const float *signs = nullptr) {
  static_assert(KF == FMT_INT8, "keys: int8");
  static_assert(VF == FMT_INT8 || VF == FMT_INT4, "values: int8 or int4");
  static_assert(D == 64 || D == 128, "head dimension");
  static_assert(!PF || U == 1, "pipelined loop takes one tile per stage");
  constexpr int KS = D / 16;            // k-steps over the head dimension
  constexpr int NCH = D / 64;           // 64-dim key chunks
  constexpr int MT = D / 16;            // m-tiles of the output
  constexpr int VPT = D / 8;            // value dims per lane per token
  constexpr int VW = VF == FMT_INT8 ? VPT / 4 : VPT / 8;  // 32-bit words of them

  const int lane = threadIdx.x & 31;
  const int warp = threadIdx.x >> 5;
  const int nw = a.warps;
  const int g = lane >> 2;              // group id: head row / token column
  const int t = lane & 3;               // thread in group

  const int split = blockIdx.x;
  const int hkv = blockIdx.y;
  const int b = blockIdx.z;
  const int G = a.H / a.Hkv;            // heads sharing this KV head, <= 8

  const int chunk = (a.n + a.splits - 1) / a.splits;
  const int t0 = split * chunk;
  const int t1 = min(a.n, t0 + chunk);
  const int ntiles = t1 > t0 ? (t1 - t0 + 15) / 16 : 0;

  // Query fragments (rows g < G real, rows g + 8 padding).
  unsigned qa[KS][2];
  __shared__ __align__(16) float s_q[ROT ? 8 : 1][ROT ? D : 4];
  {
    const bool real = g < G;
    const float *qp = a.q + ((long long)b * a.H + hkv * G + (real ? g : 0)) * D;
    if (ROT) {
      const float *q0 = a.q + ((long long)b * a.H + hkv * G) * D;
      const float sc = rsqrtf((float)D);
      for (int i = threadIdx.x; i < G * D; i += blockDim.x)
        (&s_q[0][0])[i] = q0[i] * signs[i % D];
      fwht_smem<D>(&s_q[0][0], G);
      for (int i = threadIdx.x; i < G * D; i += blockDim.x) (&s_q[0][0])[i] *= sc;
      __syncthreads();
      qp = &s_q[real ? g : 0][0];
    }
#pragma unroll
    for (int s = 0; s < KS; ++s) {
      const int base = 64 * (s >> 2) + 16 * t + 4 * (s & 3);
      const float4 v = real ? (ROT ? *reinterpret_cast<const float4 *>(qp + base)
                                   : __ldg(reinterpret_cast<const float4 *>(qp + base)))
                            : make_float4(0.f, 0.f, 0.f, 0.f);
      qa[s][0] = h2u(__floats2half2_rn(v.x * a.scale_log2, v.y * a.scale_log2));
      qa[s][1] = h2u(__floats2half2_rn(v.z * a.scale_log2, v.w * a.scale_log2));
    }
  }

  float oc[MT][4];
#pragma unroll
  for (int i = 0; i < MT; ++i) oc[i][0] = oc[i][1] = oc[i][2] = oc[i][3] = 0.f;
  float m = -INFINITY, l = 0.f;         // softmax state of head g

  const long long rows_base = ((long long)b * a.Hkv + hkv) * a.n;   // head-major
  const int kgroups = D >> kgs, vgroups = D >> a.group_shift;

  // One 16-token tile's loads, in registers.
  struct Tile {
    uint4 kw[2][NCH];                   // keys: n-tile j (token 8 j + g), chunk c
    __half2 ksz[2][NCH];
    unsigned vw[4][VW];                 // values: token slots 2t, 2t+1, 2t+8, 2t+9
    __half2 vsz[4];
    bool kval[2], vval[4];
  };

  auto load_tile = [&](Tile &r, int tile) {
    const int tok0 = t0 + tile * 16;
    const bool tile_ok = tile < ntiles;
#pragma unroll
    for (int j = 0; j < 2; ++j) {
      const int tok = tok0 + 8 * j + g;
      r.kval[j] = tile_ok && tok < t1;
      const long long row = rows_base + (r.kval[j] ? tok : 0);
#pragma unroll
      for (int c = 0; c < NCH; ++c) {
        r.kw[j][c] = r.kval[j]
            ? __ldcs(reinterpret_cast<const uint4 *>(a.k + row * D + 64 * c + 16 * t))
            : make_uint4(0, 0, 0, 0);
        r.ksz[j][c] = r.kval[j] ? __ldg(a.k_meta + row * kgroups + ((64 * c + 16 * t) >> kgs))
                                : __floats2half2_rn(0.f, 0.f);
      }
    }
#pragma unroll
    for (int e = 0; e < 4; ++e) {
      const int tok = tok0 + 2 * t + (e & 1) + 8 * (e >> 1);
      r.vval[e] = tile_ok && tok < t1;
      const long long row = rows_base + (r.vval[e] ? tok : 0);
      const unsigned char *vp = a.v + row * (VF == FMT_INT8 ? D : D / 2) +
                                (VF == FMT_INT8 ? VPT : VPT / 2) * g;
      if (VW == 4) {
        const uint4 x = r.vval[e] ? __ldcs(reinterpret_cast<const uint4 *>(vp)) : make_uint4(0, 0, 0, 0);
        r.vw[e][0] = x.x; r.vw[e][1] = x.y; r.vw[e][2] = x.z; r.vw[e][3] = x.w;
      } else if (VW == 2) {
        const uint2 x = r.vval[e] ? __ldcs(reinterpret_cast<const uint2 *>(vp)) : make_uint2(0, 0);
        r.vw[e][0] = x.x; r.vw[e][1] = x.y;
      } else {
        r.vw[e][0] = r.vval[e] ? __ldcs(reinterpret_cast<const unsigned *>(vp)) : 0u;
      }
      r.vsz[e] = r.vval[e] ? __ldg(a.v_meta + row * vgroups + ((VPT * g) >> a.group_shift))
                           : __floats2half2_rn(0.f, 0.f);
    }
  };

  auto compute = [&](const Tile (&r)[U]) {
    // Scores: sc[u][j][0..1] = head g, tokens 16 tile + 8 j + 2t + {0,1}.
    float sc[U][2][2];
#pragma unroll
    for (int u = 0; u < U; ++u) {
#pragma unroll
      for (int j = 0; j < 2; ++j) {
        float c4[4] = {0.f, 0.f, 0.f, 0.f};
#pragma unroll
        for (int s = 0; s < KS; ++s) {
          const int c = s >> 2;
          const unsigned w = (&r[u].kw[j][c].x)[s & 3];
          const __half2 sc2 = __low2half2(r[u].ksz[j][c]);
          const __half2 zr2 = __high2half2(r[u].ksz[j][c]);
          const __half2 lo = __hfma2(bytes02_to_h2(__byte_perm(w, 0u, 0x4140)), sc2, zr2);
          const __half2 hi = __hfma2(bytes02_to_h2(__byte_perm(w, 0u, 0x4342)), sc2, zr2);
          mma16816(c4, qa[s][0], 0u, qa[s][1], 0u, h2u(lo), h2u(hi));
        }
        // column n of the tile is token 8 j + n; lane holds n = 2t, 2t+1
        const bool ok0 = __shfl_sync(0xffffffffu, r[u].kval[j], 4 * (2 * t));
        const bool ok1 = __shfl_sync(0xffffffffu, r[u].kval[j], 4 * (2 * t + 1));
        sc[u][j][0] = ok0 ? c4[0] : -INFINITY;
        sc[u][j][1] = ok1 ? c4[1] : -INFINITY;
      }
    }

    // Online softmax for head g over this lane group's tokens.
    float mx = m;
#pragma unroll
    for (int u = 0; u < U; ++u)
#pragma unroll
      for (int j = 0; j < 2; ++j) mx = fmaxf(mx, fmaxf(sc[u][j][0], sc[u][j][1]));
    mx = fmaxf(mx, __shfl_xor_sync(0xffffffffu, mx, 1));
    mx = fmaxf(mx, __shfl_xor_sync(0xffffffffu, mx, 2));
    const float alpha = mx == -INFINITY ? 1.f : exp2f(m - mx);
    m = mx;
    l *= alpha;
    unsigned pb[U][2];                  // P^T fragments: (tokens 2t, 2t+1), (2t+8, 2t+9)
#pragma unroll
    for (int u = 0; u < U; ++u) {
      float p[2][2];
#pragma unroll
      for (int j = 0; j < 2; ++j) {
        p[j][0] = mx == -INFINITY ? 0.f : exp2f(sc[u][j][0] - mx);
        p[j][1] = mx == -INFINITY ? 0.f : exp2f(sc[u][j][1] - mx);
        l += p[j][0] + p[j][1];
      }
      pb[u][0] = h2u(__floats2half2_rn(p[0][0], p[0][1]));
      pb[u][1] = h2u(__floats2half2_rn(p[1][0], p[1][1]));
    }

    // Rescale the output columns this lane holds: heads 2t and 2t+1.
    const float al0 = __shfl_sync(0xffffffffu, alpha, 4 * (2 * t));
    const float al1 = __shfl_sync(0xffffffffu, alpha, 4 * (2 * t + 1));
#pragma unroll
    for (int i = 0; i < MT; ++i) {
      oc[i][0] *= al0; oc[i][1] *= al1; oc[i][2] *= al0; oc[i][3] *= al1;
    }

    // O^T += V^T P^T. A fragment for m-tile i: rows g (dim VPT g + i) and g + 8
    // (dim VPT g + VPT/2 + i), columns = token slots (2t, 2t+1) and (2t+8, 2t+9).
#pragma unroll
    for (int u = 0; u < U; ++u) {
      // per token slot: the lane's VPT elements, one per byte
      unsigned ev[4][VW], od[4][VW];
#pragma unroll
      for (int e = 0; e < 4; ++e)
#pragma unroll
        for (int k = 0; k < VW; ++k) {
          ev[e][k] = VF == FMT_INT8 ? r[u].vw[e][k] : (r[u].vw[e][k] & 0x0F0F0F0Fu);
          od[e][k] = VF == FMT_INT8 ? 0u : ((r[u].vw[e][k] >> 4) & 0x0F0F0F0Fu);
        }
      const __half2 s01 = __lows2half2(r[u].vsz[0], r[u].vsz[1]);
      const __half2 z01 = __highs2half2(r[u].vsz[0], r[u].vsz[1]);
      const __half2 s23 = __lows2half2(r[u].vsz[2], r[u].vsz[3]);
      const __half2 z23 = __highs2half2(r[u].vsz[2], r[u].vsz[3]);
#pragma unroll
      for (int i = 0; i < MT; ++i) {
        unsigned av[4];
#pragma unroll
        for (int h = 0; h < 2; ++h) {          // h = 0: row g, h = 1: row g + 8
          const int dim = i + h * (VPT / 2);   // index into the lane's VPT dims
#pragma unroll
          for (int pr = 0; pr < 2; ++pr) {     // token pair (0,1) or (2,3)
            unsigned wa, wb;
            int byte;
            if (VF == FMT_INT8) {
              wa = ev[2 * pr][dim >> 2]; wb = ev[2 * pr + 1][dim >> 2]; byte = dim & 3;
            } else {
              const int k = dim >> 3;
              byte = (dim >> 1) & 3;
              wa = (dim & 1) ? od[2 * pr][k] : ev[2 * pr][k];
              wb = (dim & 1) ? od[2 * pr + 1][k] : ev[2 * pr + 1][k];
            }
            const unsigned x = __byte_perm(wa, wb, byte | ((4 + byte) << 8));
            const __half2 v = __hfma2(bytes02_to_h2(x), pr ? s23 : s01, pr ? z23 : z01);
            av[pr * 2 + h] = h2u(v);
          }
        }
        // a0a1 = (row g, tokens 2t,2t+1); a2a3 = (row g+8, same);
        // a4a5 = (row g, tokens 2t+8, 2t+9); a6a7 = (row g+8, same)
        mma16816(oc[i], av[0], av[1], av[2], av[3], pb[u][0], pb[u][1]);
      }
    }
  };

  if constexpr (PF) {
    // Software pipeline: the next tile's loads are in flight while this one is
    // computed. Two register sets, used alternately, so nothing is copied.
    Tile ra[1], rb[1];
    int tb = warp;
    load_tile(ra[0], tb);
    for (; tb < ntiles; tb += 2 * nw) {
      load_tile(rb[0], tb + nw);
      compute(ra);
      if (tb + nw >= ntiles) break;
      load_tile(ra[0], tb + 2 * nw);
      compute(rb);
    }
  } else {
    for (int tb = warp; tb < ntiles; tb += nw * U) {
      Tile r[U];
#pragma unroll
      for (int u = 0; u < U; ++u) load_tile(r[u], tb + u * nw);
      compute(r);
    }
  }

  // Head g's sum over the lane group, then merge the warps.
  l += __shfl_xor_sync(0xffffffffu, l, 1);
  l += __shfl_xor_sync(0xffffffffu, l, 2);
  __shared__ float s_o[8][8][D];
  __shared__ float s_m[8][8], s_l[8][8];
  if (t == 0 && g < G) {
    s_m[warp][g] = m;
    s_l[warp][g] = l;
  }
#pragma unroll
  for (int i = 0; i < MT; ++i) {
    const int d0 = VPT * g + i, d1 = VPT * g + VPT / 2 + i;
    if (2 * t < G) { s_o[warp][2 * t][d0] = oc[i][0]; s_o[warp][2 * t][d1] = oc[i][2]; }
    if (2 * t + 1 < G) { s_o[warp][2 * t + 1][d0] = oc[i][1]; s_o[warp][2 * t + 1][d1] = oc[i][3]; }
  }
  __syncthreads();
  for (int idx = threadIdx.x; idx < G * D; idx += blockDim.x) {
    const int h = idx / D, d = idx % D;
    float M = -INFINITY;
    for (int w = 0; w < nw; ++w) M = fmaxf(M, s_m[w][h]);
    float L = 0.f, O = 0.f;
    if (M != -INFINITY) {
      for (int w = 0; w < nw; ++w) {
        if (s_m[w][h] == -INFINITY) continue;
        const float wt = exp2f(s_m[w][h] - M);
        L = fmaf(s_l[w][h], wt, L);
        O = fmaf(s_o[w][h][d], wt, O);
      }
    }
    const long long head = (long long)b * a.H + hkv * G + h;
    if (FINAL) {
      a.out[head * D + d] = L > 0.f ? O / L : 0.f;
    } else {
      a.part_o[(head * a.splits + split) * D + d] = O;
      if (d == 0) {
        a.part_ml[(head * a.splits + split) * 2] = M;
        a.part_ml[(head * a.splits + split) * 2 + 1] = L;
      }
    }
  }
}

// decode_merge_body followed by the inverse rotation: out = FWHT(o) * signs / sqrt(D).
template <int D>
__device__ __forceinline__ void decode_merge_rot_body(const Args &a, const float *signs) {
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
  __shared__ float s_o[D];
  s_o[t] = L > 0.f ? O / L : 0.f;
  fwht_smem<D>(s_o, 1);
  a.out[head * D + t] = s_o[t] * signs[t] * rsqrtf((float)D);
}

} // namespace kvf
