"""KVForge cache-format kernels (runtime/kvf_lowrank.cuh) against FlashInfer.

Same rules as bench/wsl/compare.py: one process, same GPU, CUDA-event timing with
an L2 flush before every repetition, median of the repetitions. Every KVForge
output is checked against an fp32 reference computed from exactly what the
kernel stores, so a pass means the kernel is correct; what each stored format
costs in model accuracy is measured separately, on a real model (study.py).

Variants (key format, value format, key width R, query transform):
  f16           fp16 K and V                         (same bytes as FlashInfer fp16)
  int8          int8:32 K and V                      (vs FlashInfer fp8)
  k8v4          int8:32 K, int4:32 V                 (PPL +0.2% on Qwen3-1.7B)
  rot_k8v4      rotated int8:64 K, int4:32 V         (PPL +0.0%; q rotated before,
                                                      output rotated back after)
  lr64q_int8    rank-64 keys, int8 K and V           (PPL +11%; kept for the record)

Times include every kernel a variant needs (query projection or rotation, the
decode kernel, the split merge, the output rotation). Plans come from a short
measured search; the six best are re-timed interleaved, because the laptop's
memory clock changes between runs. The final timing is interleaved too.

    ~/kvbench/bin/python bench/wsl/lowrank/bench_lr.py [--reps 30] [--only SHAPE]
"""
import argparse
import csv
import ctypes
import math
import os
import subprocess
import sys

import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import compare as C  # noqa: E402

ROOT = C.ROOT
LOG2E = C.LOG2E
ck = C.ck
drv = C.drv


class Kernels:
    def __init__(self, path=ROOT + "build/cubin/lowrank_sm120.cubin", tc_path=ROOT + "build/cubin/tc_sm120.cubin"):
        self.mod = ck(drv.cuModuleLoadData(open(path, "rb").read()))
        self.tc_mod = ck(drv.cuModuleLoadData(open(tc_path, "rb").read()))
        self.funcs = {}

    def f(self, name):
        if name not in self.funcs:
            mod = self.tc_mod if name.startswith(("tc_", "merge_rot_")) else self.mod
            self.funcs[name] = ck(drv.cuModuleGetFunction(mod, name.encode()))
        return self.funcs[name]

    def _proj(self, src, mat, dst, d, R, H, Hkv, B):
        """dst[b][h][r] = sum_i src[b][h][i] * mat[hkv][i][r], as a launch closure."""
        fn = self.f("proj_d%d_r%d" % (d, R))
        args = [ctypes.c_void_p(src.data_ptr()), ctypes.c_void_p(mat.data_ptr()),
                ctypes.c_void_p(dst.data_ptr()), ctypes.c_int(H), ctypes.c_int(Hkv)]
        params = (ctypes.c_void_p * 5)(*[ctypes.addressof(x) for x in args])

        def launch(st):
            ck(drv.cuLaunchKernel(fn, H, B, 1, R, 1, 1, 0, st, ctypes.addressof(params), 0))
        launch._keep = (args, params)
        return launch

    def make(self, v, plan, t, B, H, Hkv, n, d):
        """v: variant dict; plan: (splits, G, U, warps); t: device tensors."""
        splits, G, U, warps = plan
        R = v["R"]
        a = C.Args()
        a.q = (t["q_lr"] if v["qmode"] in ("proj", "rot") else t["q"]).data_ptr()
        a.k, a.v = t["k"].data_ptr(), t["v"].data_ptr()
        a.k_meta = t["k_meta"].data_ptr() if v["kf"] != "f16" else 0
        a.v_meta = t["v_meta"].data_ptr() if v["vf"] != "f16" else 0
        a.block_table = 0
        a.out = (t["out_r"] if v["qmode"] == "rot" else t["out"]).data_ptr()
        a.part_o, a.part_ml = t["part_o"].data_ptr(), t["part_ml"].data_ptr()
        a.B, a.H, a.Hkv, a.n = B, H, Hkv, n
        a.splits, a.warps, a.group_shift, a.block_shift, a.max_blocks = splits, warps, v["vgs"], 0, 0
        a.scale_log2 = (1.0 / math.sqrt(d)) * LOG2E
        kg = ctypes.c_int(v["kgs"])
        fin = "final" if splits == 1 else "part"
        fused = v["qmode"] == "rotf"      # rotation inside the kernels (split path only)
        if fused:
            assert splits > 1
            part = self.f("tc_rot_%s_%s_d%d_u%d_part" % (v["kf"], v["vf"], d, U))
        elif v.get("tc"):   # tensor-core kernel: one block per KV head, G is runtime
            part = self.f("tc_%s_%s_d%d_u%d_%s" % (v["kf"], v["vf"], d, U, fin))
        else:
            part = self.f("lr_%s_%s_d%d_r%d_g%d_u%d_mb1_%s" % (v["kf"], v["vf"], d, R, G, U, fin))
        merge = None if splits == 1 else self.f(("merge_rot_d%d" if fused else "merge_d%d") % d)
        pre = self._proj(t["q"], t["Bp"], t["q_lr"], d, R, H, Hkv, B) if v["qmode"] in ("proj", "rot") else None
        post = self._proj(t["out_r"], t["Hinv"], t["out"], d, d, H, Hkv, B) if v["qmode"] == "rot" else None
        sg = ctypes.c_void_p(t["signs"].data_ptr() if fused else 0)
        part_params = (ctypes.c_void_p * 3)(ctypes.addressof(a), ctypes.addressof(kg), ctypes.addressof(sg))
        merge_params = (ctypes.c_void_p * 2)(ctypes.addressof(a), ctypes.addressof(sg))
        grid = (splits, Hkv if (G > 1 or v.get("tc")) else H, B)

        def run():
            st = torch.cuda.current_stream().cuda_stream
            if pre is not None:
                pre(st)
            ck(drv.cuLaunchKernel(part, grid[0], grid[1], grid[2], warps * 32, 1, 1, 0, st, ctypes.addressof(part_params), 0))
            if merge is not None:
                ck(drv.cuLaunchKernel(merge, H, B, 1, d, 1, 1, 0, st, ctypes.addressof(merge_params), 0))
            if post is not None:
                post(st)
        run._keep = (a, kg, sg, pre, post, part_params, merge_params)
        return run


