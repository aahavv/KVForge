// sweep - time every plan of a design space on the local GPU.
//
// Input is the plans.csv written by `kvf plan <shape.kv> --all`: one row per
// candidate the compiler enumerated for that shape. For each plan the harness
// builds the cache in the plan's format and layout, runs the kernel the
// compiler generated for it (through the dispatch registry), checks the output
// against a double-precision reference, and times it.
//
// This is ground truth for the cost model: the fit uses one machine's sweeps,
// and the transfer experiment compares predictions against another's.
//
//   sweep --plans plans.csv[,more.csv] --out sweep.csv
//         [--reps 25] [--warmup 5] [--seed 1] [--limit N] [--device 0]
#include "kvf_host.h"
#include "kvf_registry.h"

#include <fstream>
#include <map>
#include <sstream>
#include <tuple>

using namespace kvf;

namespace {

std::vector<std::string> split(const std::string &s, char sep) {
  std::vector<std::string> out;
  std::string cur;
  for (char c : s) {
    if (c == sep) { out.push_back(cur); cur.clear(); }
    else if (c != '\r') cur.push_back(c);
  }
  out.push_back(cur);
  return out;
}

struct PlanRow {
  std::string name;
  int H, Hkv, D, n, batch;
  std::string fmt;
  int group;
  std::string order, residency;
  int bt, splits, pack, warps, unroll;
};

std::vector<PlanRow> read_plans(const std::string &path) {
  std::ifstream in(path);
  if (!in) { std::fprintf(stderr, "cannot read %s\n", path.c_str()); std::exit(2); }
  std::string line;
  std::getline(in, line);
  const auto head = split(line, ',');
  std::map<std::string, size_t> col;
  for (size_t i = 0; i < head.size(); ++i) col[head[i]] = i;
  std::vector<PlanRow> rows;
  while (std::getline(in, line)) {
    if (line.empty()) continue;
    const auto f = split(line, ',');
    auto I = [&](const char *k) { return std::stoi(f.at(col.at(k))); };
    auto S = [&](const char *k) { return f.at(col.at(k)); };
    PlanRow r;
    r.name = S("name"); r.H = I("H"); r.Hkv = I("H_kv"); r.D = I("d"); r.n = I("n");
    r.batch = I("batch"); r.fmt = S("fmt"); r.group = I("group"); r.order = S("order");
    r.residency = S("residency"); r.bt = I("block_tokens"); r.splits = I("splits");
    r.pack = I("gqa_pack"); r.warps = I("warps"); r.unroll = I("unroll");
    rows.push_back(r);
  }
  return rows;
}

FormatSel fmt_of(const PlanRow &r) {
  FormatSel f;
  f.fmt = r.fmt == "f16" ? FMT_F16 : r.fmt == "int8" ? FMT_INT8 : FMT_INT4;
  f.group = r.group;
  return f;
}

LayoutSel layout_of(const PlanRow &r) {
  LayoutSel l;
  l.order = r.order == "head_major" ? ORD_HEAD : ORD_TOKEN;
  l.paged = r.residency == "paged";
  l.bt = l.paged ? r.bt : 0;
  return l;
}

std::string variant_id(const PlanRow &r, int g) {
  std::ostringstream o;
  o << r.fmt << "_" << (r.order == "head_major" ? "hm" : "tm") << "_"
    << (r.residency == "paged" ? "p" : "c") << "_g" << (r.pack ? g : 1) << "_u"
    << r.unroll << "_d" << r.D;
  return o.str();
}

} // namespace

