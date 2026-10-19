#include "kvf/parser.h"

#include <stdexcept>

namespace kvf {

Parser::Parser(std::string source) : lexer_(std::move(source)) { advance(); }

void Parser::advance() { cur_ = lexer_.next(); }

bool Parser::accept(Tok k) {
  if (cur_.kind != k)
    return false;
  advance();
  return true;
}

void Parser::expect(Tok k, const char *what) {
  if (cur_.kind != k)
    error(cur_, std::string("expected ") + what + ", got " + tokName(cur_.kind));
  advance();
}

void Parser::error(const Token &t, const std::string &msg) {
  throw std::runtime_error("parse:" + std::to_string(t.line) + ":" +
                           std::to_string(t.col) + ": " + msg);
}

std::string Parser::identLike(const char *what) {
  if (cur_.kind != Tok::Ident)
    error(cur_, std::string("expected ") + what);
  const std::string s = cur_.text;
  advance();
  return s;
}

Program Parser::parse() {
  Program p;
  while (cur_.kind != Tok::End) {
    if (cur_.kind == Tok::KwTarget)
      parseTarget(p);
    else if (cur_.kind == Tok::KwDecode)
      parseDecode(p);
    else
      error(cur_, "expected 'target' or 'decode'");
  }
  if (p.fn.name.empty())
    error(cur_, "program must contain a decode function");
  return p;
}

void Parser::parseTarget(Program &p) {
  TargetDecl t;
  t.line = cur_.line;
  expect(Tok::KwTarget, "target");
  t.key = identLike("target key");
  expect(Tok::Equal, "=");
  if (cur_.kind == Tok::Number) {
    t.value = cur_.number;
    advance();
  } else if (cur_.kind == Tok::Text) {
    t.is_text = true;
    t.text = cur_.text;
    advance();
  } else {
    error(cur_, "expected number or quoted string");
  }
  p.targets.push_back(std::move(t));
}

void Parser::parseDecode(Program &p) {
  if (!p.fn.name.empty())
    error(cur_, "only one decode function is supported");
  DecodeFn fn;
  fn.line = cur_.line;
  expect(Tok::KwDecode, "decode");
  fn.name = identLike("function name");
  expect(Tok::LParen, "(");

  // H: 32, H_kv: 8, d: 128, n: 4096 [, batch: 1]
  auto param = [&](const char *want, bool optional) -> int {
    if (cur_.kind != Tok::Ident || cur_.text != want) {
      if (optional)
        return -1;
      error(cur_, std::string("expected parameter ") + want);
    }
    advance();
    expect(Tok::Colon, ":");
    if (cur_.kind != Tok::Number)
      error(cur_, "expected integer");
    const int v = static_cast<int>(cur_.number);
    advance();
    return v;
  };
  fn.H = param("H", false);
  expect(Tok::Comma, ",");
  fn.H_kv = param("H_kv", false);
  expect(Tok::Comma, ",");
  fn.d = param("d", false);
  expect(Tok::Comma, ",");
  fn.n = param("n", false);
  fn.batch = 1;
  if (accept(Tok::Comma)) {
    const int b = param("batch", true);
    if (b < 0)
      error(cur_, "expected parameter batch");
    fn.batch = b;
  }
  expect(Tok::RParen, ")");
  expect(Tok::LBrace, "{");

  bool saw_attn = false;
  while (cur_.kind != Tok::RBrace && cur_.kind != Tok::End) {
    const std::string name = identLike("declaration or assignment name");
    const int line = cur_.line;
    if (accept(Tok::Colon)) {
      if (cur_.kind == Tok::KwKvCache) {
        KvDecl d = parseKvCache(fn);
        d.name = name;
        d.line = line;
        fn.caches.push_back(std::move(d));
      } else if (cur_.kind == Tok::KwQuery) {
        QueryDecl q = parseQuery();
        q.name = name;
        q.line = line;
        fn.query = std::move(q);
      } else {
        error(cur_, "expected 'kvcache' or 'query'");
      }
    } else if (accept(Tok::Equal)) {
      if (saw_attn)
        error(cur_, "only one decode_attn statement is supported");
      fn.attn.out = name;
      fn.attn.line = line;
      parseAttn(fn);
      saw_attn = true;
    } else {
      error(cur_, "expected ':' or '='");
    }
  }
  expect(Tok::RBrace, "}");

  if (fn.caches.size() != 2)
    error(cur_, "decode must declare exactly two caches (K and V)");
  if (fn.query.name.empty())
    error(cur_, "decode must declare a query tensor");
  if (!saw_attn)
    error(cur_, "decode must contain O = decode_attn(...)");
  p.fn = std::move(fn);
}

std::string Parser::taggedWord(int &arg) {
  arg = 0;
  if (accept(Tok::Question))
    return "?";
  const std::string w = identLike("format or layout name");
  if (accept(Tok::Colon)) {
    if (cur_.kind != Tok::Number)
      error(cur_, "expected integer after ':'");
    arg = static_cast<int>(cur_.number);
    advance();
  }
  return w;
}

int Parser::dimValue(const DecodeFn &fn, const std::string &s, int line) {
  if (s == "n")
    return fn.n;
  if (s == "d")
    return fn.d;
  if (s == "H")
    return fn.H;
  if (s == "H_kv")
    return fn.H_kv;
  try {
    return std::stoi(s);
  } catch (const std::exception &) {
    throw std::runtime_error("semantic:" + std::to_string(line) +
                             ": unknown dimension '" + s + "'");
  }
}

// kvcache<n, d, f16, token_major, contiguous>
// kvcache<n, d, ?, ?, ?>
// kvcache<n, d, int4:128, channel_major:8, paged:64>
KvDecl Parser::parseKvCache(const DecodeFn &fn) {
  KvDecl d;
  expect(Tok::KwKvCache, "kvcache");
  expect(Tok::LAngle, "<");
  auto dim = [&]() -> std::string {
    if (cur_.kind == Tok::Ident || cur_.kind == Tok::Number) {
      const std::string s = cur_.text;
      advance();
      return s;
    }
    error(cur_, "expected shape dimension");
  };
  d.rows = dim();
  expect(Tok::Comma, ",");
  d.cols = dim();
  expect(Tok::Comma, ",");
  d.fmt = taggedWord(d.fmt_group);
  expect(Tok::Comma, ",");
  d.order = taggedWord(d.channel_block);
  expect(Tok::Comma, ",");
  d.residency = taggedWord(d.block_tokens);
  expect(Tok::RAngle, ">");

  const int rows = dimValue(fn, d.rows, d.line);
  const int cols = dimValue(fn, d.cols, d.line);
  if (rows != fn.n || cols != fn.d)
    throw std::runtime_error("semantic: cache shape must be <n, d, ...>");
  return d;
}

// query<H, d, f32>
QueryDecl Parser::parseQuery() {
  QueryDecl q;
  expect(Tok::KwQuery, "query");
  expect(Tok::LAngle, "<");
  q.rows = identLike("row dimension");
  expect(Tok::Comma, ",");
  q.cols = identLike("column dimension");
  expect(Tok::Comma, ",");
  q.dtype = identLike("dtype");
  expect(Tok::RAngle, ">");
  return q;
}

// decode_attn(Q, K, V [, scale = auto|number] [, splits = N|?]
//                     [, gqa_pack = true|false|?])
void Parser::parseAttn(DecodeFn &fn) {
  expect(Tok::KwDecodeAttn, "decode_attn");
  expect(Tok::LParen, "(");
  fn.attn.q = identLike("query name");
  expect(Tok::Comma, ",");
  fn.attn.k = identLike("key cache name");
  expect(Tok::Comma, ",");
  fn.attn.v = identLike("value cache name");
  while (accept(Tok::Comma)) {
    if (accept(Tok::KwScale)) {
      expect(Tok::Equal, "=");
      if (accept(Tok::KwAuto)) {
        fn.attn.scale_auto = true;
      } else if (cur_.kind == Tok::Number) {
        fn.attn.scale_auto = false;
        fn.attn.scale = cur_.number;
        advance();
      } else {
        error(cur_, "expected 'auto' or a number");
      }
    } else if (accept(Tok::KwSplits)) {
      expect(Tok::Equal, "=");
      if (accept(Tok::Question)) {
        fn.attn.splits = 0; // free: the planner chooses
      } else if (cur_.kind == Tok::Number) {
        fn.attn.splits = static_cast<int>(cur_.number);
        if (fn.attn.splits < 1)
          error(cur_, "splits must be >= 1");
        advance();
      } else {
        error(cur_, "expected integer or '?'");
      }
    } else if (accept(Tok::KwGqaPack)) {
      expect(Tok::Equal, "=");
      if (accept(Tok::Question)) {
        fn.attn.gqa_pack_set = false;
      } else if (accept(Tok::KwTrue)) {
        fn.attn.gqa_pack = true;
        fn.attn.gqa_pack_set = true;
      } else if (accept(Tok::KwFalse)) {
        fn.attn.gqa_pack = false;
        fn.attn.gqa_pack_set = true;
      } else {
        error(cur_, "expected true, false or '?'");
      }
    } else {
      error(cur_, "expected scale=, splits= or gqa_pack=");
    }
  }
  expect(Tok::RParen, ")");
}

} // namespace kvf