def quant(x, bits, group):
    """KVForge int<bits>:<group> along the last dim: packed codes, half2 (scale, zero) meta,
    and the dequantized values the kernel will see."""
    sh = x.shape
    gx = x.float().reshape(*sh[:-1], sh[-1] // group, group)
    mn, mx = gx.amin(-1, keepdim=True), gx.amax(-1, keepdim=True)
    top = 2 ** bits - 1
    scale = ((mx - mn) / top).clamp_min(1e-8)
    scale_h, mn_h = scale.half(), mn.half()
    code = torch.round((gx - mn_h.float()) / scale_h.float()).clamp(0, top)
    deq = (code * scale_h.float() + mn_h.float()).reshape(sh)
    meta = torch.stack([scale_h[..., 0], mn_h[..., 0]], -1).contiguous()
    code = code.to(torch.uint8).reshape(sh)
    if bits == 4:  # two codes per byte, element 2j in the low nibble
        code = code[..., 0::2] | (code[..., 1::2] << 4)
    return code.contiguous(), meta, deq


def hadamard(d, seed, device):
    Hm = torch.ones(1, 1)
    while Hm.shape[0] < d:
        Hm = torch.cat([torch.cat([Hm, Hm], 1), torch.cat([Hm, -Hm], 1)], 0)
    gen = torch.Generator().manual_seed(seed)
    signs = torch.randint(0, 2, (d,), generator=gen).float() * 2 - 1
    return ((torch.diag(signs) @ Hm) / math.sqrt(d)).to(device)


def ref_attn(qx, kdeq, vdeq, H, Hkv, d):
    B = qx.shape[0]
    g = H // Hkv
    R = qx.shape[-1]
    s = torch.einsum("bhgr,bhnr->bhgn", qx.view(B, Hkv, g, R).float(), kdeq.float()) / math.sqrt(d)
    return torch.einsum("bhgn,bhnd->bhgd", torch.softmax(s, -1), vdeq.float()).reshape(B, H, d)


def flashinfer_fp8(q, K, V, H, Hkv, d, B, n):
    import flashinfer
    out = {}
    ps = 16
    pages = n // ps
    ks = float(K.float().abs().amax()) / 448.0
    vs = float(V.float().abs().amax()) / 448.0
    k8 = (K.float() / ks).to(torch.float8_e4m3fn)
    v8 = (V.float() / vs).to(torch.float8_e4m3fn)
    kc = k8.view(B, Hkv, pages, ps, d).permute(0, 2, 1, 3, 4).reshape(B * pages, Hkv, ps, d).contiguous()
    vc = v8.view(B, Hkv, pages, ps, d).permute(0, 2, 1, 3, 4).reshape(B * pages, Hkv, ps, d).contiguous()
    del k8, v8
    indptr = torch.arange(B + 1, dtype=torch.int32, device="cuda") * pages
    indices = torch.arange(B * pages, dtype=torch.int32, device="cuda")
    last = torch.full((B,), ps, dtype=torch.int32, device="cuda")
    ws = torch.empty(128 << 20, dtype=torch.uint8, device="cuda")
    qh = q.half()
    for tc in (False, True):
        name = "flashinfer_fp8_paged16_tc%d" % int(tc)
        try:
            w = flashinfer.BatchDecodeWithPagedKVCacheWrapper(ws, kv_layout="HND", use_tensor_cores=tc)
            w.plan(indptr, indices, last, H, Hkv, d, ps, pos_encoding_mode="NONE",
                   data_type=torch.float8_e4m3fn, q_data_type=torch.float16)
            fn = lambda w=w: w.run(qh, (kc, vc), k_scale=ks, v_scale=vs)
            r = fn()
            torch.cuda.synchronize()
            out[name] = (fn, r.view(B, H, d))
        except Exception as e:
            out[name + "_unavailable"] = (None, str(e).split("\n")[0][:120])
    return out


def mem_clock():
    try:
        return subprocess.run(["nvidia-smi", "--query-gpu=clocks.mem", "--format=csv,noheader,nounits"],
                              capture_output=True, text=True, timeout=10).stdout.strip() or "?"
    except Exception:
        return "?"


def variants(d, g):
    r_lo = 64 if d == 128 else 32
    tc = [] if not 1 <= g <= 8 else [
        {"name": "tc_int8", "kf": "int8", "vf": "int8", "R": d, "kgs": 5, "vgs": 5, "qmode": "none", "tc": True},
        {"name": "tc_k8v4", "kf": "int8", "vf": "int4", "R": d, "kgs": 5, "vgs": 5, "qmode": "none", "tc": True},
        {"name": "tc_k8g64v4", "kf": "int8", "vf": "int4", "R": d, "kgs": 6, "vgs": 5, "qmode": "none", "tc": True},
        {"name": "tc_rot_k8g128v4g64", "kf": "int8", "vf": "int4", "R": d, "kgs": 7, "vgs": 6, "qmode": "rotf", "tc": True},
        {"name": "tc_rot_k8g128v4g128", "kf": "int8", "vf": "int4", "R": d, "kgs": 7, "vgs": 7, "qmode": "rotf", "tc": True},
    ]
    lg = int(math.log2(d))   # a group never spans more than one row
    for v in tc:
        v["kgs"], v["vgs"] = min(v["kgs"], lg), min(v["vgs"], lg)
    return tc + [
        {"name": "f16", "kf": "f16", "vf": "f16", "R": d, "kgs": 5, "vgs": 5, "qmode": "none"},
        {"name": "int8", "kf": "int8", "vf": "int8", "R": d, "kgs": 5, "vgs": 5, "qmode": "none"},
        {"name": "k8v4", "kf": "int8", "vf": "int4", "R": d, "kgs": 5, "vgs": 5, "qmode": "none"},
        {"name": "rot_k8v4", "kf": "int8", "vf": "int4", "R": d, "kgs": 6, "vgs": 5, "qmode": "rot"},
        {"name": "lr%dq_int8" % r_lo, "kf": "int8", "vf": "int8", "R": r_lo, "kgs": 5, "vgs": 5, "qmode": "proj"},
    ]


def timed_interleaved(fns, flush, rounds):
    e0, e1 = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
    tt = [[] for _ in fns]
    for rep in range(rounds):
        for i, fn in enumerate(fns):
            flush()
            e0.record(); fn(); e1.record(); e1.synchronize()
            tt[i].append(e0.elapsed_time(e1) * 1000.0)
    return tt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=30)
    ap.add_argument("--search-reps", type=int, default=5)
    ap.add_argument("--only", default="")
    ap.add_argument("--variants", default="")
    ap.add_argument("--out", default=ROOT + "results/lowrank/bench_formats_rtx5060-laptop.csv")
    a = ap.parse_args()

    plans = {}
    for r in csv.DictReader(open(ROOT + "results/compare_plans.csv")):
        plans.setdefault(r["shape"], {})[r["role"]] = r
    flush = C.make_flusher()
    kvf = C.KvForgeKernels()
    kn = Kernels()
    rows = []
    rejected = []
    print("torch", torch.__version__, "|", torch.cuda.get_device_name(0), flush=True)
    for shape in sorted(plans):
        if a.only and a.only not in shape:
            continue
        H, Hkv, d, n, B = C.parse_shape(shape)
        g = H // Hkv
        torch.manual_seed(1)
        q = torch.randn(B, H, d, device="cuda", dtype=torch.float32)
        K = torch.randn(B, Hkv, n, d, device="cuda", dtype=torch.float16)
        V = torch.randn(B, Hkv, n, d, device="cuda", dtype=torch.float16)
        ref = C.reference(q, K, V, H, Hkv, d)
        print("\n%s" % shape, flush=True)
        cands = []   # (name, fn, err, note); every candidate is checked when it is built
        keep = []

        # anchors: KVForge's fp16 pick (the frozen kernels), FlashInfer fp16 and fp8
        out = torch.zeros(B, H, d, device="cuda")
        part_o = torch.zeros(B, H, 64, d, device="cuda")
        part_ml = torch.zeros(B, H, 64, 2, device="cuda")
        p = plans[shape]["kvforge_pick"]
        Kp, Vp = (K, V) if p["order"] == "head_major" else (K.permute(0, 2, 1, 3).contiguous(), V.permute(0, 2, 1, 3).contiguous())
        fn = kvf.make(p, q, Kp, Vp, out, part_o, part_ml, B, H, Hkv, n, d)
        fn(); torch.cuda.synchronize()
        cands.append(("kvforge_f16_pick", fn, C.rel_l2(out, ref), "frozen kernels, compiler pick"))
        keep += [Kp, Vp]
        fi = C.flashinfer_candidates(q, K, V, H, Hkv, d, B, n)
        fi.update(flashinfer_fp8(q, K, V, H, Hkv, d, B, n))
        for name, (fn, r) in fi.items():
            if fn is None:
                print("  %-34s unavailable: %s" % (name, r), flush=True)
                continue
            cands.append((name, fn, C.rel_l2(r, ref), ""))

        for v in variants(d, g):
            if a.variants and v["name"] not in a.variants.split(","):
                continue
            R = v["R"]
            t = {"q": q, "q_lr": torch.zeros(B, H, R, device="cuda"), "out": torch.zeros(B, H, d, device="cuda"),
                 "out_r": torch.zeros(B, H, d, device="cuda"),
                 "part_o": torch.zeros(B, H, 64, d, device="cuda"), "part_ml": torch.zeros(B, H, 64, 2, device="cuda")}
            if v["qmode"] in ("rot", "rotf"):
                Hm = hadamard(d, 7, "cuda")
                t["signs"] = (Hm[:, 0] * math.sqrt(d)).contiguous()
                t["Bp"] = Hm.expand(Hkv, d, d).contiguous()             # q_rot = q @ H
                t["Hinv"] = Hm.T.expand(Hkv, d, d).contiguous()         # out = out_rot @ H^T
                kstore, vstore = (K.float() @ Hm).half(), (V.float() @ Hm).half()
            elif v["qmode"] == "proj":
                t["Bp"] = torch.linalg.qr(torch.randn(Hkv, d, R, device="cuda", dtype=torch.float64))[0].float().contiguous()
                kstore, vstore = torch.randn(B, Hkv, n, R, device="cuda", dtype=torch.float16), V
            else:
                kstore, vstore = K, V
            bits = {"int8": 8, "int4": 4}
            if v["kf"] == "f16":
                t["k"], kd = kstore.contiguous(), kstore
            else:
                t["k"], t["k_meta"], kd = quant(kstore, bits[v["kf"]], 1 << v["kgs"])
            if v["vf"] == "f16":
                t["v"], vd = vstore.contiguous(), vstore
            else:
                t["v"], t["v_meta"], vd = quant(vstore, bits[v["vf"]], 1 << v["vgs"])
            del kstore, vstore
            if v["qmode"] == "none":
                vref = ref_attn(q, kd, vd, H, Hkv, d)
            elif v["qmode"] != "rotf":
                qx = torch.einsum("bhgd,hdr->bhgr", q.view(B, Hkv, g, d), t["Bp"]).reshape(B, H, R)
                vref = ref_attn(qx, kd, vd, H, Hkv, d)
                if v["qmode"] == "rot":
                    vref = vref @ Hm.T
            if v["qmode"] == "rotf":
                qx = (q.view(B * H, d) @ Hm).view(B, H, d)
                vref = ref_attn(qx, kd, vd, H, Hkv, d) @ Hm.T
            del kd, vd

            # quick search, then the six best re-timed interleaved
            quick = []
            for splits in ((2, 4, 8, 16, 32) if v["qmode"] == "rotf" else (1, 2, 4, 8, 16, 32)):
                for G in ([g] if v.get("tc") else sorted({1, g})):
                    if G > 8:
                        continue
                    for U in ((1, 2, 0) if v.get("tc") else (2, 4, 8)):   # tc U = 0: pipelined
                        for warps in (4, 8):
                            fn = kn.make(v, (splits, G, U, warps), t, B, H, Hkv, n, d)
                            t["out"].zero_()
                            fn(); torch.cuda.synchronize()
                            e = C.rel_l2(t["out"], vref)
                            if not e < 1e-2:   # every plan is verified, not only the winner
                                rejected.append("%s splits=%d G=%d U=%d w%d err=%.2e" % (v["name"], splits, G, U, warps, e))
                                continue
                            quick.append((C.bench(fn, flush, a.search_reps, warmup=2)[0], (splits, G, U, warps)))
            quick.sort()
            fins = [cfg for _, cfg in quick[:6]]
            tt = timed_interleaved([kn.make(v, cfg, t, B, H, Hkv, n, d) for cfg in fins], flush, 9)
            med = [sorted(x)[len(x) // 2] for x in tt]
            plan = fins[med.index(min(med))]
            fn = kn.make(v, plan, t, B, H, Hkv, n, d)
            t["out"].zero_()
            fn(); torch.cuda.synchronize()
            cands.append(("kvforge_" + v["name"], fn, C.rel_l2(t["out"], vref),
                          "splits=%d pack=%d u%d w%d" % (plan[0], int(plan[1] > 1), plan[2], plan[3])))
            keep += [t, vref]

        clk0 = mem_clock()
        tt = timed_interleaved([c[1] for c in cands], flush, 3 + a.reps)
        clk1 = mem_clock()
        print("  memory clock %s -> %s MHz" % (clk0, clk1), flush=True)
        for (name, fn, err, note), ts in zip(cands, tt):
            ts = sorted(ts[3:])
            med, p25, p75 = ts[len(ts) // 2], ts[len(ts) // 4], ts[(3 * len(ts)) // 4]
            print("  %-34s %9.1f us  (IQR %.1f..%.1f)  err %.2e  %s" % (name, med, p25, p75, err, note), flush=True)
            rows.append({"shape": shape, "method": name, "t_us": "%.2f" % med, "p25": "%.2f" % p25, "p75": "%.2f" % p75,
                         "err": "%.3e" % err, "note": note, "mem_clock": "%s/%s" % (clk0, clk1)})
        del cands, keep, fi, q, K, V, ref
        torch.cuda.empty_cache()

    print("\nplans rejected by the output check: %d" % len(rejected))
    for r in rejected:
        print("  " + r)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["shape", "method", "t_us", "p25", "p75", "err", "note", "mem_clock"])
        w.writeheader()
        w.writerows(rows)
    print("\nwrote", a.out)


if __name__ == "__main__":
    main()
