"""Decode attention, fp16: KVForge kernels against FlashInfer and PyTorch SDPA.

Runs inside WSL2 (FlashInfer needs Linux). Every method runs in the same process,
on the same GPU, on the same K and V, timed the same way (CUDA events, L2 flushed
before every repetition, median of the repetitions), and every output is checked
against an fp32 reference.

KVForge kernels are loaded from cubins compiled on Windows (build/cubin) and
launched through the CUDA driver API, so they are exactly the kernels the sweep
timed. Plans come from results/compare_plans.csv.

    ~/kvbench/bin/python bench/wsl/compare.py [--reps 30] [--only SHAPE]
"""
import argparse
import csv
import ctypes
import math
import statistics
import sys
import time

import torch
import torch.nn.functional as F

try:
    from cuda.bindings import driver as drv
except ImportError:  # older cuda-python layout
    from cuda import cuda as drv

ROOT = "/mnt/c/Users/aahav/KVForge/"
LOG2E = 1.4426950408889634


# ----------------------------------------------------------------- driver API
def ck(res):
    err = res[0]
    if int(err) != 0:
        raise RuntimeError("CUDA driver error %s" % err)
    return res[1] if len(res) == 2 else res[1:]


class Args(ctypes.Structure):  # mirrors kvf::Args in runtime/kvf_kernels.cuh
    _fields_ = [(n, ctypes.c_void_p) for n in ("q", "k", "v", "k_meta", "v_meta", "block_table", "out", "part_o", "part_ml")] + \
               [(n, ctypes.c_int) for n in ("B", "H", "Hkv", "n", "splits", "warps", "group_shift", "block_shift", "max_blocks")] + \
               [("scale_log2", ctypes.c_float)]


class KvForgeKernels:
    def __init__(self):
        torch.cuda.init()
        torch.zeros(1, device="cuda")  # make sure the primary context exists
        self.mods = {}
        self.funcs = {}

    def _func(self, order, mangled):
        key = (order, mangled)
        if key not in self.funcs:
            if order not in self.mods:
                path = ROOT + "build/cubin/f16_%s_c.cubin" % ("hm" if order == "head_major" else "tm")
                self.mods[order] = ck(drv.cuModuleLoadData(open(path, "rb").read()))
            self.funcs[key] = ck(drv.cuModuleGetFunction(self.mods[order], mangled.encode()))
        return self.funcs[key]

    def make(self, plan, q, K, V, out, part_o, part_ml, B, H, Hkv, n, d):
        """Return a zero-argument callable that runs one decode step."""
        order = plan["order"]
        ordv = 0 if order == "head_major" else 1
        g = H // Hkv
        pack = int(plan["gqa_pack"])
        G = g if pack else 1
        U = int(plan["unroll"])
        splits = int(plan["splits"])
        warps = int(plan["warps"])
        a = Args()
        a.q, a.k, a.v = q.data_ptr(), K.data_ptr(), V.data_ptr()
        a.k_meta = a.v_meta = a.block_table = 0
        a.out, a.part_o, a.part_ml = out.data_ptr(), part_o.data_ptr(), part_ml.data_ptr()
        a.B, a.H, a.Hkv, a.n = B, H, Hkv, n
        a.splits, a.warps, a.group_shift, a.block_shift, a.max_blocks = splits, warps, 0, 0, 0
        a.scale_log2 = (1.0 / math.sqrt(d)) * LOG2E
        final = 1 if splits == 1 else 0
        part_f = self._func(order, "_ZN3kvf14decode_partialILi0ELi%dELi%dELi%dELi%dELb0ELb%dEEEvNS_4ArgsE" % (d, G, U, ordv, final))
        merge_f = None if splits == 1 else self._func(order, "_ZN3kvf12decode_mergeILi%dEEEvNS_4ArgsE" % d)
        params = (ctypes.c_void_p * 1)(ctypes.addressof(a))
        pp = ctypes.addressof(params)
        grid = (splits, Hkv if G > 1 else H, B)

        def run():
            st = torch.cuda.current_stream().cuda_stream
            ck(drv.cuLaunchKernel(part_f, grid[0], grid[1], grid[2], warps * 32, 1, 1, 0, st, pp, 0))
            if merge_f is not None:
                ck(drv.cuLaunchKernel(merge_f, H, B, 1, d, 1, 1, 0, st, pp, 0))
        run._keep = (a, params)  # keep the argument block alive
        return run


