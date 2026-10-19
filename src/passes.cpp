#include "kvf/passes.h"

#include <stdexcept>

namespace kvf {

void runPlanner(Module &m) {
  const std::vector<Plan> plans = enumeratePlans(m.spec, m.machine, m.space);
  if (plans.empty())
    throw std::runtime_error("planner: design space is empty");
  m.ranked = rankPlans(m.spec, m.machine, m.calib, plans, m.space.max_rel_err);

  // The cheapest plan that passes the accuracy gate wins. Rejected plans stay
  // in the ranking so the report shows what the gate cost.
  const Ranked *chosen = nullptr;
  for (const auto &r : m.ranked) {
    if (!r.cost.rejected) {
      chosen = &r;
      break;
    }
  }
  if (!chosen)
    throw std::runtime_error(
        "planner: every candidate fails the accuracy limit (max_rel_err)");

  bool rewrote = false;
  for (auto &op : m.ops) {
    if (op.kind != OpKind::DecodeAttn)
      continue;
    op.kind = OpKind::PlannedAttn;
    op.plan = chosen->plan;
    op.cost = chosen->cost;
    op.planned = true;
    rewrote = true;

    // The chosen plan is also the cache value's type from here on.
    for (int id : op.operands) {
      Value &v = m.values[static_cast<std::size_t>(id)];
      if (v.type.kind != ValueKind::KvCache)
        continue;
      v.type.fmt = chosen->plan.fmt;
      v.type.layout = chosen->plan.layout;
    }
  }
  if (!rewrote)
    throw std::runtime_error("planner: no kvf.decode_attn to plan");
}

} // namespace kvf
