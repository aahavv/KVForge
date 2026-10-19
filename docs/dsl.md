# The KVForge specification language

A `.kv` file describes one decode-attention layer. A field written `?` is one the
compiler is free to choose, so a program declares its own search space. Pin every
field and you get the hand-written baseline the searched plans have to beat; the
two programs differ only by question marks.

```
target machine = "machines/rtx5060-laptop.gpu"
target calib   = "model/constants.cal"
target max_rel_err = 0.02

decode llama3_8b(H: 32, H_kv: 8, d: 128, n: 32768, batch: 1) {
  Q: query<H, d, f32>
  K: kvcache<n, d, ?, ?, ?>
  V: kvcache<n, d, ?, ?, ?>
  O = decode_attn(Q, K, V, scale = auto, splits = ?, gqa_pack = ?)
}
```

## Grammar

```
program   := (target | decode)+
target    := "target" key "=" (number | string)
decode    := "decode" name "(" "H" ":" int "," "H_kv" ":" int "," "d" ":" int ","
             "n" ":" int ["," "batch" ":" int] ")" "{" decl* attn "}"
decl      := name ":" query | name ":" kvcache
query     := "query" "<" "H" "," "d" "," "f32" ">"
kvcache   := "kvcache" "<" "n" "," "d" "," format "," order "," residency ">"
attn      := name "=" "decode_attn" "(" name "," name "," name
             ["," "scale" "=" ("auto" | number)]
             ["," "splits" "=" (int | "?")]
             ["," "gqa_pack" "=" ("true" | "false" | "?")] ")"
format    := "?" | "f16" | "int8" [":" G] | "int4" [":" G]
order     := "?" | "head_major" | "token_major"
residency := "?" | "contiguous" | "paged" [":" B]
```

Comments start with `#` or `//`.

## Fields

| Field | Values | Meaning |
| --- | --- | --- |
| `format` | `f16`, `int8:G`, `int4:G` | Storage format. `G` is the quantization group (32, 64 or 128) and must divide `d`. `f16` is lossless; `int8` and `int4` are lossy. |
| `order` | `head_major`, `token_major` | `K[b][h][t][c]` versus `K[b][t][h][c]`. |
| `residency` | `contiguous`, `paged:B` | One flat region per sequence, or blocks of `B` tokens (16, 32, 64, 128) behind a block table. |
| `splits` | integer or `?` | Chunks the KV length is cut into (split-KV). |
| `gqa_pack` | `true`, `false`, `?` | One block serves all `g` query heads of a KV group. Needs `g` = 2, 4 or 8. |

`splits` and `gqa_pack` are independent: pinning one never frees or ignores the
other.

## Targets

| Key | Meaning |
| --- | --- |
| `machine = "path"` | GPU description file, written by `bw_probe`. |
| `calib = "path"` | Frozen cost-model constants (see `kvf calibrate`). |
| `max_rel_err = X` | Accuracy budget. Lossy formats are searched only when this is set, and a lossy plan is rejected if its calibrated relative error exceeds `X`. |
| `include_quantized = 1` | Search lossy formats without a stated budget. |
| `max_splits = N` | Cap on the split count (default 64). |
| any machine key | Overrides one value of the machine file, e.g. `sms = 20`. |

## Restrictions in this release

* `d` is 64 or 128.
* K and V share a format and a layout, so both must pin or both must leave `?`.
* The query is always `f32`.
* Quantization groups run along the head dimension within one token.