# ----------------------------------------------------------------- timing
def make_flusher():
    buf = torch.empty(256 << 20, dtype=torch.uint8, device="cuda")
    return lambda: buf.zero_()


def bench(fn, flush, reps, warmup=5):
    ts = []
    e0, e1 = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
    for i in range(warmup + reps):
        flush()
        e0.record()
        fn()
        e1.record()
        e1.synchronize()
        if i >= warmup:
            ts.append(e0.elapsed_time(e1) * 1000.0)
    ts.sort()
    return ts[len(ts) // 2], ts[len(ts) // 4], ts[(3 * len(ts)) // 4]


def rel_l2(a, ref):
    return float(torch.linalg.vector_norm((a.float() - ref).flatten()) / torch.linalg.vector_norm(ref.flatten()))


def reference(q, K, V, H, Hkv, d):
    B = q.shape[0]
    g = H // Hkv
    s = torch.einsum("bhgd,bhnd->bhgn", q.view(B, Hkv, g, d).float(), K.float()) / math.sqrt(d)
    o = torch.einsum("bhgn,bhnd->bhgd", torch.softmax(s, -1), V.float())
    return o.reshape(B, H, d)


# ----------------------------------------------------------------- baselines
def sdpa_candidates(q, K, V, H, Hkv, d, B):
    """PyTorch scaled_dot_product_attention, one entry per usable backend."""
    from torch.nn.attention import SDPBackend, sdpa_kernel
    qh = q.half().view(B, H, 1, d)
    out = {}
    for name, be in (("default", None), ("flash", SDPBackend.FLASH_ATTENTION),
                     ("efficient", SDPBackend.EFFICIENT_ATTENTION), ("cudnn", SDPBackend.CUDNN_ATTENTION)):
        def fn(be=be):
            if be is None:
                return F.scaled_dot_product_attention(qh, K, V, enable_gqa=(H != Hkv))
            with sdpa_kernel([be]):
                return F.scaled_dot_product_attention(qh, K, V, enable_gqa=(H != Hkv))
        try:
            r = fn()
            torch.cuda.synchronize()
            out["sdpa_" + name] = (fn, r.view(B, H, d))
        except Exception as e:  # backend unavailable for this shape
            out["sdpa_" + name + "_unavailable"] = (None, str(e).split("\n")[0][:80])
    return out


def flashinfer_candidates(q, K, V, H, Hkv, d, B, n):
    try:
        import flashinfer
    except Exception as e:
        return {"flashinfer_unavailable": (None, "import failed: " + str(e).split("\n")[0][:100])}
    out = {}
    qh = q.half()
    ps = 16
    pages = n // ps
    kc = K.view(B, Hkv, pages, ps, d).permute(0, 2, 1, 3, 4).reshape(B * pages, Hkv, ps, d).contiguous()
    vc = V.view(B, Hkv, pages, ps, d).permute(0, 2, 1, 3, 4).reshape(B * pages, Hkv, ps, d).contiguous()
    indptr = torch.arange(B + 1, dtype=torch.int32, device="cuda") * pages
    indices = torch.arange(B * pages, dtype=torch.int32, device="cuda")
    last = torch.full((B,), ps, dtype=torch.int32, device="cuda")
    ws = torch.empty(128 << 20, dtype=torch.uint8, device="cuda")
    for tc in (False, True):
        name = "flashinfer_batch_paged16_tc%d" % int(tc)
        try:
            w = flashinfer.BatchDecodeWithPagedKVCacheWrapper(ws, kv_layout="HND", use_tensor_cores=tc)
            w.plan(indptr, indices, last, H, Hkv, d, ps, pos_encoding_mode="NONE", data_type=torch.float16, q_data_type=torch.float16)
            fn = lambda w=w: w.run(qh, (kc, vc))
            r = fn()
            torch.cuda.synchronize()
            out[name] = (fn, r.view(B, H, d))
        except Exception as e:
            out[name + "_unavailable"] = (None, str(e).split("\n")[0][:100])
    if B == 1:
        try:
            fn = lambda: flashinfer.single_decode_with_kv_cache(qh[0], K[0], V[0], kv_layout="HND")
            r = fn()
            torch.cuda.synchronize()
            out["flashinfer_single"] = (fn, r.view(1, H, d))
        except Exception as e:
            out["flashinfer_single_unavailable"] = (None, str(e).split("\n")[0][:100])
    return out


# ----------------------------------------------------------------- main
def parse_shape(key):
    p = key.split("_")
    return int(p[0][1:]), int(p[1][3:]), int(p[2][1:]), int(p[3][1:]), int(p[4][1:])  # H, Hkv, d, n, B


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=30)
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default=ROOT + "results/compare_rtx5060-laptop.csv")
    ap.add_argument("--no-flashinfer", action="store_true")
    a = ap.parse_args()

    plans = {}
    for r in csv.DictReader(open(ROOT + "results/compare_plans.csv")):
        plans.setdefault(r["shape"], {})[r["role"]] = r
    flush = make_flusher()
    kvf = KvForgeKernels()
    rows = []
    print("torch", torch.__version__, "|", torch.cuda.get_device_name(0), flush=True)
    for shape in sorted(plans):
        if a.only and a.only not in shape:
            continue
        H, Hkv, d, n, B = parse_shape(shape)
        torch.manual_seed(1)
        q = torch.randn(B, H, d, device="cuda", dtype=torch.float32)
        K = torch.randn(B, Hkv, n, d, device="cuda", dtype=torch.float16)
        V = torch.randn(B, Hkv, n, d, device="cuda", dtype=torch.float16)
        ref = reference(q, K, V, H, Hkv, d)
        print("\n%s" % shape, flush=True)
        results = {}

        out = torch.zeros(B, H, d, device="cuda", dtype=torch.float32)
        part_o = torch.zeros(B, H, 64, d, device="cuda", dtype=torch.float32)
        part_ml = torch.zeros(B, H, 64, 2, device="cuda", dtype=torch.float32)
        for role in ("baseline", "kvforge_pick", "oracle"):
            p = plans[shape][role]
            Kp, Vp = (K, V) if p["order"] == "head_major" else (K.permute(0, 2, 1, 3).contiguous(), V.permute(0, 2, 1, 3).contiguous())
            fn = kvf.make(p, q, Kp, Vp, out, part_o, part_ml, B, H, Hkv, n, d)
            fn()
            torch.cuda.synchronize()
            err = rel_l2(out, ref)
            t = bench(fn, flush, a.reps)
            results["kvforge_" + role.replace("kvforge_", "")] = (t, err, "splits=%s pack=%s w%s u%s %s" % (p["splits"], p["gqa_pack"], p["warps"], p["unroll"], p["order"]))
            del Kp, Vp

        cands = sdpa_candidates(q, K, V, H, Hkv, d, B)
        if not a.no_flashinfer:
            cands.update(flashinfer_candidates(q, K, V, H, Hkv, d, B, n))
        for name, (fn, r) in cands.items():
            if fn is None:
                results[name] = (None, None, r)
                continue
            t = bench(fn, flush, a.reps)
            results[name] = (t, rel_l2(r, ref), "")

        for name, (t, err, note) in results.items():
            if t is None:
                print("  %-34s unavailable: %s" % (name, note), flush=True)
                continue
            print("  %-34s %9.1f us  (IQR %.1f..%.1f)  err %.2e  %s" % (name, t[0], t[1], t[2], err, note), flush=True)
            rows.append({"shape": shape, "method": name, "t_us": "%.2f" % t[0], "p25": "%.2f" % t[1], "p75": "%.2f" % t[2], "err_vs_fp32": "%.3e" % err, "note": note})
        del q, K, V, ref
        torch.cuda.empty_cache()

    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["shape", "method", "t_us", "p25", "p75", "err_vs_fp32", "note"])
        w.writeheader()
        w.writerows(rows)
    print("\nwrote", a.out)


if __name__ == "__main__":
    main()
