#include "kvf/calib.h"
#include "kvf/codegen.h"
#include "kvf/emit.h"
#include "kvf/fit.h"
#include "kvf/parser.h"
#include "kvf/passes.h"

#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

std::string readFile(const std::filesystem::path &p) {
  std::ifstream in(p, std::ios::binary);
  if (!in)
    throw std::runtime_error("cannot read " + p.string());
  std::ostringstream ss;
  ss << in.rdbuf();
  return ss.str();
}

void writeFile(const std::filesystem::path &p, const std::string &s) {
  std::filesystem::create_directories(p.parent_path().empty() ? "." : p.parent_path());
  std::ofstream o(p, std::ios::binary);
  if (!o)
    throw std::runtime_error("cannot write " + p.string());
  o << s;
}

int usage() {
  std::cerr
      << "kvf - a bandwidth-model-driven compiler for GPU decode-phase attention\n\n"
      << "usage:\n"
      << "  kvf plan <file.kv>  [--out DIR] [--top N] [--all] [--quant]\n"
      << "                      [--machine FILE] [--calib FILE] [--max-err X]\n"
      << "  kvf roofline <file.kv> [--machine FILE]\n"
      << "  kvf machine  <file.gpu>\n"
      << "  kvf emit-dispatch --out DIR [--d 128,64] [--g 1,4,8] [--quant]\n"
      << "  kvf calibrate --sweep A.csv[,B.csv] --machine FILE --out FILE\n"
      << "                [--holdout-every N]\n"
      << "  kvf predict   --sweep A.csv --machine FILE [--calib FILE] --out FILE\n"
      << "  kvf evaluate  --sweep A.csv --machine FILE [--calib FILE]\n"
      << "                [--holdout-every N] [--which fit|heldout|all]\n\n"
      << "  --out DIR       output directory (default: out)\n"
      << "  --top N         rows of the candidate table to print (default 12)\n"
      << "  --all           print every candidate\n"
      << "  --quant         allow lossy formats (int8 / int4) in the search\n"
      << "  --max-err X     accuracy limit: lossy formats must have calibrated\n"
      << "                  relative error <= X (implies --quant)\n"
      << "  --machine FILE  GPU description, overrides `target machine`\n"
      << "  --calib FILE    frozen cost-model constants, overrides `target calib`\n";
  return 2;
}

struct Args {
  std::string cmd;
  std::vector<std::string> pos;
  std::map<std::string, std::string> opt;
  std::set<std::string> flags;
  bool has(const std::string &k) const { return opt.count(k) || flags.count(k); }
  std::string get(const std::string &k, const std::string &d = "") const {
    const auto it = opt.find(k);
    return it == opt.end() ? d : it->second;
  }
};

Args parseArgs(int argc, char **argv) {
  static const std::set<std::string> boolean{"all", "quant"};
  Args a;
  a.cmd = argv[1];
  for (int i = 2; i < argc; ++i) {
    const std::string s = argv[i];
    if (s.rfind("--", 0) == 0) {
      const std::string k = s.substr(2);
      if (boolean.count(k))
        a.flags.insert(k);
      else if (i + 1 < argc)
        a.opt[k] = argv[++i];
      else
        throw std::runtime_error("option --" + k + " needs a value");
    } else {
      a.pos.push_back(s);
    }
  }
  return a;
}

std::vector<int> intList(const std::string &s) {
  std::vector<int> out;
  std::stringstream ss(s);
  std::string tok;
  while (std::getline(ss, tok, ','))
    if (!tok.empty())
      out.push_back(std::stoi(tok));
  return out;
}

kvf::Module frontEnd(const Args &a) {
  if (a.pos.empty())
    throw std::runtime_error("missing input file");
  kvf::Parser parser(readFile(a.pos[0]));
  const kvf::Program prog = parser.parse();
  kvf::Module mod = kvf::importAst(prog);
  if (a.has("machine")) {
    mod.machine = kvf::loadMachine(a.get("machine"));
    mod.machine_file = a.get("machine");
  }
  if (a.has("calib")) {
    mod.calib = kvf::loadCalib(a.get("calib"));
    mod.calib_file = a.get("calib");
  }
  if (a.flags.count("quant"))
    mod.space.include_quantized = true;
  if (a.has("max-err")) {
    mod.space.max_rel_err = std::stod(a.get("max-err"));
    mod.space.include_quantized = true;
  }
  return mod;
}

