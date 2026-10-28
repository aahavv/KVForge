"""Low-rank and quantized KV caches on a real model: how much accuracy each costs.

Every attention layer of the model is routed through one hook. The hook sees the
keys after RoPE (what a decode kernel stores) and the values, replaces them with
what a given cache format would give back, and runs the usual attention. The
score is end-to-end perplexity on WikiText-2, plus the relative error of the
attention output itself (the quantity KVForge's accuracy gate bounds).

Formats
  f16                      reference (the model's own bf16)
  fp8                      e4m3, one dynamic scale per layer (FlashInfer's fp8 cache)
  int8:G / int4:G          KVForge's per-group asymmetric formats
  lr<r>[q]  (+ int8)       keys stored as r coefficients c = A^T k; scores use
                           (B^T q) . c. Plain = PCA of the keys; "q" = query-aware
                           (PCA after whitening by the query covariance).

Projections are fitted on WikiText-2 train, scored on WikiText-2 test.

    ~/kvbench/bin/python bench/wsl/lowrank/study.py [--model Qwen/Qwen3-1.7B]
"""
import argparse
import json
import math
import os
import time

import torch
from datasets import load_dataset
from transformers import AttentionInterface, AutoModelForCausalLM, AutoTokenizer
from transformers.integrations.sdpa_attention import sdpa_attention_forward

ROOT = "/mnt/c/Users/aahav/KVForge/"


