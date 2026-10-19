#pragma once

#include <string>
#include <vector>

namespace kvf {

enum class Format {
  F16,   // lossless: the model's own storage type
  INT8,  // lossy: unsigned 8-bit, per-group scale and zero point
  INT4,  // lossy: unsigned 4-bit (two per byte), per-group scale and zero point
  Unset, // '?' in the DSL: the compiler chooses
};

// A storage format plus the metadata scheme that makes it decodable.
//
// Low-bit formats do not cost `bits` per element: each group of `group`
// elements (along the head dimension, within one token) also stores a scale and
// a zero point, both FP16. Effective bits per element is
// bits + metadata_bits / group, and that is the number the bandwidth model uses.
struct KvFormat {
  Format fmt = Format::F16;
  int group = 0;           // elements per quantization group (0 = none)
  int metadata_bits = 0;   // 32 for quantized formats: FP16 scale + FP16 zero

  int rawBits() const;
  double effectiveBits() const;
  double effectiveBytes() const { return effectiveBits() / 8.0; }
  bool isQuantized() const { return fmt == Format::INT8 || fmt == Format::INT4; }
  // Bytes of payload in one cached row of d elements, metadata excluded.
  int dataRowBytes(int d) const { return d * rawBits() / 8; }
  // Bytes of metadata in one cached row of d elements.
  int metaRowBytes(int d) const { return isQuantized() ? (d / group) * 4 : 0; }
  // FLOPs per loaded element to unpack and dequantize (an estimate: the kernels
  // are memory bound, so this term only matters if it is wildly wrong).
  double dequantFlopsPerElem() const;
  std::string str() const;
  // Stable key used by calibration files, e.g. "int8_128".
  std::string key() const;
};

Format parseFormat(const std::string &s);
const char *formatName(Format f);

// The formats the plan enumerator considers when the DSL leaves format free.
// Groups must divide d; d = 64 therefore drops the 128-element groups.
std::vector<KvFormat> candidateFormats(int d, bool include_quantized);

} // namespace kvf
