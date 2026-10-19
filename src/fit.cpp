#include "kvf/fit.h"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <map>
#include <numeric>
#include <set>
#include <sstream>
#include <stdexcept>

namespace kvf {

namespace {

std::vector<std::string> splitCsv(const std::string &line) {
  std::vector<std::string> out;
  std::string cur;
  for (char ch : line) {
    if (ch == ',') {
      out.push_back(cur);
      cur.clear();
    } else if (ch != '\r') {
      cur.push_back(ch);
    }
  }
  out.push_back(cur);
  return out;
}

// Average ranks, so ties do not distort the correlation.
std::vector<double> ranks(const std::vector<double> &v) {
  std::vector<std::size_t> idx(v.size());
  std::iota(idx.begin(), idx.end(), 0);
  std::sort(idx.begin(), idx.end(),
            [&](std::size_t a, std::size_t b) { return v[a] < v[b]; });
  std::vector<double> r(v.size());
  for (std::size_t i = 0; i < idx.size();) {
    std::size_t j = i;
    while (j + 1 < idx.size() && v[idx[j + 1]] == v[idx[i]])
      ++j;
    const double avg = 0.5 * (static_cast<double>(i) + static_cast<double>(j)) + 1.0;
    for (std::size_t k = i; k <= j; ++k)
      r[idx[k]] = avg;
    i = j + 1;
  }
  return r;
}

double pearson(const std::vector<double> &a, const std::vector<double> &b) {
  const double n = static_cast<double>(a.size());
  double ma = 0, mb = 0;
  for (std::size_t i = 0; i < a.size(); ++i) {
    ma += a[i];
    mb += b[i];
  }
  ma /= n;
  mb /= n;
  double num = 0, da = 0, db = 0;
  for (std::size_t i = 0; i < a.size(); ++i) {
    num += (a[i] - ma) * (b[i] - mb);
    da += (a[i] - ma) * (a[i] - ma);
    db += (b[i] - mb) * (b[i] - mb);
  }
  return da > 0 && db > 0 ? num / std::sqrt(da * db) : 0.0;
}

double kendallTau(const std::vector<double> &a, const std::vector<double> &b) {
  long long conc = 0, disc = 0;
  for (std::size_t i = 0; i < a.size(); ++i)
    for (std::size_t j = i + 1; j < a.size(); ++j) {
      const double x = (a[i] - a[j]) * (b[i] - b[j]);
      if (x > 0)
        ++conc;
      else if (x < 0)
        ++disc;
    }
  const long long tot = conc + disc;
  return tot > 0 ? static_cast<double>(conc - disc) / static_cast<double>(tot) : 0.0;
}

bool formatAllowed(const SweepRow &r, const Calib &c, const Eligibility &e) {
  if (!e.formats.empty()) {
    bool ok = false;
    for (const auto &f : e.formats)
      ok = ok || f == formatName(r.plan.fmt.fmt);
    if (!ok)
      return false;
  }
  if (e.max_rel_err > 0 && r.plan.fmt.isQuantized()) {
    const auto it = c.rel_err.find(r.plan.fmt.key());
    const double err = it == c.rel_err.end() ? 1.0 : it->second;
    if (err > e.max_rel_err)
      return false;
  }
  return true;
}

} // namespace

std::string shapeKey(const DecodeSpec &s) {
  std::ostringstream o;
  o << "H" << s.H << "_Hkv" << s.H_kv << "_d" << s.d << "_n" << s.n << "_b"
    << s.batch;
  return o.str();
}

std::vector<SweepRow> loadSweep(const std::filesystem::path &p) {
  std::ifstream in(p);
  if (!in)
    throw std::runtime_error("cannot read sweep file " + p.string());
  std::string line;
  if (!std::getline(in, line))
    throw std::runtime_error("empty sweep file " + p.string());
  const auto head = splitCsv(line);
  std::map<std::string, std::size_t> col;
  for (std::size_t i = 0; i < head.size(); ++i)
    col[head[i]] = i;
  for (const char *need : {"H", "H_kv", "d", "n", "batch", "fmt", "group", "order",
                           "residency", "block_tokens", "splits", "gqa_pack",
                           "warps", "unroll", "t_us"})
    if (!col.count(need))
      throw std::runtime_error(p.string() + ": missing column " + need);

  std::vector<SweepRow> rows;
  while (std::getline(in, line)) {
    if (line.empty())
      continue;
    const auto f = splitCsv(line);
    auto get = [&](const char *k) -> const std::string & { return f.at(col.at(k)); };
    auto num = [&](const char *k, double dflt = 0.0) {
      return col.count(k) ? std::stod(f.at(col.at(k))) : dflt;
    };
    SweepRow r;
    r.spec.H = std::stoi(get("H"));
    r.spec.H_kv = std::stoi(get("H_kv"));
    r.spec.d = std::stoi(get("d"));
    r.spec.n = std::stoi(get("n"));
    r.spec.batch = std::stoi(get("batch"));
    r.plan.fmt.fmt = parseFormat(get("fmt"));
    r.plan.fmt.group = std::stoi(get("group"));
    r.plan.fmt.metadata_bits = r.plan.fmt.isQuantized() ? 32 : 0;
    r.plan.layout.order = parseOrder(get("order"));
    r.plan.layout.residency = parseResidency(get("residency"));
    r.plan.layout.block_tokens = std::stoi(get("block_tokens"));
    r.plan.part.splits = std::stoi(get("splits"));
    r.plan.part.gqa_pack = std::stoi(get("gqa_pack")) != 0;
    r.plan.part.warps = std::stoi(get("warps"));
    r.plan.part.unroll = std::stoi(get("unroll"));
    r.t_us = num("t_us");
    r.t_p25 = num("t_p25");
    r.t_p75 = num("t_p75");
    r.err_exact = num("err_exact");
    r.verified = num("verified", 1.0) != 0;
    if (r.t_us > 0)
      rows.push_back(std::move(r));
  }
  return rows;
}

Metrics evaluateSweep(const std::vector<SweepRow> &rows, const Machine &m,
                      const Calib &c, const Eligibility &elig,
                      const std::function<bool(const std::string &)> &use_shape) {
  std::map<std::string, std::vector<const SweepRow *>> by_shape;
  for (const auto &r : rows)
    if (r.verified && formatAllowed(r, c, elig) && use_shape(shapeKey(r.spec)))
      by_shape[shapeKey(r.spec)].push_back(&r);

  Metrics out;
  std::ostringstream lines;
  double mape_sum = 0;
  long long mape_n = 0;
  for (const auto &kv : by_shape) {
    const auto &v = kv.second;
    if (v.size() < 2)
      continue;
    std::vector<double> pred, meas;
    for (const SweepRow *r : v) {
      const double p = evaluate(r->spec, m, c, r->plan).t_total_us;
      pred.push_back(p);
      meas.push_back(r->t_us);
      mape_sum += std::abs(p - r->t_us) / r->t_us;
      ++mape_n;
    }
    const double rho = pearson(ranks(pred), ranks(meas));
    const double tau = kendallTau(pred, meas);
    const std::size_t best_pred = static_cast<std::size_t>(
        std::min_element(pred.begin(), pred.end()) - pred.begin());
    const double best_meas = *std::min_element(meas.begin(), meas.end());
    const double regret = meas[best_pred] / best_meas - 1.0;
    out.spearman += rho;
    out.kendall += tau;
    out.regret_mean += regret;
    out.regret_max = std::max(out.regret_max, regret);
    out.top1 += regret <= 1e-9 ? 1.0 : 0.0;
    ++out.shapes;
    out.rows += static_cast<int>(v.size());
    lines << "  " << kv.first << "  rows=" << v.size() << "  rho=" << rho
          << "  tau=" << tau << "  regret=" << 100.0 * regret << "%  chosen="
          << v[best_pred]->plan.str() << " (" << meas[best_pred] << " us vs best "
          << best_meas << " us)\n";
  }
  if (out.shapes > 0) {
    out.spearman /= out.shapes;
    out.kendall /= out.shapes;
    out.regret_mean /= out.shapes;
    out.top1 /= out.shapes;
  }
  out.mape = mape_n ? mape_sum / static_cast<double>(mape_n) : 0;
  out.per_shape = lines.str();
  return out;
}

Calib calibrate(const std::vector<SweepRow> &rows, const Machine &m,
                const Calib &start,
                const std::function<bool(const std::string &)> &use_shape) {
  std::vector<const SweepRow *> use;
  for (const auto &r : rows)
    if (r.verified && use_shape(shapeKey(r.spec)))
      use.push_back(&r);
  if (use.empty())
    throw std::runtime_error("calibrate: no rows selected");

  // The objective is what the compiler is for: choosing well. It is the mean
  // absolute log error of the predictions (so the model stays honest about
  // time) plus the selection regret, averaged over the three eligibility classes
  // a user can ask for: lossless only, int8 allowed, everything allowed.
  std::map<std::string, std::vector<std::size_t>> by_shape;
  for (std::size_t i = 0; i < use.size(); ++i)
    by_shape[shapeKey(use[i]->spec)].push_back(i);
  auto class_ok = [](const SweepRow &r, int cls) {
    const Format f = r.plan.fmt.fmt;
    if (cls == 0) return f == Format::F16;
    if (cls == 1) return f != Format::INT4;
    return true;
  };
  std::vector<double> pred(use.size());
  auto loss = [&](const Calib &c) {
    double mae = 0;
    for (std::size_t i = 0; i < use.size(); ++i) {
      pred[i] = evaluate(use[i]->spec, m, c, use[i]->plan).t_total_us;
      mae += std::abs(std::log(std::max(pred[i], 1e-6) / use[i]->t_us));
    }
    mae /= static_cast<double>(use.size());
    double regret = 0;
    int n = 0;
    for (const auto &kv : by_shape)
      for (int cls = 0; cls < 3; ++cls) {
        double best_meas = 1e300, best_pred = 1e300, chosen_meas = 0;
        for (std::size_t i : kv.second) {
          if (!class_ok(*use[i], cls)) continue;
          best_meas = std::min(best_meas, use[i]->t_us);
          if (pred[i] < best_pred) {
            best_pred = pred[i];
            chosen_meas = use[i]->t_us;
          }
        }
        if (best_meas < 1e299) {
          regret += chosen_meas / best_meas - 1.0;
          ++n;
        }
      }
    return mae + (n ? regret / n : 0.0);
  };

  struct Knob {
    double Calib::*field;
    double lo, hi;
    bool logScale;
  };
  const Knob knobs[] = {
      {&Calib::r0_bytes, 2.0, 8192.0, true},
      {&Calib::c_page_ns, 0.5, 4000.0, true},
      {&Calib::unpack_l2_hit, 0.0, 1.0, false},
      {&Calib::issue_eff, 0.02, 1.0, true},
      {&Calib::meta_waste, 0.0, 2.0, false},
      {&Calib::overlap_p, 1.0, 24.0, true},
      {&Calib::launch_frac, 0.0, 1.5, false},
      {&Calib::merge_frac, 0.0, 1.5, false},
      {&Calib::lat_scale, 1.0, 40.0, true},
      {&Calib::warp_w0, 0.5, 40.0, true},
  };

  Calib best = start;
  double best_loss = loss(best);
  for (int round = 0; round < 6; ++round) {
    for (const Knob &k : knobs) {
      // A grid that tightens around the incumbent each round.
      const double cur = best.*k.field;
      const double span = round == 0 ? 1.0 : std::pow(0.5, round);
      for (int i = 0; i <= 40; ++i) {
        const double t = static_cast<double>(i) / 40.0;
        double v;
        if (k.logScale) {
          const double a = std::log(k.lo), b = std::log(k.hi), cc = std::log(std::max(cur, k.lo));
          const double lo = round == 0 ? a : std::max(a, cc - span * (b - a) / 2);
          const double hi = round == 0 ? b : std::min(b, cc + span * (b - a) / 2);
          v = std::exp(lo + t * (hi - lo));
        } else {
          const double lo = round == 0 ? k.lo : std::max(k.lo, cur - span * (k.hi - k.lo) / 2);
          const double hi = round == 0 ? k.hi : std::min(k.hi, cur + span * (k.hi - k.lo) / 2);
          v = lo + t * (hi - lo);
        }
        Calib trial = best;
        trial.*k.field = v;
        const double l = loss(trial);
        if (l < best_loss) {
          best_loss = l;
          best = trial;
        }
      }
    }
  }

  // Accuracy of each lossy format: the median measured error over the rows.
  std::map<std::string, std::vector<double>> errs;
  for (const SweepRow *r : use)
    if (r->plan.fmt.isQuantized() && r->err_exact > 0)
      errs[r->plan.fmt.key()].push_back(r->err_exact);
  for (auto &kv : errs) {
    std::sort(kv.second.begin(), kv.second.end());
    best.rel_err[kv.first] = kv.second[kv.second.size() / 2];
  }
  return best;
}

} // namespace kvf