# ----------------------------------------------------------------- formats
def quant_group(x, bits, group):
    """KVForge int<bits>:<group>: asymmetric min/max per group of the last dim."""
    sh = x.shape
    g = x.float().reshape(*sh[:-1], sh[-1] // group, group)
    mn, mx = g.amin(-1, keepdim=True), g.amax(-1, keepdim=True)
    scale = ((mx - mn) / (2 ** bits - 1)).clamp_min(1e-8)
    q = torch.round((g - mn) / scale).clamp(0, 2 ** bits - 1)
    return (q * scale + mn).reshape(sh).to(x.dtype)


def fp8(x):
    s = x.float().abs().amax().clamp_min(1e-8) / 448.0
    return ((x.float() / s).to(torch.float8_e4m3fn).float() * s).to(x.dtype)


class State:
    mode = "off"            # off | calib | eval
    kfmt = "f16"            # f16 | fp8 | int8 | int4
    vfmt = "f16"
    group = 32
    rank = 0                # 0 = keys not projected
    proj = None             # layer -> (A [Hkv,d,r], B [Hkv,d,r]); score = (B^T q).(A^T k)
    cov = {}                # calibration accumulators
    err = {}                # layer -> [sum of rel err, count]
    rot = False             # randomized Hadamard rotation of q, k, v (output rotated back)
    kgroup = None           # quantization group for keys / values (None = group)
    vgroup = None


S = State()


def coef_group(r):
    return S.group if r % S.group == 0 else 16


def apply_fmt(x, fmt, group=None):
    if fmt == "f16":
        return x
    if fmt == "fp8":
        return fp8(x)
    return quant_group(x, 8 if fmt == "int8" else 4, min(group or S.group, x.shape[-1]))


_HAD = {}


def hadamard(d, layer, device):
    """Randomized Hadamard matrix (orthonormal), one sign pattern per layer."""
    if (d, layer) not in _HAD:
        Hm = torch.ones(1, 1)
        while Hm.shape[0] < d:
            Hm = torch.cat([torch.cat([Hm, Hm], 1), torch.cat([Hm, -Hm], 1)], 0)
        gen = torch.Generator().manual_seed(1000 + layer)
        signs = torch.randint(0, 2, (d,), generator=gen).float() * 2 - 1
        _HAD[(d, layer)] = ((torch.diag(signs) @ Hm) / math.sqrt(d)).to(device)
    return _HAD[(d, layer)]


def kvf_attention(module, query, key, value, attention_mask, **kw):
    """query [B,H,T,d], key/value [B,Hkv,T,d], post-RoPE."""
    li = module.layer_idx
    Hkv = key.shape[1]
    g = query.shape[1] // Hkv
    if S.mode == "calib":
        kf = key.float().transpose(0, 1).reshape(Hkv, -1, key.shape[-1])
        vf = value.float().transpose(0, 1).reshape(Hkv, -1, value.shape[-1])
        qf = query.float().view(query.shape[0], Hkv, g, -1, query.shape[-1]).transpose(0, 1).reshape(Hkv, -1, query.shape[-1])
        for name, t in (("k", kf), ("v", vf), ("q", qf)):
            c = torch.einsum("hnd,hne->hde", t.double(), t.double())
            key_ = (li, name)
            S.cov[key_] = S.cov.get(key_, 0) + c
        return sdpa_attention_forward(module, query, key, value, attention_mask, **kw)
    if S.mode != "eval":
        return sdpa_attention_forward(module, query, key, value, attention_mask, **kw)

    q2, k2 = query, key
    if S.rot:
        # orthogonal rotation of the head dimension: q.k and the attention output are
        # unchanged before quantization; the rotation spreads outlier channels
        Hm = hadamard(query.shape[-1], li, query.device)
        q2 = (query.float() @ Hm).to(query.dtype)
        k2 = apply_fmt((key.float() @ Hm).to(key.dtype), S.kfmt, S.kgroup)
        v2 = apply_fmt((value.float() @ Hm).to(value.dtype), S.vfmt, S.vgroup)
        out_r, w = sdpa_attention_forward(module, q2, k2, v2, attention_mask, **kw)   # [B,T,H,d]
        out = (out_r.float() @ Hm.T).to(out_r.dtype)
        if S.sample_err:
            ref, _ = sdpa_attention_forward(module, query, key, value, attention_mask, **kw)
            e = (torch.linalg.vector_norm((out - ref).float()) / torch.linalg.vector_norm(ref.float())).item()
            acc = S.err.setdefault(li, [0.0, 0])
            acc[0] += e
            acc[1] += 1
        return out, w
    if S.rank:
        A, Bm = S.proj[li]                                       # [Hkv,d,r]
        c = torch.einsum("bhtd,hdr->bhtr", key.float(), A)        # stored coefficients
        c = apply_fmt(c.to(key.dtype), S.kfmt, coef_group(S.rank)).float() if S.kfmt != "f16" else c
        qh = query.float().view(query.shape[0], Hkv, g, query.shape[2], -1)
        qt = torch.einsum("bhgtd,hdr->bhgtr", qh, Bm).reshape(query.shape[0], Hkv * g, query.shape[2], -1)
        # scores must keep the original 1/sqrt(d) scale: pass it explicitly
        q2, k2 = qt.to(query.dtype), c.to(key.dtype)
        kw = dict(kw)
        kw["scaling"] = kw.get("scaling") or 1.0 / math.sqrt(query.shape[-1])
    else:
        k2 = apply_fmt(key, S.kfmt, S.kgroup)
    v2 = apply_fmt(value, S.vfmt, S.vgroup)
    out, w = sdpa_attention_forward(module, q2, k2, v2, attention_mask, **kw)
    if S.sample_err:
        ref, _ = sdpa_attention_forward(module, query, key, value, attention_mask, **kw)
        e = (torch.linalg.vector_norm((out - ref).float()) / torch.linalg.vector_norm(ref.float())).item()
        acc = S.err.setdefault(li, [0.0, 0])
        acc[0] += e
        acc[1] += 1
    return out, w


S.sample_err = True
AttentionInterface.register("kvf", kvf_attention)


# ----------------------------------------------------------------- projections
def fit_projections(rank, query_aware, nlayers):
    proj = {}
    for li in range(nlayers):
        Ck = S.cov[(li, "k")]                                    # [Hkv,d,d]
        Hkv, d, _ = Ck.shape
        A = torch.empty(Hkv, d, rank, dtype=torch.float64, device=Ck.device)
        Bm = torch.empty_like(A)
        for h in range(Hkv):
            if not query_aware:
                ev, U = torch.linalg.eigh(Ck[h])
                Ur = U[:, -rank:]
                A[h], Bm[h] = Ur, Ur
            else:
                Cq = S.cov[(li, "q")][h]
                Cq = Cq / Cq.trace() * d + 1e-4 * torch.eye(d, dtype=Cq.dtype, device=Cq.device)
                eq, Uq = torch.linalg.eigh(Cq)
                half = Uq @ torch.diag(eq.sqrt()) @ Uq.T          # Sigma_q^{1/2}
                ihalf = Uq @ torch.diag(eq.rsqrt()) @ Uq.T
                M = half @ Ck[h] @ half
                ev, U = torch.linalg.eigh(M)
                Ur = U[:, -rank:]
                A[h] = half @ Ur                                  # c = Ur^T Sigma^{1/2} k
                Bm[h] = ihalf @ Ur                                # q~ = Ur^T Sigma^{-1/2} q
        proj[li] = (A.float(), Bm.float())
    return proj


def spectra(nlayers):
    """Fraction of key / value energy kept at rank r, averaged over layers and heads."""
    out = {}
    for name in ("k", "v"):
        fr = []
        for li in range(nlayers):
            ev = torch.linalg.eigvalsh(S.cov[(li, name)]).flip(-1).clamp_min(0)   # [Hkv,d]
            cum = ev.cumsum(-1) / ev.sum(-1, keepdim=True)
            fr.append(cum)
        fr = torch.stack(fr)                                      # [L,Hkv,d]
        d = fr.shape[-1]
        out[name] = {str(r): float(fr[:, :, r - 1].mean()) for r in (8, 16, 32, 48, 64, 96, 112) if r < d}
        out[name + "_min_layer_at_half"] = float(fr[:, :, d // 2 - 1].mean(-1).min())
    return out


# ----------------------------------------------------------------- data, ppl
def windows(tok, split, seq, count):
    ds = load_dataset("Salesforce/wikitext", "wikitext-2-raw-v1", split=split)
    ids = tok("\n\n".join(ds["text"]), return_tensors="pt").input_ids[0]
    n = min(count, ids.numel() // seq)
    return [ids[i * seq:(i + 1) * seq] for i in range(n)]


@torch.no_grad()
def run(model, wins, label=None):
    nll, cnt = 0.0, 0
    for w in wins:
        x = w.unsqueeze(0).cuda()
        logits = model(x).logits.float()
        lp = torch.log_softmax(logits[0, :-1], -1)
        nll -= lp.gather(1, x[0, 1:, None]).sum().item()
        cnt += x.numel() - 1
    return math.exp(nll / cnt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3-1.7B")
    ap.add_argument("--seq", type=int, default=2048)
    ap.add_argument("--calib", type=int, default=16)
    ap.add_argument("--evalw", type=int, default=40)
    ap.add_argument("--out", default="")
    ap.add_argument("--suite", default="lowrank", choices=["lowrank", "rot", "groups"])
    a = ap.parse_args()
    tag = a.model.split("/")[-1].lower()
    a.out = a.out or ROOT + "results/lowrank/study_%s_%s.json" % (a.suite, tag)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)

    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16, attn_implementation="kvf").cuda().eval()
    cfg = model.config
    L, H, Hkv = cfg.num_hidden_layers, cfg.num_attention_heads, cfg.num_key_value_heads
    d = getattr(cfg, "head_dim", cfg.hidden_size // H)
    print("model", a.model, "layers", L, "H", H, "Hkv", Hkv, "d", d, flush=True)

    cal = windows(tok, "train", a.seq, a.calib)
    ev = windows(tok, "test", a.seq, a.evalw)
    print("calib windows", len(cal), "eval windows", len(ev), flush=True)

    S.mode = "calib"
    t0 = time.time()
    run(model, cal)
    print("calibrated in %.0fs" % (time.time() - t0), flush=True)
    spec = spectra(L)
    print("energy kept (keys):  ", spec["k"], flush=True)
    print("energy kept (values):", spec["v"], flush=True)

    if a.suite in ("rot", "groups"):
        return run_rot_suite(model, ev, d, a)

    configs = [("f16", "f16", 0, False), ("fp8", "fp8", 0, False), ("int8", "int8", 0, False),
               ("int4", "int4", 0, False), ("int4", "int8", 0, False)]
    for r in (32, 48, 64, 96):
        configs += [("f16", "f16", r, False), ("f16", "f16", r, True)]
    for r in (48, 64, 96):
        configs += [("int8", "int8", r, True)]
    configs += [("fp8", "fp8", 64, True)]

    S.mode = "eval"
    results = []
    projcache = {}
    for kf, vf, r, qa in configs:
        S.kfmt, S.vfmt, S.rank = kf, vf, r
        if r:
            if (r, qa) not in projcache:
                projcache[(r, qa)] = fit_projections(r, qa, L)
            S.proj = projcache[(r, qa)]
        S.err = {}
        t0 = time.time()
        ppl = run(model, ev)
        errs = [s / c for s, c in S.err.values()]
        kbytes = (r if r else d) * {"f16": 2, "fp8": 1, "int8": 1, "int4": 0.5}[kf]
        vbytes = d * {"f16": 2, "fp8": 1, "int8": 1, "int4": 0.5}[vf]
        if kf in ("int8", "int4"):
            kbytes += (r if r else d) / (coef_group(r) if r else S.group) * 4
        if vf in ("int8", "int4"):
            vbytes += d / S.group * 4
        name = ("K:%s" % kf) + ("+lr%d%s" % (r, "q" if qa else "") if r else "") + " V:%s" % vf
        row = {"config": name, "kfmt": kf, "vfmt": vf, "rank": r, "query_aware": qa, "ppl": ppl,
               "attn_rel_err_mean": sum(errs) / len(errs), "attn_rel_err_max_layer": max(errs),
               "bytes_per_token_head": kbytes + vbytes, "bytes_vs_f16": (kbytes + vbytes) / (4 * d)}
        results.append(row)
        print("%-28s ppl %.4f  attn err mean %.4f max-layer %.4f  bytes %.3fx f16   (%.0fs)" % (
            name, ppl, row["attn_rel_err_mean"], row["attn_rel_err_max_layer"], row["bytes_vs_f16"], time.time() - t0), flush=True)

    # Projections used by the kernel benchmark (one layer is enough for timing data).
    json.dump({"model": a.model, "layers": L, "H": H, "Hkv": Hkv, "d": d, "seq": a.seq,
               "calib_windows": len(cal), "eval_windows": len(ev), "group": S.group,
               "spectra": spec, "results": results}, open(a.out, "w"), indent=1)
    print("wrote", a.out)


def run_rot_suite(model, ev, d, a):
    """Rotation + quantization. (label, rot, kfmt, kgroup, vfmt, vgroup)."""
    S.mode = "eval"
    S.rank = 0
    configs = [("f16", False, "f16", 32, "f16", 32), ("fp8 (FlashInfer)", False, "fp8", 32, "fp8", 32),
               ("int8:32", False, "int8", 32, "int8", 32), ("int8:128", False, "int8", 128, "int8", 128),
               ("int4:32", False, "int4", 32, "int4", 32),
               ("rot int8:128", True, "int8", 128, "int8", 128),
               ("rot int4:32", True, "int4", 32, "int4", 32), ("rot int4:16", True, "int4", 16, "int4", 16),
               ("rot int4:64", True, "int4", 64, "int4", 64),
               ("rot K int8:64 V int4:32", True, "int8", 64, "int4", 32),
               ("rot K int4:32 V int8:64", True, "int4", 32, "int8", 64),
               ("K int8:32 V int4:32 (no rot)", False, "int8", 32, "int4", 32)]
    if a.suite == "groups":   # larger groups: less scale/zero metadata per row
        configs = [("f16", False, "f16", 32, "f16", 32), ("fp8 (FlashInfer)", False, "fp8", 32, "fp8", 32),
                   ("K int8:32 V int4:32", False, "int8", 32, "int4", 32),
                   ("K int8:64 V int4:32", False, "int8", 64, "int4", 32),
                   ("K int8:64 V int4:64", False, "int8", 64, "int4", 64),
                   ("K int8:128 V int4:64", False, "int8", 128, "int4", 64),
                   ("K int8:128 V int4:128", False, "int8", 128, "int4", 128),
                   ("rot K int8:64 V int4:64", True, "int8", 64, "int4", 64),
                   ("rot K int8:128 V int4:64", True, "int8", 128, "int4", 64),
                   ("rot K int8:128 V int4:128", True, "int8", 128, "int4", 128)]
    per_byte = {"f16": 2, "fp8": 1, "int8": 1, "int4": 0.5}
    results = []
    for label, rot, kf, kg, vf, vg in configs:
        S.rot, S.kfmt, S.kgroup, S.vfmt, S.vgroup = rot, kf, kg, vf, vg
        S.err = {}
        t0 = time.time()
        ppl = run(model, ev)
        errs = [s_ / c for s_, c in S.err.values()]
        kb = d * per_byte[kf] + (d / min(kg, d) * 4 if kf.startswith("int") else 0)
        vb = d * per_byte[vf] + (d / min(vg, d) * 4 if vf.startswith("int") else 0)
        row = {"config": label, "rot": rot, "kfmt": kf, "kgroup": kg, "vfmt": vf, "vgroup": vg, "ppl": ppl,
               "attn_rel_err_mean": sum(errs) / len(errs), "attn_rel_err_max_layer": max(errs),
               "bytes_vs_f16": (kb + vb) / (4 * d)}
        results.append(row)
        print("%-30s ppl %.4f  attn err mean %.4f max-layer %.4f  bytes %.3fx f16   (%.0fs)" % (
            label, ppl, row["attn_rel_err_mean"], row["attn_rel_err_max_layer"], row["bytes_vs_f16"], time.time() - t0), flush=True)
    S.rot = False
    json.dump({"model": a.model, "d": d, "seq": a.seq, "eval_windows": len(ev), "results": results}, open(a.out, "w"), indent=1)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
