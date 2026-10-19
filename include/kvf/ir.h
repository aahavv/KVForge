#pragma once

#include "kvf/ast.h"
#include "kvf/calib.h"
#include "kvf/cost.h"
#include "kvf/machine.h"
#include "kvf/plan.h"
#include "kvf/spec.h"

#include <string>
#include <vector>

namespace kvf {

enum class OpKind {
  Query,       // kvf.query     : the single decode query, one vector per head
  KvCache,     // kvf.kvcache   : typed cache value, carries format + layout
  DecodeAttn,  // kvf.decode_attn       : before planning, layout-agnostic
  PlannedAttn, // kvf.decode_attn_split : after planning, fully specified
  Output,      // kvf.output
};

enum class ValueKind { Dense, KvCache };

struct ValueType {
  ValueKind kind = ValueKind::Dense;
  int rows = 0;
  int cols = 0;
  KvFormat fmt;
  KvLayout layout;
  std::string str() const;
};

struct Value {
  int id = -1;
  std::string name;
  ValueType type;
};

// Attributes live on the operation, as in an MLIR-style dialect: planning is a
// rewrite that replaces kvf.decode_attn with kvf.decode_attn_split and attaches
// the chosen format, layout and partition plus the predicted cost.
struct Operation {
  OpKind kind{};
  std::vector<int> operands;
  int result = -1;
  float scale = 0;
  Plan plan;
  Cost cost;
  bool planned = false;
};

struct Module {
  DecodeSpec spec;
  Machine machine;
  Calib calib;
  SearchSpace space;
  std::string machine_file;
  std::string calib_file;
  std::vector<Value> values;
  std::vector<Operation> ops;
  std::vector<Ranked> ranked; // full search result, cheapest first

  int addValue(std::string name, ValueType ty);
  const Value &v(int id) const { return values[id]; }
};

// Semantic analysis: resolve n/d/H against the signature, check shapes, fold
// `?` into the search space, and apply target keys to the machine description.
Module importAst(const Program &p);
std::string dumpModule(const Module &m);

} // namespace kvf
