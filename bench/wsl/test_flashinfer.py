"""Smallest FlashInfer decode call that uses a pre-built kernel: does it run here?"""
import time

import torch
import flashinfer

print("flashinfer", flashinfer.__version__)
B, H, Hkv, d, n, ps = 1, 32, 8, 128, 4096, 16
pages = n // ps
q = torch.randn(B, H, d, device="cuda", dtype=torch.float16)
K = torch.randn(B, Hkv, n, d, device="cuda", dtype=torch.float16)
V = torch.randn(B, Hkv, n, d, device="cuda", dtype=torch.float16)
kc = K.view(B, Hkv, pages, ps, d).permute(0, 2, 1, 3, 4).reshape(B * pages, Hkv, ps, d).contiguous()
vc = V.view(B, Hkv, pages, ps, d).permute(0, 2, 1, 3, 4).reshape(B * pages, Hkv, ps, d).contiguous()
indptr = torch.arange(B + 1, dtype=torch.int32, device="cuda") * pages
indices = torch.arange(B * pages, dtype=torch.int32, device="cuda")
last = torch.full((B,), ps, dtype=torch.int32, device="cuda")
ws = torch.empty(128 << 20, dtype=torch.uint8, device="cuda")
ref = torch.nn.functional.scaled_dot_product_attention(
    q.view(B, H, 1, d).float(), K.float(), V.float(), enable_gqa=True).view(B, H, d)

for tc in (False, True):
    t0 = time.time()
    try:
        w = flashinfer.BatchDecodeWithPagedKVCacheWrapper(ws, kv_layout="HND", use_tensor_cores=tc)
        w.plan(indptr, indices, last, H, Hkv, d, ps, pos_encoding_mode="NONE",
               data_type=torch.float16, q_data_type=torch.float16)
        o = w.run(q, (kc, vc))
        torch.cuda.synchronize()
        err = float((o.float() - ref).abs().max())
        print("use_tensor_cores=%s: ok, first call %.1f s, max abs error vs fp32 SDPA %.2e" % (tc, time.time() - t0, err))
    except Exception as e:
        print("use_tensor_cores=%s: FAILED: %s" % (tc, str(e).split("\n")[0][:160]))