int main(int argc, char **argv) {
  std::string plans_arg, out_path = "sweep.csv";
  int reps = 25, warmup = 5, limit = 0, dev = 0;
  uint64_t seed = 1;
  for (int i = 1; i < argc; ++i) {
    const std::string a = argv[i];
    auto next = [&]() -> std::string {
      if (i + 1 >= argc) { std::fprintf(stderr, "%s needs a value\n", a.c_str()); std::exit(2); }
      return argv[++i];
    };
    if (a == "--plans") plans_arg = next();
    else if (a == "--out") out_path = next();
    else if (a == "--reps") reps = std::stoi(next());
    else if (a == "--warmup") warmup = std::stoi(next());
    else if (a == "--limit") limit = std::stoi(next());
    else if (a == "--seed") seed = std::stoull(next());
    else if (a == "--device") dev = std::stoi(next());
    else { std::fprintf(stderr, "unknown option %s\n", a.c_str()); return 2; }
  }
  if (plans_arg.empty()) {
    std::fprintf(stderr, "usage: sweep --plans plans.csv[,more.csv] --out sweep.csv\n");
    return 2;
  }
  KVF_CUDA_CHECK(cudaSetDevice(dev));
  cudaDeviceProp prop;
  KVF_CUDA_CHECK(cudaGetDeviceProperties(&prop, dev));
  std::printf("device %s (cc %d.%d, %d SMs)\n", prop.name, prop.major, prop.minor,
              prop.multiProcessorCount);

  Registry reg;
  kvf_register_all(reg);
  std::printf("registry: %zu variants\n", reg.fn.size());

  FILE *out = std::fopen(out_path.c_str(), "w");
  if (!out) { std::fprintf(stderr, "cannot write %s\n", out_path.c_str()); return 1; }
  std::fprintf(out, "name,H,H_kv,d,n,batch,fmt,group,order,residency,block_tokens,splits,"
                    "gqa_pack,warps,unroll,t_us,t_p25,t_p75,t_min,reps,err_exact,err_ref,"
                    "verified,device\n");

  long long done = 0, skipped = 0, unverified = 0;
  for (const std::string &pf : split(plans_arg, ',')) {
    std::vector<PlanRow> plans = read_plans(pf);
    if (plans.empty()) continue;
    if (limit > 0 && (int)plans.size() > limit) plans.resize(limit);
    Shape s;
    s.B = plans[0].batch; s.H = plans[0].H; s.Hkv = plans[0].Hkv; s.D = plans[0].D;
    s.n = plans[0].n;
    std::printf("\nshape %s: B=%d H=%d Hkv=%d D=%d n=%d, %zu plans\n", plans[0].name.c_str(),
                s.B, s.H, s.Hkv, s.D, s.n, plans.size());

    std::vector<float> q, K, V;
    make_data(s, seed, q, K, V);
    const float scale = 1.0f / std::sqrt((float)s.D);
    const std::vector<float> exact = reference_attention(s, q, K, V, scale);

    int max_splits = 1;
    for (const auto &p : plans) max_splits = std::max(max_splits, p.splits);
    const size_t flush = std::max<size_t>(96u << 20, (size_t)prop.l2CacheSize * 3);
    DeviceBuffers dbuf = alloc_buffers(s, max_splits, flush, q);
    std::vector<float> got((size_t)s.B * s.H * s.D);

    // Group plans so each (format, layout) cache is built once.
    std::map<std::tuple<std::string, int, std::string, std::string, int>, std::vector<size_t>> groups;
    for (size_t i = 0; i < plans.size(); ++i) {
      const auto &p = plans[i];
      groups[{p.fmt, p.group, p.order, p.residency, p.bt}].push_back(i);
    }

    std::string cur_fmt_key;
    Quantized Kq, Vq;
    std::vector<float> ref;
    for (auto &gk : groups) {
      const PlanRow &p0 = plans[gk.second[0]];
      const FormatSel f = fmt_of(p0);
      const LayoutSel l = layout_of(p0);
      const std::string fkey = p0.fmt + ":" + std::to_string(p0.group);
      if (fkey != cur_fmt_key) {
        Kq = quantize(f, s.D, K, s.rows());
        Vq = quantize(f, s.D, V, s.rows());
        ref = reference_attention(s, q, Kq.deq, Vq.deq, scale);
        cur_fmt_key = fkey;
      }
      Cache cache = upload_cache(s, f, l, Kq, Vq, seed + 17);
      for (size_t idx : gk.second) {
        const PlanRow &p = plans[idx];
        LaunchFn fn = reg.find(variant_id(p, s.H / s.Hkv));
        if (!fn) { ++skipped; continue; }
        Args a = make_args(s, f, l, cache, dbuf, p.splits, p.warps);
        KVF_CUDA_CHECK(cudaMemset(dbuf.out, 0, got.size() * 4));
        cudaError_t e = fn(a, 0);
        if (e == cudaSuccess) e = cudaDeviceSynchronize();
        if (e != cudaSuccess) {
          std::fprintf(stderr, "launch failed (%s) for %s\n", cudaGetErrorString(e),
                       variant_id(p, s.H / s.Hkv).c_str());
          cudaGetLastError();
          ++skipped;
          continue;
        }
        KVF_CUDA_CHECK(cudaMemcpy(got.data(), dbuf.out, got.size() * 4, cudaMemcpyDeviceToHost));
        const double err_ref = rel_l2(got, ref);
        const double err_exact = rel_l2(got, exact);
        const bool ok = err_ref < 2e-3;
        if (!ok) ++unverified;
        const TimeStats t = time_launch([&] { fn(a, 0); }, dbuf, warmup, reps);
        std::fprintf(out, "%s,%d,%d,%d,%d,%d,%s,%d,%s,%s,%d,%d,%d,%d,%d,%.3f,%.3f,%.3f,%.3f,%d,%.6g,%.6g,%d,%s\n",
                     p.name.c_str(), p.H, p.Hkv, p.D, p.n, p.batch, p.fmt.c_str(), p.group,
                     p.order.c_str(), p.residency.c_str(), p.bt, p.splits, p.pack, p.warps,
                     p.unroll, t.median, t.p25, t.p75, t.min, t.reps, err_exact, err_ref,
                     ok ? 1 : 0, prop.name);
        ++done;
        if (done % 100 == 0) { std::printf("  %lld plans timed\n", done); std::fflush(stdout); }
      }
      cache.release();
    }
    free_buffers(dbuf);
  }
  std::fclose(out);
  std::printf("\ndone: %lld timed, %lld skipped, %lld failed verification\nwrote %s\n", done,
              skipped, unverified, out_path.c_str());
  return unverified ? 3 : 0;
}
