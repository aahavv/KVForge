#pragma once

#include <string>

namespace kvf {

enum class Tok {
  End,
  Ident,
  Number,
  Text, // "quoted"
  KwTarget,
  KwDecode,
  KwKvCache,
  KwQuery,
  KwDecodeAttn,
  KwScale,
  KwAuto,
  KwSplits,
  KwGqaPack,
  KwTrue,
  KwFalse,
  Equal,
  Comma,
  Colon,
  Question,
  LParen,
  RParen,
  LBrace,
  RBrace,
  LAngle,
  RAngle,
};

struct Token {
  Tok kind{};
  std::string text;
  double number = 0;
  int line = 1;
  int col = 1;
};

// Hand-written DFA scanner: identifiers and keywords, decimal numbers, double
// quoted strings, `#` and `//` comments.
class Lexer {
public:
  explicit Lexer(std::string source);
  Token next();

private:
  std::string src_;
  std::size_t i_ = 0;
  int line_ = 1;
  int col_ = 1;

  char peek(int off = 0) const;
  char get();
  void skipTrivia();
  Token identOrKw(int line, int col);
  Token number(int line, int col);
  Token text(int line, int col);
};

const char *tokName(Tok k);

} // namespace kvf