// Hold out every Nth distinct shape (sorted by key) so the model is judged on
// shapes it was not fitted on.
std::set<std::string> heldOutShapes(const std::vector<kvf::SweepRow> &rows, int every) {
  std::set<std::string> keys;
  for (const auto &r : rows)
    keys.insert(kvf::shapeKey(r.spec));
  std::set<std::string> held;
  int i = 0;
  for (const auto &k : keys) {
    if (every > 0 && i % every == every - 1)
      held.insert(k);
    ++i;
  }
  return held;
}

std::string fmtMetrics(const std::string &title, const kvf::Metrics &m) {
  std::ostringstream o;
  o << std::fixed << std::setprecision(3);
  o << title << "\n";
  o << "  shapes " << m.shapes << ", rows " << m.rows << "\n";
  o << "  MAPE            " << 100.0 * m.mape << " %\n";
  o << "  Spearman rho    " << m.spearman << "\n";
  o << "  Kendall tau     " << m.kendall << "\n";
  o << "  regret mean     " << 100.0 * m.regret_mean << " %\n";
  o << "  regret max      " << 100.0 * m.regret_max << " %\n";
  o << "  top-1 hit       " << 100.0 * m.top1 << " %\n";
  return o.str();
}

std::string evalReport(const std::vector<kvf::SweepRow> &rows, const kvf::Machine &mach,
                       const kvf::Calib &calib,
                       const std::function<bool(const std::string &)> &pick) {
  struct Case {
    const char *name;
    kvf::Eligibility e;
  };
  std::vector<Case> cases;
  {
    kvf::Eligibility e;
    e.formats = {"f16"};
    cases.push_back({"lossless only (f16)", e});
  }
  {
    kvf::Eligibility e;
    e.max_rel_err = 0.02;
    cases.push_back({"accuracy limit 0.02 (f16 + int8)", e});
  }
  {
    kvf::Eligibility e;
    cases.push_back({"no accuracy limit (f16 + int8 + int4)", e});
  }
  std::ostringstream o;
  for (const auto &c : cases) {
    const kvf::Metrics m = kvf::evaluateSweep(rows, mach, calib, c.e, pick);
    o << fmtMetrics(c.name, m) << m.per_shape << "\n";
  }
  return o.str();
}

} // namespace

