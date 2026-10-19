#pragma once

#include "kvf/ir.h"

namespace kvf {

// Enumerate the design space, score every candidate with the analytic cost
// model, apply the accuracy gate, and rewrite kvf.decode_attn into
// kvf.decode_attn_split with the cheapest surviving plan attached.
void runPlanner(Module &m);

} // namespace kvf
