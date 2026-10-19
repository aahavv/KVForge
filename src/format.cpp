#include "kvf/format.h"

#include <sstream>
#include <stdexcept>

namespace kvf {

int KvFormat::rawBits() const {
  switch (fmt) {
  case Format::F16:
    return 16;
  case Format::INT8:
    return 8;
  case Format::INT4:
    return 4;
  case Format::Unset:
    break;
  }
  throw std::runtime_error("format not resolved");
}

double KvFormat::effectiveBits() const {
  const double raw = rawBits();
  if (!isQuantized())
    return raw;
  if (group <= 0)
    throw std::runtime_error("quantized format needs a group size");
  // One scale and one zero point per group, amortized over the group.
  return raw + static_cast<double>(metadata_bits) / group;
}

double KvFormat::dequantFlopsPerElem() const {
  switch (fmt) {
  case Format::F16:
    // Widening to FP32 is a convert, not arithmetic, but it occupies issue
    // slots; counted as a fractional op so the compute roof is not optimistic.
    return 0.5;
  case Format::INT8:
    return 1.5; // convert, then one fused multiply-add with scale and zero
  case Format::INT4:
    return 2.5; // unpack nibble, convert, then one fused multiply-add
  case Format::Unset:
    break;
  }
  return 0;
}

std::string KvFormat::str() const {
  std::ostringstream o;
  o << formatName(fmt);
  if (isQuantized())
    o << ":" << group;
  return o.str();
}

std::string KvFormat::key() const {
  std::ostringstream o;
  o << formatName(fmt);
  if (isQuantized())
    o << "_" << group;
  return o.str();
}

const char *formatName(Format f) {
  switch (f) {
  case Format::F16:
    return "f16";
  case Format::INT8:
    return "int8";
  case Format::INT4:
    return "int4";
  case Format::Unset:
    return "?";
  }
  return "?";
}

Format parseFormat(const std::string &s) {
  if (s == "f16")
    return Format::F16;
  if (s == "int8")
    return Format::INT8;
  if (s == "int4")
    return Format::INT4;
  if (s == "?")
    return Format::Unset;
  throw std::runtime_error("unknown KV format '" + s + "' (f16, int8, int4, ?)");
}

std::vector<KvFormat> candidateFormats(int d, bool include_quantized) {
  std::vector<KvFormat> out;
  out.push_back(KvFormat{Format::F16, 0, 0});
  if (include_quantized) {
    for (int g : {64, 128})
      if (g <= d && d % g == 0)
        out.push_back(KvFormat{Format::INT8, g, 32});
    for (int g : {32, 64, 128})
      if (g <= d && d % g == 0)
        out.push_back(KvFormat{Format::INT4, g, 32});
  }
  return out;
}

} // namespace kvf
