#include "kvf/lexer.h"

#include <cctype>
#include <stdexcept>
#include <unordered_map>

namespace kvf {

Lexer::Lexer(std::string source) : src_(std::move(source)) {}

char Lexer::peek(int off) const {
  const std::size_t j = i_ + static_cast<std::size_t>(off);
  return j < src_.size() ? src_[j] : '\0';
}

char Lexer::get() {
  if (i_ >= src_.size())
    return '\0';
  const char ch = src_[i_++];
  if (ch == '\n') {
    ++line_;
    col_ = 1;
  } else {
    ++col_;
  }
  return ch;
}

void Lexer::skipTrivia() {
  for (;;) {
    while (std::isspace(static_cast<unsigned char>(peek())))
      get();
    if (peek() == '#' || (peek() == '/' && peek(1) == '/')) {
      while (peek() && peek() != '\n')
        get();
      continue;
    }
    break;
  }
}

Token Lexer::identOrKw(int line, int col) {
  std::string s;
  while (std::isalnum(static_cast<unsigned char>(peek())) || peek() == '_')
    s.push_back(get());
  static const std::unordered_map<std::string, Tok> kw{
      {"target", Tok::KwTarget},   {"decode", Tok::KwDecode},
      {"kvcache", Tok::KwKvCache}, {"query", Tok::KwQuery},
      {"decode_attn", Tok::KwDecodeAttn}, {"scale", Tok::KwScale},
      {"auto", Tok::KwAuto},       {"splits", Tok::KwSplits},
      {"gqa_pack", Tok::KwGqaPack}, {"true", Tok::KwTrue},
      {"false", Tok::KwFalse},
  };
  Token t;
  t.line = line;
  t.col = col;
  t.text = s;
  const auto it = kw.find(s);
  t.kind = it == kw.end() ? Tok::Ident : it->second;
  return t;
}

Token Lexer::number(int line, int col) {
  std::string s;
  while (std::isdigit(static_cast<unsigned char>(peek())) || peek() == '.')
    s.push_back(get());
  Token t;
  t.kind = Tok::Number;
  t.line = line;
  t.col = col;
  t.text = s;
  t.number = std::stod(s);
  return t;
}

Token Lexer::text(int line, int col) {
  get(); // opening quote
  std::string s;
  while (peek() && peek() != '"')
    s.push_back(get());
  if (!peek())
    throw std::runtime_error("lex:" + std::to_string(line) +
                             ": unterminated string");
  get(); // closing quote
  Token t;
  t.kind = Tok::Text;
  t.line = line;
  t.col = col;
  t.text = s;
  return t;
}

Token Lexer::next() {
  skipTrivia();
  const int line = line_, col = col_;
  const char ch = peek();
  if (!ch)
    return Token{Tok::End, "", 0, line, col};
  if (std::isalpha(static_cast<unsigned char>(ch)) || ch == '_')
    return identOrKw(line, col);
  if (std::isdigit(static_cast<unsigned char>(ch)))
    return number(line, col);
  if (ch == '"')
    return text(line, col);

  get();
  Token t;
  t.line = line;
  t.col = col;
  t.text = std::string(1, ch);
  switch (ch) {
  case '=': t.kind = Tok::Equal; break;
  case ',': t.kind = Tok::Comma; break;
  case ':': t.kind = Tok::Colon; break;
  case '?': t.kind = Tok::Question; break;
  case '(': t.kind = Tok::LParen; break;
  case ')': t.kind = Tok::RParen; break;
  case '{': t.kind = Tok::LBrace; break;
  case '}': t.kind = Tok::RBrace; break;
  case '<': t.kind = Tok::LAngle; break;
  case '>': t.kind = Tok::RAngle; break;
  default:
    throw std::runtime_error("lex:" + std::to_string(line) + ":" +
                             std::to_string(col) + ": unexpected '" + t.text +
                             "'");
  }
  return t;
}

const char *tokName(Tok k) {
  switch (k) {
  case Tok::End: return "EOF";
  case Tok::Ident: return "ident";
  case Tok::Number: return "number";
  case Tok::Text: return "string";
  case Tok::KwTarget: return "target";
  case Tok::KwDecode: return "decode";
  case Tok::KwKvCache: return "kvcache";
  case Tok::KwQuery: return "query";
  case Tok::KwDecodeAttn: return "decode_attn";
  case Tok::KwScale: return "scale";
  case Tok::KwAuto: return "auto";
  case Tok::KwSplits: return "splits";
  case Tok::KwGqaPack: return "gqa_pack";
  case Tok::KwTrue: return "true";
  case Tok::KwFalse: return "false";
  case Tok::Equal: return "=";
  case Tok::Comma: return ",";
  case Tok::Colon: return ":";
  case Tok::Question: return "?";
  case Tok::LParen: return "(";
  case Tok::RParen: return ")";
  case Tok::LBrace: return "{";
  case Tok::RBrace: return "}";
  case Tok::LAngle: return "<";
  case Tok::RAngle: return ">";
  }
  return "?";
}

} // namespace kvf