int main(int argc, char **argv) {
  try {
    if (argc < 2)
      return usage();
    const Args a = parseArgs(argc, argv);

    if (a.cmd == "machine") {
      if (a.pos.empty())
        return usage();
      const kvf::Machine m = kvf::loadMachine(a.pos[0]);
      std::cout << kvf::dumpMachine(m);
      std::cout << "# derived\n";
      std::cout << "# ridge          = " << m.ridgeFlopPerByte() << " FLOP/byte\n";
      std::cout << "# f_sm_gflops    = " << m.fSmGflops() << "\n";
      std::cout << "# bw_device(all, full flight) = "
                << m.bwDeviceGbs(m.sms, 1e9) << " GB/s\n";
      return 0;
    }

    if (a.cmd == "emit-dispatch") {
      const std::filesystem::path out = a.get("out", "gen");
      const auto dims = intList(a.get("d", "128"));
      const auto groups = intList(a.get("g", "1,4"));
      const bool quant = a.flags.count("quant") || true;
      const auto files = kvf::emitDispatchSources(dims, groups, quant);
      std::filesystem::create_directories(out);
      for (const auto &f : files)
        writeFile(out / f.first, f.second);
      std::cout << "wrote " << files.size() << " dispatch sources to " << out.string()
                << "\n";
      for (const auto &f : files)
        std::cout << f.first << "\n";
      return 0;
    }

    if (a.cmd == "predict") {
      // Predicted next to measured for every row of a sweep, for plotting.
      if (!a.has("sweep") || !a.has("machine"))
        return usage();
      const auto rows = kvf::loadSweep(a.get("sweep"));
      const kvf::Machine mach = kvf::loadMachine(a.get("machine"));
      const kvf::Calib c =
          a.has("calib") ? kvf::loadCalib(a.get("calib")) : kvf::Calib::defaults();
      std::ostringstream o;
      o << "shape,fmt,group,order,residency,block_tokens,splits,gqa_pack,warps,unroll,"
           "t_us,pred_us,pred_mem_us,pred_merge_us,pred_page_us,eta,verified,err_exact\n";
      // enough digits that near-tied predictions rank as the compiler ranks them
      o << std::setprecision(10);
      for (const auto &r : rows) {
        const kvf::Cost k = kvf::evaluate(r.spec, mach, c, r.plan);
        o << kvf::shapeKey(r.spec) << ',' << kvf::formatName(r.plan.fmt.fmt) << ','
          << r.plan.fmt.group << ',' << kvf::orderName(r.plan.layout.order) << ','
          << kvf::residencyName(r.plan.layout.residency) << ','
          << r.plan.layout.block_tokens << ',' << r.plan.part.splits << ','
          << (r.plan.part.gqa_pack ? 1 : 0) << ',' << r.plan.part.warps << ','
          << r.plan.part.unroll << ',' << r.t_us << ',' << k.t_total_us << ','
          << k.t_mem_us << ',' << k.t_merge_us << ',' << k.t_page_us << ',' << k.eta
          << ',' << (r.verified ? 1 : 0) << ',' << r.err_exact << "\n";
      }
      writeFile(a.get("out", "predicted.csv"), o.str());
      std::cout << "wrote " << a.get("out", "predicted.csv") << " (" << rows.size()
                << " rows)\n";
      return 0;
    }

    if (a.cmd == "calibrate" || a.cmd == "evaluate") {
      if (!a.has("sweep") || !a.has("machine"))
        return usage();
      std::vector<kvf::SweepRow> rows;
      {
        std::stringstream ss(a.get("sweep"));
        std::string path;
        while (std::getline(ss, path, ',')) {
          auto part = kvf::loadSweep(path);
          rows.insert(rows.end(), part.begin(), part.end());
        }
      }
      const kvf::Machine mach = kvf::loadMachine(a.get("machine"));
      const int every = std::stoi(a.get("holdout-every", "3"));
      const auto held = heldOutShapes(rows, every);
      auto fit = [&](const std::string &k) { return !held.count(k); };
      auto heldout = [&](const std::string &k) { return held.count(k) > 0; };
      auto all = [](const std::string &) { return true; };

      if (a.cmd == "calibrate") {
        kvf::Calib start = kvf::Calib::defaults();
        if (a.has("wave-model"))
          start.wave_model = std::stod(a.get("wave-model"));
        kvf::Calib c = kvf::calibrate(rows, mach, start, fit);
        if (a.has("out"))
          kvf::saveCalib(c, a.get("out"));
        std::cout << "fitted constants (machine " << mach.name << ", "
                  << (rows.size()) << " rows, " << held.size() << " held-out shapes)\n";
        std::cout << kvf::dumpCalib(c) << "\n";
        std::cout << evalReport(rows, mach, c, fit);
        if (!held.empty()) {
          std::cout << "=== HELD-OUT shapes (not used in the fit) ===\n";
          std::cout << evalReport(rows, mach, c, heldout);
        }
        return 0;
      }

      const kvf::Calib c =
          a.has("calib") ? kvf::loadCalib(a.get("calib")) : kvf::Calib::defaults();
      const std::string which = a.get("which", "all");
      const auto &pick = which == "fit" ? std::function<bool(const std::string &)>(fit)
                         : which == "heldout"
                             ? std::function<bool(const std::string &)>(heldout)
                             : std::function<bool(const std::string &)>(all);
      std::cout << "machine " << mach.name << ", constants "
                << (a.has("calib") ? a.get("calib") : "defaults") << ", shapes: " << which
                << "\n\n";
      std::cout << evalReport(rows, mach, c, pick);
      return 0;
    }

    if (a.pos.empty())
      return usage();
    kvf::Module mod = frontEnd(a);

    if (a.cmd == "roofline") {
      std::cout << kvf::emitRoofline(mod);
      return 0;
    }
    if (a.cmd != "plan")
      return usage();

    const std::string before = kvf::dumpModule(mod);
    kvf::runPlanner(mod);
    const int top = a.flags.count("all") ? 0 : std::stoi(a.get("top", "12"));
    const kvf::Artifacts art =
        kvf::emitAll(mod, a.get("out", "out"), before, top);
    std::cout << readFile(art.report);
    std::cout << "\nwrote " << art.report.string() << "\n";
    std::cout << "wrote " << art.plans_csv.string() << "\n";
    std::cout << "wrote " << art.ir_txt.string() << "\n";
    std::cout << "wrote " << art.kernel_cu.string() << "\n";
    return 0;
  } catch (const std::exception &e) {
    std::cerr << "kvf: " << e.what() << "\n";
    return 1;
  }
}
