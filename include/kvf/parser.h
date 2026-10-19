#pragma once

#include "kvf/ast.h"
#include "kvf/lexer.h"

namespace kvf {

// Recursive-descent parser for the grammar in docs/dsl.md.
class Parser {
public:
  explicit Parser(std::string source);
  Program parse();

private:
  Lexer lexer_;
  Token cur_;

  void advance();
  bool accept(Tok k);
  void expect(Tok k, const char *what);
  [[noreturn]] void error(const Token &t, const std::string &msg);

  std::string identLike(const char *what);
  int dimValue(const DecodeFn &fn, const std::string &s, int line);

  void parseTarget(Program &p);
  void parseDecode(Program &p);
  KvDecl parseKvCache(const DecodeFn &fn);
  QueryDecl parseQuery();
  void parseAttn(DecodeFn &fn);
  // `name` or `name:arg` in a format/layout position; "?" stays as "?".
  std::string taggedWord(int &arg);
};

} // namespace kvf
